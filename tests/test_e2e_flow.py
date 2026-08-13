import asyncio
import json
import logging
import sys
import time
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("e2e-test")

GATEWAY_URL = "http://localhost:8000"
DEV_API_KEY = "sk_live_dev_test_12345"

async def run_e2e_integration_tests():
    headers = {
        "Authorization": f"Bearer {DEV_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        logger.info("=== Starting SovereignForge & PrivyCode E2E Integration Suite ===")

        # 1. Gateway Health
        logger.info("1. Testing Gateway Health (/health)...")
        res = await client.get(f"{GATEWAY_URL}/health")
        assert res.status_code == 200, f"Gateway health check failed: {res.text}"
        data = res.json()
        assert data["status"] == "healthy"
        logger.info("   -> PASSED: Gateway is healthy.")

        # 2. Authenticated Profile (/v1/me)
        logger.info("2. Testing User Profile (/v1/me)...")
        res = await client.get(f"{GATEWAY_URL}/v1/me", headers=headers)
        assert res.status_code == 200, f"User profile check failed: {res.text}"
        user = res.json()
        assert "email" in user
        logger.info(f"   -> PASSED: Authenticated user: {user['email']} (role: {user['role']})")

        # 3. Monthly Usage & Rate Limit (/v1/me/usage)
        logger.info("3. Testing Quota & Telemetry (/v1/me/usage)...")
        res = await client.get(f"{GATEWAY_URL}/v1/me/usage", headers=headers)
        assert res.status_code == 200, f"Usage check failed: {res.text}"
        usage = res.json()
        assert "monthly_token_limit" in usage
        logger.info(f"   -> PASSED: Quota: {usage['tokens_used_this_month']}/{usage['monthly_token_limit']} tokens used.")

        # 4. List Models (/v1/models)
        logger.info("4. Testing Model Profiles (/v1/models)...")
        res = await client.get(f"{GATEWAY_URL}/v1/models", headers=headers)
        assert res.status_code == 200, f"Model listing failed: {res.text}"
        models = res.json()["data"]
        assert len(models) > 0
        logger.info(f"   -> PASSED: {len(models)} active model profile(s) found.")

        # 5. Multi-File Context Chat with SSE Streaming (POST /v1/chat)
        logger.info("5. Testing Multi-File Chat Streaming (POST /v1/chat)...")
        chat_payload = {
            "model": "mock-qwen-32b",
            "mode": "balanced",
            "messages": [{"role": "user", "content": "How do we handle zero retention?"}],
            "context_files": [
                {
                    "path": "src/security.py",
                    "content": "class Security: def sanitize(self): return True",
                    "selection_range": {"start_line": 1, "end_line": 2},
                }
            ],
            "stream": True,
        }

        chunks_received = 0
        start_t = time.perf_counter()
        first_token_time = None

        async with client.stream("POST", f"{GATEWAY_URL}/v1/chat", json=chat_payload, headers=headers) as chat_res:
            assert chat_res.status_code == 200, f"Chat endpoint failed: {chat_res.status_code}"
            async for line in chat_res.aiter_lines():
                if line.startswith("data: "):
                    if first_token_time is None:
                        first_token_time = (time.perf_counter() - start_t) * 1000
                    chunks_received += 1

        assert chunks_received > 0, "No SSE stream chunks received."
        logger.info(f"   -> PASSED: Received {chunks_received} chunks (TTFT: {first_token_time:.2f}ms).")

        # 6. Fill-in-the-Middle Code Completion (POST /v1/completions)
        logger.info("6. Testing FIM Inline Code Completion (POST /v1/completions)...")
        fim_payload = {
            "model": "mock-qwen-7b",
            "prompt": "<|fim_prefix|>def add(a, b):\n<|fim_suffix|>\n    return c<|fim_middle|>",
            "max_tokens": 64,
            "stream": False,
        }
        res = await client.post(f"{GATEWAY_URL}/v1/completions", json=fim_payload, headers=headers)
        assert res.status_code == 200, f"FIM completion failed: {res.text}"
        comp = res.json()
        assert "choices" in comp
        logger.info("   -> PASSED: FIM completion generated successfully.")

        # 7. Code Edits / Refactoring (POST /v1/edits)
        logger.info("7. Testing Code Edits & Diff Generation (POST /v1/edits)...")
        edit_payload = {
            "model": "mock-qwen-32b",
            "input": "def slow(): time.sleep(1)",
            "instruction": "Convert to async coroutine",
            "file_path": "worker.py",
            "language": "python",
            "stream": False,
        }
        res = await client.post(f"{GATEWAY_URL}/v1/edits", json=edit_payload, headers=headers)
        assert res.status_code == 200, f"Edit endpoint failed: {res.text}"
        logger.info("   -> PASSED: Code edit executed successfully.")

        logger.info("=== ALL E2E INTEGRATION TESTS PASSED (7/7) ===")

if __name__ == "__main__":
    try:
        asyncio.run(run_e2e_integration_tests())
    except Exception as e:
        logger.error(f"E2E Test Failure: {e}")
        sys.exit(1)
