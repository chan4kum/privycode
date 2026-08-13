import pytest
from services.inference_worker.adapters.base import SamplingParams
from services.inference_worker.adapters.mock_adapter import MockAdapter
from services.inference_worker.adapters.ollama_adapter import OllamaAdapter
from services.inference_worker.adapters.vllm_adapter import VLLMAdapter
from services.inference_worker.adapters.groq_adapter import GroqAdapter

@pytest.mark.asyncio
async def test_mock_adapter_stream_chat():
    adapter = MockAdapter()
    params = SamplingParams(temperature=0.2, max_tokens=64)
    messages = [{"role": "user", "content": "hello world"}]

    chunks = []
    async for chunk in adapter.stream_chat(messages, params, "mock-qwen-32b", "req_test_1"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert "choices" in chunks[0]
    assert chunks[-1]["choices"][0]["finish_reason"] == "stop"

@pytest.mark.asyncio
async def test_mock_adapter_stream_completion():
    adapter = MockAdapter()
    params = SamplingParams(temperature=0.0, max_tokens=32)
    prompt = "<|fim_prefix|>def add(a, b):<|fim_suffix|>    return c<|fim_middle|>"

    chunks = []
    async for chunk in adapter.stream_completion(prompt, params, "mock-qwen-7b", "req_test_2"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert "text" in chunks[0]["choices"][0]

@pytest.mark.asyncio
async def test_mock_adapter_health():
    adapter = MockAdapter()
    health = await adapter.health()
    assert health["status"] == "healthy"
    assert health["runtime"] == "mock"

def test_adapter_initialization():
    vllm = VLLMAdapter(base_url="http://localhost:8000")
    assert vllm.base_url == "http://localhost:8000"

    ollama = OllamaAdapter(base_url="http://localhost:11434")
    assert ollama.base_url == "http://localhost:11434"

    groq = GroqAdapter(api_key="gsk_sample")
    assert groq.headers["Authorization"] == "Bearer gsk_sample"
