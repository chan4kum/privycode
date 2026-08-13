import asyncio
import json
import logging
import time
from typing import Annotated, AsyncGenerator

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from packages.contracts import (
    ChatRequest,
    CompletionRequest,
    EditRequest,
)
from packages.db.database import get_db_session
from packages.db.models import User

from ..dependencies.auth import get_current_authenticated_user
from ..middleware.rate_limiter import rate_limiter
from ..services.router import model_router
from ..services.telemetry import record_usage_telemetry

logger = logging.getLogger("coding-api")

router = APIRouter(prefix="/v1", tags=["Coding Intelligence"])


def format_chat_messages_with_context(req: ChatRequest) -> list[dict]:
    """Combines multi-file IDE context snippets into structured chat messages."""
    messages = []

    # If context files were attached, construct a system context block
    if req.context_files:
        context_blocks = []
        for f in req.context_files:
            snippet = f"# File: {f.path}\n{f.content}"
            if f.selection_range:
                snippet += f"\n# Selection: Lines {f.selection_range.get('start_line')}-{f.selection_range.get('end_line')}"
            context_blocks.append(snippet)

        context_prompt = (
            "You are PrivyCode, an expert coding assistant.\n"
            "Below is the relevant context from the developer's repository:\n\n"
            + "\n\n---\n\n".join(context_blocks)
        )
        messages.append({"role": "system", "content": context_prompt})

    for msg in req.messages:
        messages.append({"role": msg.role, "content": msg.content})

    return messages


