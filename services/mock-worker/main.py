import asyncio
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Literal

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mock-worker")

# Configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
WORKER_NAME = os.getenv("WORKER_NAME", "mock-worker-1")
WORKER_BASE_URL = os.getenv("WORKER_BASE_URL", "http://localhost:8001")
WORKER_RUNTIME = os.getenv("WORKER_RUNTIME", "mock")
MAX_CONTEXT_TOKENS = int(os.getenv("MAX_CONTEXT_TOKENS", "32768"))
TOKEN_DELAY_SECONDS = float(os.getenv("TOKEN_DELAY_SECONDS", "0.015"))  # ~66 tokens/sec simulation

# Pydantic Models
class WorkerHealthResponse(BaseModel):
    status: Literal["healthy", "degraded", "offline"] = "healthy"
    worker_name: str
    runtime: str
    max_context_tokens: int
    gpu_utilization_percent: float
    kv_cache_usage_percent: float
    active_requests: int

class SamplingParams(BaseModel):
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    stop: list[str] = Field(default_factory=list)

class WorkerGenerateRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    model: str
    prompt: str | None = None
    messages: list[dict] | None = None
    sampling_params: SamplingParams = Field(default_factory=SamplingParams)
    stream: bool = True

active_request_count = 0

def estimate_prompt_tokens(req: WorkerGenerateRequest) -> int:
    """Estimates the input prompt tokens based on word count."""
    if req.prompt:
        return max(1, len(req.prompt.split()))
    if req.messages:
        return max(1, sum(len(m.get("content", "").split()) for m in req.messages))
    return 20

# Mock Text Generation Templates
def generate_mock_tokens(prompt: str | None, messages: list[dict] | None) -> list[str]:
    """Generates realistic mock code tokens for chat, edits, and completions."""
    text_content = ""
    if messages:
        last_msg = messages[-1].get("content", "")
        text_content = (
            f"```python\n"
            f"# Generated code response to: {last_msg[:60]}...\n"
            f"async def process_task(data: dict) -> dict:\n"
            f"    # Validating zero-retention privacy boundary\n"
            f"    sanitized = {k: v for k, v in data.items() if k != 'secret'}\n"
            f"    return {'status': 'processed', 'payload': sanitized}\n"
            f"```\n\n"
            f"I have refactored the function to ensure in-memory handling and strict error boundaries."
        )
    elif prompt and "<|fim_prefix|>" in prompt:
        # FIM completion
        text_content = "    result = compute_metrics(tokens, latency)\n    return result"
    else:
        text_content = (
            "def handler():\n"
            "    \"\"\"Mocked high performance code completion.\"\"\"\n"
            "    return True"
        )

    # Chunk into word-level / token-level pieces
    words = text_content.split(" ")
    tokens = [w + " " for w in words[:-1]] + [words[-1]]
    return tokens


async def heartbeat_loop():
    """Background task to register and heartbeat with SovereignForge Gateway."""
    logger.info(f"Starting registration loop targeting Gateway at: {GATEWAY_URL}")
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                # 1. Register or send heartbeat
                payload = {
                    "name": WORKER_NAME,
                    "runtime": WORKER_RUNTIME,
                    "base_url": WORKER_BASE_URL,
                    "status": "healthy",
                    "max_context_tokens": MAX_CONTEXT_TOKENS,
                }
                res = await client.post(f"{GATEWAY_URL}/internal/workers/heartbeat", json=payload)
                if res.status_code == status.HTTP_200:
                    logger.debug(f"Heartbeat accepted by Gateway: {res.status_code}")
                else:
                    # If heartbeat fails, register worker first
                    await client.post(f"{GATEWAY_URL}/internal/workers/register", json=payload)
                    logger.info("Worker registered with Gateway successfully.")
            except Exception as e:
                logger.debug(f"Gateway connection standby ({GATEWAY_URL}): {e}")

            await asyncio.sleep(10)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    yield
    # Shutdown
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="SovereignForge Mock Inference Worker",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health", response_model=WorkerHealthResponse)
async def health_check():
    """Returns worker health and simulated hardware metrics."""
    return WorkerHealthResponse(
        status="healthy",
        worker_name=WORKER_NAME,
        runtime=WORKER_RUNTIME,
        max_context_tokens=MAX_CONTEXT_TOKENS,
        gpu_utilization_percent=34.5,
        kv_cache_usage_percent=18.2,
        active_requests=active_request_count,
    )


@app.post("/worker/v1/generate")
async def generate(req: WorkerGenerateRequest):
    """Core inference generation endpoint supporting SSE streams and JSON payloads."""
    global active_request_count
    active_request_count += 1
    tokens = generate_mock_tokens(req.prompt, req.messages)
    estimated_prompt_tokens = estimate_prompt_tokens(req)

    if req.stream:
        async def event_generator() -> AsyncGenerator[str, None]:
            global active_request_count
            try:
                for idx, token in enumerate(tokens):
                    await asyncio.sleep(TOKEN_DELAY_SECONDS)
                    chunk_payload = {
                        "id": req.request_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": req.model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {"content": token},
                                "finish_reason": "stop" if idx == len(tokens) - 1 else None,
                            }
                        ],
                        "usage": {
                            "prompt_tokens": estimated_prompt_tokens,
                            "completion_tokens": idx + 1,
                        },
                    }
                    yield f"data: {json.dumps(chunk_payload)}\n\n"
                yield "data: [DONE]\n\n"
            finally:
                active_request_count = max(0, active_request_count - 1)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        try:
            full_text = "".join(tokens)
            return JSONResponse(
                content={
                    "id": req.request_id,
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {"role": "assistant", "content": full_text},
                            "finish_reason": "stop",
                        }
                    ],
                    "usage": {
                        "prompt_tokens": estimated_prompt_tokens,
                        "completion_tokens": len(tokens),
                        "total_tokens": estimated_prompt_tokens + len(tokens),
                    },
                }
            )
        finally:
            active_request_count = max(0, active_request_count - 1)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
