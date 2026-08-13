import argparse
import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List

import httpx
from tabulate import tabulate

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("benchmark-harness")

async def run_benchmark_task(client: httpx.AsyncClient, base_url: str, api_key: str, task: Dict[str, Any], model: str) -> Dict[str, Any]:
    """Executes a single benchmark task against SovereignForge and measures latency/TTFT."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    task_type = task.get("type", "chat")
    task_id = task.get("id")
    task_name = task.get("name")

    start_time = time.perf_counter()
    first_token_time = None
    output_tokens_estimated = 0
    status_str = "PASS"

    try:
        if task_type == "autocomplete":
            payload = {
                "model": model,
                "prompt": task["prompt"],
                "max_tokens": 128,
                "stream": True,
            }
            async with client.stream("POST", f"{base_url}/v1/completions", json=payload, headers=headers) as res:
                if res.status_code != 200:
                    return {
                        "id": task_id,
                        "name": task_name,
                        "type": task_type,
                        "ttft_ms": -1,
                        "total_ms": -1,
                        "tokens": 0,
                        "tps": 0,
                        "status": f"HTTP {res.status_code}",
                    }
                async for line in res.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        if first_token_time is None:
                            first_token_time = (time.perf_counter() - start_time) * 1000
                        output_tokens_estimated += 1

        elif task_type == "edit":
            payload = {
                "model": model,
                "input": task["input"],
                "instruction": task["instruction"],
                "stream": True,
            }
            async with client.stream("POST", f"{base_url}/v1/edits", json=payload, headers=headers) as res:
                if res.status_code != 200:
                    return {
                        "id": task_id,
                        "name": task_name,
                        "type": task_type,
                        "ttft_ms": -1,
                        "total_ms": -1,
                        "tokens": 0,
                        "tps": 0,
                        "status": f"HTTP {res.status_code}",
                    }
                async for line in res.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        if first_token_time is None:
                            first_token_time = (time.perf_counter() - start_time) * 1000
                        output_tokens_estimated += 1

        else:  # chat
            payload = {
                "model": model,
                "messages": task["messages"],
                "stream": True,
            }
            async with client.stream("POST", f"{base_url}/v1/chat", json=payload, headers=headers) as res:
                if res.status_code != 200:
                    return {
                        "id": task_id,
                        "name": task_name,
                        "type": task_type,
                        "ttft_ms": -1,
                        "total_ms": -1,
                        "tokens": 0,
                        "tps": 0,
                        "status": f"HTTP {res.status_code}",
                    }
                async for line in res.aiter_lines():
                    if line.startswith("data: ") and not line.endswith("[DONE]"):
                        if first_token_time is None:
                            first_token_time = (time.perf_counter() - start_time) * 1000
                        output_tokens_estimated += 1

        total_time_ms = (time.perf_counter() - start_time) * 1000
        ttft = first_token_time if first_token_time is not None else total_time_ms
        gen_duration_sec = max(0.001, (total_time_ms - ttft) / 1000.0)
        tps = output_tokens_estimated / gen_duration_sec

        return {
            "id": task_id,
            "name": task_name,
            "type": task_type,
            "ttft_ms": round(ttft, 1),
            "total_ms": round(total_time_ms, 1),
            "tokens": output_tokens_estimated,
            "tps": round(tps, 1),
            "status": status_str,
        }

    except Exception as e:
        return {
            "id": task_id,
            "name": task_name,
            "type": task_type,
            "ttft_ms": -1,
            "total_ms": -1,
            "tokens": 0,
            "tps": 0,
            "status": f"ERROR: {str(e)[:25]}",
        }

async def main():
    parser = argparse.ArgumentParser(description="SovereignForge AI Model & Latency Benchmark Runner")
    parser.add_argument("--endpoint", default="http://localhost:8000", help="Gateway endpoint URL")
    parser.add_argument("--api-key", default="sk_live_dev_test_12345", help="API Key")
    parser.add_argument("--model", default="mock-qwen-32b", help="Model ID to evaluate")
    parser.add_argument("--tasks", default=str(Path(__file__).parent / "tasks.json"), help="Tasks JSON path")
    args = parser.parse_args()

    tasks_path = Path(args.tasks)
    if not tasks_path.exists():
        logger.error(f"Tasks file not found at: {tasks_path}")
        return

    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    logger.info(f"Loaded {len(tasks)} benchmark task(s). Target: {args.endpoint} | Model: {args.model}")

    results = []
    async with httpx.AsyncClient(timeout=30.0) as client:
        for t in tasks:
            logger.info(f"Running [{t.get('type')}] {t.get('name')}...")
            res = await run_benchmark_task(client, args.endpoint, args.api_key, t, args.model)
            results.append(res)

    print("\n" + "=" * 80)
    print(f"       SOVEREIGNFORGE BENCHMARK SUMMARY REPORT (Model: {args.model})")
    print("=" * 80)

    table_data = [
        [
            r["id"],
            r["name"],
            r["type"],
            f"{r['ttft_ms']}ms" if r["ttft_ms"] > 0 else "N/A",
            f"{r['total_ms']}ms" if r["total_ms"] > 0 else "N/A",
            r.get("tokens", 0),
            f"{r['tps']} tok/s" if r["tps"] > 0 else "N/A",
            r["status"],
        ]
        for r in results
    ]
    headers = ["Task ID", "Name", "Type", "TTFT (ms)", "Total (ms)", "Tokens", "Throughput", "Status"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    valid_ttfts = [r["ttft_ms"] for r in results if r["ttft_ms"] > 0]
    valid_tps = [r["tps"] for r in results if r["tps"] > 0]

    avg_ttft = sum(valid_ttfts) / max(1, len(valid_ttfts)) if valid_ttfts else 0.0
    avg_tps = sum(valid_tps) / max(1, len(valid_tps)) if valid_tps else 0.0

    print(f"\n📊 Aggregate KPIs:")
    print(f"   • Mean Time To First Token (TTFT): {avg_ttft:.1f}ms (Target: < 250ms)")
    print(f"   • Mean Token Throughput:          {avg_tps:.1f} tokens/sec (Target: > 40 tokens/sec)")
    print("=" * 80 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