@router.post("/chat")
async def chat_completions(
    req: ChatRequest,
    current_user: Annotated[User, Depends(get_current_authenticated_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
):
    """Context-aware conversational chat endpoint with SSE streaming."""
    rl = await rate_limiter.check_rate_limit(str(current_user.id), "/v1/chat")
    if not rl["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry in {rl['reset_in_seconds']}s.",
        )

    model_record, worker_url = await model_router.resolve_route(
        session=session,
        user=current_user,
        requested_model=req.model,
        mode=req.mode,
        request_type="chat",
    )

    formatted_messages = format_chat_messages_with_context(req)
    worker_payload = {
        "model": model_record.id,
        "messages": formatted_messages,
        "sampling_params": {
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
        },
        "stream": req.stream,
    }

    start_time = time.perf_counter()

    if req.stream:
        async def sse_proxy_stream() -> AsyncGenerator[str, None]:
            prompt_tokens = 0
            completion_tokens = 0
            status_code = 200

            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        f"{worker_url}/worker/v1/generate",
                        json=worker_payload,
                    ) as response:
                        if response.status_code != 200:
                            status_code = response.status_code
                            yield f"data: {json.dumps({'error': 'Worker unavailable'})}\n\n"
                            return

                        async for line in response.aiter_lines():
                            if line.startswith("data: ") and not line.endswith("[DONE]"):
                                try:
                                    chunk = json.loads(line[6:])
                                    usage = chunk.get("usage", {})
                                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                                    completion_tokens = usage.get("completion_tokens", completion_tokens)
                                except Exception:
                                    pass
                            yield f"{line}\n\n"
            except Exception as exc:
                logger.warning(f"Chat stream interrupted for user {current_user.id}: {exc}")
                status_code = 500
            finally:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                # Direct asyncio task to guarantee execution even after stream closes
                asyncio.create_task(
                    record_usage_telemetry(
                        user_id=current_user.id,
                        model_id=model_record.id,
                        endpoint="/v1/chat",
                        prompt_tokens=prompt_tokens or 25,
                        completion_tokens=completion_tokens or 1,
                        latency_ms=elapsed_ms,
                        status_code=status_code,
                    )
                )

        return StreamingResponse(
            sse_proxy_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    else:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(f"{worker_url}/worker/v1/generate", json=worker_payload)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            data = res.json()
            usage = data.get("usage", {})

            background_tasks.add_task(
                record_usage_telemetry,
                user_id=current_user.id,
                model_id=model_record.id,
                endpoint="/v1/chat",
                prompt_tokens=usage.get("prompt_tokens", 25),
                completion_tokens=usage.get("completion_tokens", 50),
                latency_ms=elapsed_ms,
                status_code=res.status_code,
            )
            return JSONResponse(content=data, status_code=res.status_code)


@router.post("/edits")
async def code_edits(
    req: EditRequest,
    current_user: Annotated[User, Depends(get_current_authenticated_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
):
    """Targeted code edits generating unified diffs or replacement blocks with streaming support."""
    rl = await rate_limiter.check_rate_limit(str(current_user.id), "/v1/edits")
    if not rl["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Retry in {rl['reset_in_seconds']}s.",
        )

    model_record, worker_url = await model_router.resolve_route(
        session=session,
        user=current_user,
        requested_model=req.model,
        mode=req.mode,
        request_type="edit",
    )

    edit_prompt = (
        f"You are a code refactoring engine.\n"
        f"File: {req.file_path or 'unknown'}\n"
        f"Language: {req.language or 'python'}\n"
        f"Instruction: {req.instruction}\n\n"
        f"Original Code:\n```\n{req.input}\n```\n\n"
        f"Provide the exact refactored replacement code."
    )

    worker_payload = {
        "model": model_record.id,
        "prompt": edit_prompt,
        "sampling_params": {
            "temperature": req.temperature,
            "max_tokens": 4096,
        },
        "stream": req.stream,
    }

    start_time = time.perf_counter()

    if req.stream:
        async def edit_stream_generator() -> AsyncGenerator[str, None]:
            prompt_tokens = 0
            completion_tokens = 0
            status_code = 200
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    async with client.stream(
                        "POST",
                        f"{worker_url}/worker/v1/generate",
                        json=worker_payload,
                    ) as response:
                        if response.status_code != 200:
                            status_code = response.status_code
                            return

                        async for line in response.aiter_lines():
                            if line.startswith("data: ") and not line.endswith("[DONE]"):
                                try:
                                    chunk = json.loads(line[6:])
                                    usage = chunk.get("usage", {})
                                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                                    completion_tokens = usage.get("completion_tokens", completion_tokens)
                                except Exception:
                                    pass
                            yield f"{line}\n\n"
            except Exception as exc:
                logger.warning(f"Edit stream interrupted: {exc}")
                status_code = 500
            finally:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                asyncio.create_task(
                    record_usage_telemetry(
                        user_id=current_user.id,
                        model_id=model_record.id,
                        endpoint="/v1/edits",
                        prompt_tokens=prompt_tokens or len(edit_prompt.split()),
                        completion_tokens=completion_tokens or 10,
                        latency_ms=elapsed_ms,
                        status_code=status_code,
                    )
                )

        return StreamingResponse(
            edit_stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    else:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(f"{worker_url}/worker/v1/generate", json=worker_payload)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            data = res.json()
            usage = data.get("usage", {})

            background_tasks.add_task(
                record_usage_telemetry,
                user_id=current_user.id,
                model_id=model_record.id,
                endpoint="/v1/edits",
                prompt_tokens=usage.get("prompt_tokens", len(edit_prompt.split())),
                completion_tokens=usage.get("completion_tokens", 50),
                latency_ms=elapsed_ms,
                status_code=res.status_code,
            )
            return JSONResponse(content=data, status_code=res.status_code)


@router.post("/completions")
async def code_completions(
    req: CompletionRequest,
    current_user: Annotated[User, Depends(get_current_authenticated_user)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    background_tasks: BackgroundTasks,
):
    """Ultra low-latency Fill-in-the-Middle (FIM) inline completion endpoint."""
    rl = await rate_limiter.check_rate_limit(str(current_user.id), "/v1/completions", capacity=120)
    if not rl["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Completion rate limit reached.",
        )

    model_record, worker_url = await model_router.resolve_route(
        session=session,
        user=current_user,
        requested_model=req.model,
        mode="cheap",
        request_type="autocomplete",
    )

    worker_payload = {
        "model": model_record.id,
        "prompt": req.prompt,
        "sampling_params": {
            "temperature": req.temperature,
            "max_tokens": req.max_tokens,
            "stop": req.stop,
        },
        "stream": req.stream,
    }

    start_time = time.perf_counter()

    if req.stream:
        async def fim_stream_generator() -> AsyncGenerator[str, None]:
            prompt_tokens = 0
            completion_tokens = 0
            status_code = 200
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    async with client.stream(
                        "POST",
                        f"{worker_url}/worker/v1/generate",
                        json=worker_payload,
                    ) as response:
                        if response.status_code != 200:
                            status_code = response.status_code
                            return

                        async for line in response.aiter_lines():
                            if line.startswith("data: ") and not line.endswith("[DONE]"):
                                try:
                                    chunk = json.loads(line[6:])
                                    usage = chunk.get("usage", {})
                                    prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
                                    completion_tokens = usage.get("completion_tokens", completion_tokens)
                                except Exception:
                                    pass
                            yield f"{line}\n\n"
            except Exception as exc:
                logger.debug(f"FIM stream aborted by user: {exc}")
            finally:
                elapsed_ms = int((time.perf_counter() - start_time) * 1000)
                asyncio.create_task(
                    record_usage_telemetry(
                        user_id=current_user.id,
                        model_id=model_record.id,
                        endpoint="/v1/completions",
                        prompt_tokens=prompt_tokens or len(req.prompt.split()),
                        completion_tokens=completion_tokens or 5,
                        latency_ms=elapsed_ms,
                        status_code=status_code,
                    )
                )

        return StreamingResponse(
            fim_stream_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    else:
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(f"{worker_url}/worker/v1/generate", json=worker_payload)
            elapsed_ms = int((time.perf_counter() - start_time) * 1000)
            data = res.json()
            usage = data.get("usage", {})

            background_tasks.add_task(
                record_usage_telemetry,
                user_id=current_user.id,
                model_id=model_record.id,
                endpoint="/v1/completions",
                prompt_tokens=usage.get("prompt_tokens", len(req.prompt.split())),
                completion_tokens=usage.get("completion_tokens", 10),
                latency_ms=elapsed_ms,
                status_code=res.status_code,
            )
            return JSONResponse(content=data, status_code=res.status_code)
