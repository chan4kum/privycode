import asyncio
import hashlib
import json
import logging
import os
import sys
import time
import uuid
from typing import List

import httpx
import pytest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stress-edge-test")

BASE_URL = os.getenv("GATEWAY_URL", "http://localhost:8000")
DEV_API_KEY = "sk_live_dev_test_12345"
HEADERS = {"Authorization": f"Bearer {DEV_API_KEY}", "Content-Type": "application/json"}


# ==============================================================================
# 1. EDGE CASE TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_edge_missing_auth_header():
    """Edge Case: Request without Authorization header must return HTTP 401."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        res = await client.get("/v1/me")
        assert res.status_code == 401
        data = res.json()
        assert "error" in data
        assert "Missing or invalid" in data["error"]["message"]


@pytest.mark.asyncio
async def test_edge_invalid_bearer_token():
    """Edge Case: Malformed or non-existent API key must return HTTP 401."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        # Bad scheme
        res1 = await client.get("/v1/me", headers={"Authorization": "Basic 12345"})
        assert res1.status_code == 401

        # Non-existent key
        res2 = await client.get("/v1/me", headers={"Authorization": "Bearer sk_live_fake_key_99999"})
        assert res2.status_code == 401


@pytest.mark.asyncio
async def test_edge_empty_chat_messages_422():
    """Edge Case: Empty chat messages list must fail with HTTP 422 Unprocessable Entity."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        res = await client.post("/v1/chat", headers=HEADERS, json={"messages": [], "model": "mock-qwen-32b"})
        assert res.status_code == 422


@pytest.mark.asyncio
async def test_edge_unknown_model_fallback():
    """Edge Case: Unknown model should gracefully route to default balanced model."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        res = await client.post(
            "/v1/completions",
            headers=HEADERS,
            json={
                "prompt": "def add(a, b):",
                "model": "non-existent-super-model-9000",
                "max_tokens": 10,
            },
        )
        assert res.status_code == 200
        assert "data: " in res.text


@pytest.mark.asyncio
async def test_edge_secret_redactor_and_zero_retention_headers():
    """Edge Case: Prompt containing AWS keys and DB URI must be redacted with zero-retention headers returned."""
    sensitive_prompt = (
        "Check AWS key AKIAIOSFODNN7EXAMPLE and connect to postgresql://admin:SecretPass123@10.0.0.1:5432/db"
    )
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        res = await client.post(
            "/v1/completions",
            headers=HEADERS,
            json={"prompt": sensitive_prompt, "max_tokens": 10},
        )
        assert res.status_code == 200
        # Check Compliance Headers
        assert res.headers.get("X-PrivyCode-Zero-Retention") == "Verified"
        assert res.headers.get("X-PrivyCode-Audit-Signature", "").startswith("sig_")
        redacted_entities = res.headers.get("X-PrivyCode-Redacted-Entities", "").lower()
        assert "aws_access_key" in redacted_entities
        assert "db_password" in redacted_entities or "db" in redacted_entities


@pytest.mark.asyncio
async def test_edge_security_headers():
    """Edge Case: Verify all enterprise security headers are present on responses."""
    async with httpx.AsyncClient(base_url=BASE_URL) as client:
        res = await client.get("/health")
        assert res.status_code == 200
        assert res.headers.get("Strict-Transport-Security") == "max-age=31536000; includeSubDomains"
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "SAMEORIGIN"
        assert res.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


# ==============================================================================
# 2. CONCURRENCY & STRESS LOAD HARNESS
# ==============================================================================

async def send_single_completion(client: httpx.AsyncClient, req_id: int) -> dict:
    start = time.perf_counter()
    try:
        res = await client.post(
            "/v1/completions",
            headers=HEADERS,
            json={
                "prompt": f"// Request {req_id}\nfunction computeSum(x, y) {{\n",
                "suffix": "\n}",
                "max_tokens": 15,
            },
            timeout=10.0,
        )
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "req_id": req_id,
            "status_code": res.status_code,
            "latency_ms": elapsed,
            "success": res.status_code == 200,
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "req_id": req_id,
            "status_code": 0,
            "latency_ms": elapsed,
            "success": False,
            "error": str(e),
        }


