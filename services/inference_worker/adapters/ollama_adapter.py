import json
import logging
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
from .base import BaseLLMAdapter, SamplingParams

logger = logging.getLogger("ollama-adapter")

class OllamaAdapter(BaseLLMAdapter):
    """Adapter for local Ollama runtime (supports macOS Metal, CPU, and NVIDIA)."""

    def __init__(self, base_url: str = "http://localhost:11434", api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

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
            "stream": True,
            "options": {
                "temperature": sampling_params.temperature,
                "num_predict": sampling_params.max_tokens,
                "top_p": sampling_params.top_p,
                "stop": sampling_params.stop,
            },
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/chat", json=payload) as res:
                if res.status_code != 200:
                    logger.error(f"Ollama chat error HTTP {res.status_code}")
                    return

                token_idx = 0
                async for line in res.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        done = data.get("done", False)
                        token_idx += 1
                        
                        yield {
                            "id": request_id,
                            "object": "chat.completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": content},
                                    "finish_reason": "stop" if done else None,
                                }
                            ],
                        }
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
            "raw": True,
            "stream": True,
            "options": {
                "temperature": sampling_params.temperature,
                "num_predict": sampling_params.max_tokens,
                "top_p": sampling_params.top_p,
                "stop": sampling_params.stop,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("POST", f"{self.base_url}/api/generate", json=payload) as res:
                if res.status_code != 200:
                    logger.error(f"Ollama completion error HTTP {res.status_code}")
                    return

                async for line in res.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        chunk_text = data.get("response", "")
                        done = data.get("done", False)
                        yield {
                            "id": request_id,
                            "object": "text_completion.chunk",
                            "created": int(time.time()),
                            "model": model,
                            "choices": [
                                {
                                    "index": 0,
                                    "text": chunk_text,
                                    "delta": {"content": chunk_text},
                                    "finish_reason": "stop" if done else None,
                                }
                            ],
                        }
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
            "raw": True,
            "stream": False,
            "options": {
                "temperature": sampling_params.temperature,
                "num_predict": sampling_params.max_tokens,
                "top_p": sampling_params.top_p,
                "stop": sampling_params.stop,
            },
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(f"{self.base_url}/api/generate", json=payload)
            res.raise_for_status()
            data = res.json()
            response_text = data.get("response", "")
            return {
                "id": request_id,
                "object": "text_completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "text": response_text,
                        "message": {"role": "assistant", "content": response_text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                },
            }

    async def health(self) -> Dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    models = [m.get("name") for m in res.json().get("models", [])]
                    return {
                        "status": "healthy",
                        "runtime": "ollama",
                        "available_models": models,
                    }
                return {"status": "degraded", "runtime": "ollama"}
        except Exception as e:
            return {"status": "offline", "runtime": "ollama", "error": str(e)}
