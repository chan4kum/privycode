import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
from .base import BaseLLMAdapter, SamplingParams

logger = logging.getLogger("vllm-adapter")

class VLLMAdapter(BaseLLMAdapter):
    """Adapter for vLLM / TensorRT-LLM OpenAI-compatible endpoints."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: Optional[str] = None):
        super().__init__(base_url, api_key)
        self.headers = {"Content-Type": "application/json"}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": sampling_params.temperature,
            "max_tokens": sampling_params.max_tokens,
            "top_p": sampling_params.top_p,
            "stop": sampling_params.stop,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/v1/chat/completions", json=payload, headers=self.headers) as res:
                if res.status_code != 200:
                    logger.error(f"vLLM chat error HTTP {res.status_code}")
                    return

                async for line in res.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        try:
                            chunk = json.loads(line[6:])
                            yield chunk
                        except Exception:
                            pass

    async def stream_completion(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": sampling_params.temperature,
            "max_tokens": sampling_params.max_tokens,
            "top_p": sampling_params.top_p,
            "stop": sampling_params.stop,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", f"{self.base_url}/v1/completions", json=payload, headers=self.headers) as res:
                if res.status_code != 200:
                    logger.error(f"vLLM completion error HTTP {res.status_code}")
                    return

                async for line in res.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        try:
                            chunk = json.loads(line[6:])
                            yield chunk
                        except Exception:
                            pass

    async def generate_completion(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "prompt": prompt,
            "temperature": sampling_params.temperature,
            "max_tokens": sampling_params.max_tokens,
            "top_p": sampling_params.top_p,
            "stop": sampling_params.stop,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(f"{self.base_url}/v1/completions", json=payload, headers=self.headers)
            res.raise_for_status()
            return res.json()

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/health")
                return {
                    "status": "healthy" if res.status_code == 200 else "degraded",
                    "runtime": "vllm",
                    "base_url": self.base_url,
                }
        except Exception as e:
            return {"status": "offline", "runtime": "vllm", "error": str(e)}
