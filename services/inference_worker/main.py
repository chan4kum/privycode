import asyncio
import json
import logging
import os
import sys
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional

# Add project root
root_dir = str(Path(__file__).resolve().parents[2])
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

import httpx
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from services.inference_worker.adapters.base import BaseLLMAdapter, SamplingParams
from services.inference_worker.adapters.groq_adapter import GroqAdapter
from services.inference_worker.adapters.mock_adapter import MockAdapter
from services.inference_worker.adapters.ollama_adapter import OllamaAdapter
from services.inference_worker.adapters.vllm_adapter import VLLMAdapter

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("inference-worker")

# Environment Configuration
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
WORKER_NAME = os.getenv("WORKER_NAME", "unified-inference-worker-1")
WORKER_BASE_URL = os.getenv("WORKER_BASE_URL", "http://localhost:8001")
INFERENCE_RUNTIME = os.getenv("INFERENCE_RUNTIME", "mock")  # 'vllm' | 'ollama' | 'groq' | 'mock'
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://localhost:8000")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

def get_adapter(runtime: str) -> BaseLLMAdapter:
    """Instantiates the appropriate backend adapter based on runtime selection."""
    if runtime == "vllm":
        logger.info(f"Initializing vLLM adapter targeting: {VLLM_BASE_URL}")
        return VLLMAdapter(base_url=VLLM_BASE_URL)
    elif runtime == "ollama":
        logger.info(f"Initializing Ollama adapter targeting: {OLLAMA_BASE_URL}")
        return OllamaAdapter(base_url=OLLAMA_BASE_URL)
    elif runtime == "groq":
        logger.info("Initializing Groq zero-retention cloud adapter")
        return GroqAdapter(api_key=GROQ_API_KEY)
    else:
        logger.info("Initializing high-performance Mock adapter")
        return MockAdapter()

active_adapter: BaseLLMAdapter = get_adapter(INFERENCE_RUNTIME)

class WorkerGenerateRequest(BaseModel):
    request_id: str = Field(default_factory=lambda: f"req_{uuid.uuid4().hex[:12]}")
    model: str = "mock-qwen-32b"
    prompt: Optional[str] = None
    messages: Optional[List[Dict[str, str]]] = None
    sampling_params: SamplingParams = Field(default_factory=SamplingParams)
    stream: bool = True

async def heartbeat_loop():
    """Background task sending heartbeat to SovereignForge Gateway."""
    logger.info(f"Registration & heartbeat loop targeting Gateway at: {GATEWAY_URL}")
    async with httpx.AsyncClient(timeout=5.0) as client:
        while True:
            try:
                payload = {
                    "name": WORKER_NAME,
                    "runtime": INFERENCE_RUNTIME,
                    "base_url": WORKER_BASE_URL,
                    "status": "healthy",
                    "max_context_tokens": 32768,
                }
                res = await client.post(f"{GATEWAY_URL}/internal/workers/heartbeat", json=payload)
                if res.status_code != status.HTTP_200:
                    await client.post(f"{GATEWAY_URL}/internal/workers/register", json=payload)
                    logger.info("Worker registered with Gateway.")
            except Exception as e:
                logger.debug(f"Standby heartbeat ping ({GATEWAY_URL}): {e}")

            await asyncio.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    heartbeat_task = asyncio.create_task(heartbeat_loop())
    yield
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass

app = FastAPI(
    title="SovereignForge Unified Inference Worker",
    version="2.0.0",
    lifespan=lifespan,
)

@app.get("/health")
async def health():
    """Returns worker health and backend status."""
    adapter_health = await active_adapter.health()
    return {
        "status": adapter_health.get("status", "healthy"),
        "worker_name": WORKER_NAME,
        "runtime": INFERENCE_RUNTIME,
        "adapter_info": adapter_health,
    }

@app.post("/worker/v1/generate")
async def generate(req: WorkerGenerateRequest):
    """Unified generation endpoint supporting streaming SSE and JSON payloads."""
    if req.stream:
        async def stream_wrapper() -> AsyncGenerator[str, None]:
            if req.messages:
                stream_gen = active_adapter.stream_chat(
                    messages=req.messages,
                    sampling_params=req.sampling_params,
                    model=req.model,
                    request_id=req.request_id,
                )
            else:
                stream_gen = active_adapter.stream_completion(
                    prompt=req.prompt or "",
                    sampling_params=req.sampling_params,
                    model=req.model,
                    request_id=req.request_id,
                )

            async for chunk in stream_gen:
                yield f"data: {json.dumps(chunk)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            stream_wrapper(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
        )
    else:
        if req.messages:
            # Aggregate from stream
            content = ""
            async for chunk in active_adapter.stream_chat(req.messages, req.sampling_params, req.model, req.request_id):
                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                content += delta
            return JSONResponse(content={
                "id": req.request_id,
                "object": "chat.completion",
                "created": int(time.time()),
                "model": req.model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 25, "completion_tokens": len(content.split())}
            })
        else:
            res = await active_adapter.generate_completion(
                prompt=req.prompt or "",
                sampling_params=req.sampling_params,
                model=req.model,
                request_id=req.request_id,
            )
            return JSONResponse(content=res)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
