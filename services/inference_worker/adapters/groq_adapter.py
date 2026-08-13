import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
from .base import BaseLLMAdapter, SamplingParams

logger = logging.getLogger("groq-adapter")

class GroqAdapter(BaseLLMAdapter):
    """Adapter for Groq Cloud zero-retention high-speed inference (Qwen-2.5, Llama-3.3)."""

    def __init__(self, base_url: str = "https://api.groq.com/openai/v1", api_key: Optional[str] = None):
        super().__init__(base_url, api_key)
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key or 'gsk_placeholder'}",
        }

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # Map internal model names to Groq-supported models
        groq_model = "qwen-2.5-coder-32b" if "qwen" in model.lower() else "llama-3.3-70b-versatile"
        payload = {
            "model": groq_model,
            "messages": messages,
            "temperature": sampling_params.temperature,
            "max_tokens": sampling_params.max_tokens,
            "top_p": sampling_params.top_p,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", f"{self.base_url}/chat/completions", json=payload, headers=self.headers) as res:
                if res.status_code != 200:
                    logger.error(f"Groq stream error HTTP {res.status_code}")
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
        # Groq chat format wrap for completion
        messages = [{"role": "user", "content": prompt}]
        async for chunk in self.stream_chat(messages, sampling_params, model, request_id):
            yield chunk

    async def generate_completion(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> Dict[str, Any]:
        groq_model = "qwen-2.5-coder-32b" if "qwen" in model.lower() else "llama-3.3-70b-versatile"
        payload = {
            "model": groq_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": sampling_params.temperature,
            "max_tokens": sampling_params.max_tokens,
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(f"{self.base_url}/chat/completions", json=payload, headers=self.headers)
            res.raise_for_status()
            data = res.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {
                "id": request_id,
                "object": "text_completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "text": content,
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": data.get("usage", {}),
            }

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy" if self.api_key else "degraded",
            "runtime": "groq_cloud",
            "configured": bool(self.api_key),
        }
