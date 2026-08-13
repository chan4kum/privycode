from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional
from pydantic import BaseModel, Field

class SamplingParams(BaseModel):
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1)
    stop: List[str] = Field(default_factory=list)
    top_p: float = Field(default=0.95, ge=0.0, le=1.0)

class BaseLLMAdapter(ABC):
    """Abstract interface for LLM inference engines (vLLM, Ollama, Groq, Mock)."""

    def __init__(self, base_url: str, api_key: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    @abstractmethod
    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streams chat completion chunks as standard OpenAI-compatible dictionaries."""
        pass

    @abstractmethod
    async def stream_completion(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Streams raw text completion chunks (FIM)."""
        pass

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        sampling_params: SamplingParams,
        model: str,
        request_id: str,
    ) -> Dict[str, Any]:
        """Non-streaming text completion."""
        pass

    @abstractmethod
    async def health(self) -> Dict[str, Any]:
        """Returns health status and hardware telemetry metrics."""
        pass
