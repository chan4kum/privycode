# API Specification

All endpoints communicate via standard JSON contracts and Server-Sent Events (`text/event-stream`) for streaming. Standard Bearer token authentication is required: `Authorization: Bearer sk_...`.

## 1. Developer Facing Endpoints

### `POST /v1/chat`
Conversational chat with optional retrieval context chunks and streaming.

**Request Schema (`application/json`)**:
```json
{
  "model": "qwen2.5-coder-32b",
  "messages": [
    { "role": "system", "content": "You are PrivyCode..." },
    { "role": "user", "content": "Refactor the connection pool." }
  ],
  "context_files": [
    {
      "path": "src/database/db.py",
      "content": "import psycopg2...",
      "selection_range": {"start_line": 1, "end_line": 25}
    }
  ],
  "temperature": 0.2,
  "max_tokens": 4096,
  "stream": true
}
```

### `POST /v1/edits`
Targeted code modifications generating precise replacement diffs.

**Request Schema (`application/json`)**:
```json
{
  "model": "qwen2.5-coder-32b",
  "input": "def calc(total): return total * 0.08",
  "instruction": "Add input validation and use Decimal types",
  "file_path": "finance/tax.py",
  "language": "python",
  "temperature": 0.1,
  "stream": false
}
```

### `POST /v1/completions` (FIM)
High-throughput low-latency inline code completions.

**Request Schema (`application/json`)**:
```json
{
  "model": "qwen2.5-coder-7b",
  "prompt": "<|fim_prefix|>def compute():\n<|fim_suffix|>\nreturn result<|fim_middle|>",
  "max_tokens": 128,
  "temperature": 0.0,
  "stop": ["\n\n", "<|fim_prefix|>", "<|fim_suffix|>", "<|fim_middle|>", "<|file_separator|>"],
  "stream": true
}
```

### `GET /v1/models`
Returns a list of active model backend profiles.

**Response Schema (`200 OK`)**:
```json
{
  "object": "list",
  "data": [
    {
      "id": "qwen2.5-coder-32b",
      "name": "Qwen 2.5 Coder 32B Instruct",
      "provider": "vllm",
      "capabilities": ["chat", "edits"],
      "context_window": 32768
    }
  ]
}
```

### `GET /v1/me/usage`
Current user quota, token consumption, and rate limit status.

**Response Schema (`200 OK`)**:
```json
{
  "user_id": "usr_abc123",
  "tier": "pro_seat",
  "monthly_token_limit": 50000000,
  "tokens_used_this_month": 4210340,
  "tokens_remaining": 45789660,
  "rate_limit": {
    "requests_per_minute": 60,
    "requests_remaining": 58,
    "reset_in_seconds": 42
  }
}
```

## 2. Internal Worker APIs (vLLM / Mock)

### `POST /worker/v1/generate`
```json
{
  "request_id": "req_uuid4",
  "model": "qwen2.5-coder-32b",
  "prompt": "...",
  "sampling_params": {
    "temperature": 0.2,
    "max_tokens": 2048,
    "stop": ["<|endoftext|>"]
  }
}
```

### `GET /worker/v1/health`
```json
{
  "status": "healthy",
  "gpu_utilization_percent": 68.4,
  "kv_cache_usage_percent": 42.1,
  "active_requests": 3
}
```

## 3. Admin & Control Plane APIs
* `GET /admin/v1/users`: List users and allocated seats.
* `POST /admin/v1/users`: Create user and generate API keys.
* `GET /admin/v1/metrics/overview`: Aggregated requests/sec, P95 latency, error rates.
* `POST /admin/v1/models/routes`: Dynamically update routing weights.

## 4. Tokenization & Context Limits
The Gateway MUST calculate token lengths before routing requests to enforce quotas and prevent worker OOM errors. 
* **Standardization**: The Gateway will use the HuggingFace `transformers` tokenizer matching the primary model (e.g., `Qwen2.5-Coder`) rather than an approximation like `tiktoken`. This ensures exact parity with the vLLM worker's KV cache.
* **Truncation**: If the context plus prompt exceeds the `max_context_tokens`, the Gateway will reject the request with `413 Payload Too Large` rather than silently truncating, to maintain predictable behavior.
