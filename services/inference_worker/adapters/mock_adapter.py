import asyncio
import time
from typing import Any, AsyncGenerator, Dict, List, Optional
from .base import BaseLLMAdapter, SamplingParams

class MockAdapter(BaseLLMAdapter):
    """High-performance mock inference adapter for testing without local GPU or internet."""

    def __init__(self, base_url: str = "mock://internal", api_key: Optional[str] = None):
        super().__init__(base_url, api_key)

    def _generate_mock_tokens(self, prompt: Optional[str], messages: Optional[List[Dict[str, str]]]) -> List[str]:
        if messages:
            last_msg = messages[-1].get("content", "")
            text = (
                f"```python\n"
                f"# Real-time response to: {last_msg[:40]}...\n"
                f"async def process_data(data: dict) -> dict:\n"
                f"    sanitized = {{k: v for k, v in data.items() if k != 'secret'}}\n"
                f"    return {{'status': 'success', 'data': sanitized}}\n"
                f"```\n"
                f"Zero-retention inference verified."
            )
        elif prompt and "<|fim_prefix|>" in prompt:
            text = "    result = await compute_metrics(tokens, latency)\n    return result"
        else:
            text = "def solution():\n    return 'optimized'"

        words = text.split(" ")
        return [w + " " for w in words[:-1]] + [words[-1]]

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        tokens = self._generate_mock_tokens(None, messages)
        for idx, t in enumerate(tokens):
            await asyncio.sleep(0.015)
            yield {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": t},
                        "finish_reason": "stop" if idx == len(tokens) - 1 else None,
                    }
                ],
                "usage": {
                    "prompt_tokens": 20,
                    "completion_tokens": idx + 1,
                },
            }

    async def stream_completion(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        tokens = self._generate_mock_tokens(prompt, None)
        for idx, t in enumerate(tokens):
            await asyncio.sleep(0.012)
            yield {
                "id": request_id,
                "object": "text_completion.chunk",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "text": t,
                        "delta": {"content": t},
                        "finish_reason": "stop" if idx == len(tokens) - 1 else None,
                    }
                ],
                "usage": {
                    "prompt_tokens": 15,
                    "completion_tokens": idx + 1,
                },
            }

    async def generate_completion(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> Dict[str, Any]:
        tokens = self._generate_mock_tokens(prompt, None)
        text = "".join(tokens)
        return {
            "id": request_id,
            "object": "text_completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "text": text,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": len(tokens),
            },
        }

    async def health(self) -> Dict[str, Any]:
        return {
            "status": "healthy",
            "runtime": "mock",
            "max_context_tokens": 32768,
        }