async def send_single_chat_stream(client: httpx.AsyncClient, req_id: int) -> dict:
    start = time.perf_counter()
    chunks = 0
    ttft = 0.0
    try:
        async with client.stream(
            "POST",
            "/v1/chat",
            headers=HEADERS,
            json={
                "messages": [{"role": "user", "content": f"Explain stress test concurrency for worker {req_id}"}],
                "stream": True,
            },
            timeout=10.0,
        ) as res:
            first_chunk_received = False
            async for line in res.aiter_lines():
                if line.startswith("data: ") and not line.startswith("data: [DONE]"):
                    if not first_chunk_received:
                        ttft = (time.perf_counter() - start) * 1000
                        first_chunk_received = True
                    chunks += 1
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "req_id": req_id,
            "success": chunks > 0,
            "chunks": chunks,
            "ttft_ms": ttft,
            "total_ms": elapsed,
        }
    except Exception as e:
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "req_id": req_id,
            "success": False,
            "chunks": 0,
            "ttft_ms": 0.0,
            "total_ms": elapsed,
            "error": str(e),
        }


@pytest.mark.asyncio
async def test_stress_concurrent_completions():
    """Stress Test: Spawns 50 parallel concurrent FIM completion requests."""
    NUM_REQUESTS = 50
    logger.info(f"\n⚡ Starting Concurrency Stress Test: {NUM_REQUESTS} parallel requests...")

    limits = httpx.Limits(max_connections=100, max_keepalive_connections=50)
    async with httpx.AsyncClient(base_url=BASE_URL, limits=limits) as client:
        start_time = time.perf_counter()
        tasks = [send_single_completion(client, i) for i in range(NUM_REQUESTS)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

    successful = [r for r in results if r["success"]]
    rate_limited = [r for r in results if r["status_code"] == 429]
    latencies = sorted([r["latency_ms"] for r in successful])

    p50 = latencies[len(latencies) // 2] if latencies else 0
    p95 = latencies[int(len(latencies) * 0.95)] if latencies else 0
    p99 = latencies[int(len(latencies) * 0.99)] if latencies else 0
    rps = NUM_REQUESTS / total_time

    logger.info(f"📊 Stress Test Results ({NUM_REQUESTS} requests in {total_time:.2f}s):")
    logger.info(f"   • Successful (HTTP 200): {len(successful)}/{NUM_REQUESTS} ({len(successful)/NUM_REQUESTS*100:.1f}%)")
    logger.info(f"   • Rate Limited (HTTP 429): {len(rate_limited)}")
    logger.info(f"   • Throughput: {rps:.1f} Req/Sec")
    logger.info(f"   • Latency p50: {p50:.1f}ms | p95: {p95:.1f}ms | p99: {p99:.1f}ms")

    assert len(successful) + len(rate_limited) == NUM_REQUESTS
    assert len(successful) >= 30  # At least 30 successful within rate-limit bucket


@pytest.mark.asyncio
async def test_stress_concurrent_chat_streams():
    """Stress Test: Spawns 20 parallel concurrent SSE multi-turn token streams."""
    NUM_STREAMS = 20
    logger.info(f"\n⚡ Starting SSE Stream Stress Test: {NUM_STREAMS} parallel streams...")

    limits = httpx.Limits(max_connections=50, max_keepalive_connections=25)
    async with httpx.AsyncClient(base_url=BASE_URL, limits=limits) as client:
        start_time = time.perf_counter()
        tasks = [send_single_chat_stream(client, i) for i in range(NUM_STREAMS)]
        results = await asyncio.gather(*tasks)
        total_time = time.perf_counter() - start_time

    successful = [r for r in results if r["success"]]
    ttfts = sorted([r["ttft_ms"] for r in successful if r["ttft_ms"] > 0])
    mean_ttft = sum(ttfts) / len(ttfts) if ttfts else 0

    logger.info(f"📊 Stream Stress Results ({NUM_STREAMS} parallel streams in {total_time:.2f}s):")
    logger.info(f"   • Streams Completed: {len(successful)}/{NUM_STREAMS}")
    logger.info(f"   • Mean TTFT: {mean_ttft:.1f}ms")
    logger.info(f"   • Min TTFT: {ttfts[0]:.1f}ms | Max TTFT: {ttfts[-1]:.1f}ms" if ttfts else "")

    assert len(successful) >= 15


if __name__ == "__main__":
    async def main():
        print("Running Edge Cases and Stress Test Harness...")
        await test_stress_concurrent_completions()
        await test_stress_concurrent_chat_streams()
        print("✓ All Stress Tests Passed!")

    asyncio.run(main())
