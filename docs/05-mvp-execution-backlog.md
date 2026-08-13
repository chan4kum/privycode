# MVP Execution Backlog

This backlog breaks down the SovereignForge and PrivyCode implementation into highly granular, agent-executable tasks. It spans end-to-end from monorepo initialization to the VS Code extension integration and benchmarking.

Agents can use this document to explicitly track progress by marking the checkboxes (`[x]`).

## Phase 0: Repository & Environment Setup
- [x] **ENG-000**: Initialize monorepo structure (e.g., Turborepo or simple directory structure) with `apps/api`, `apps/vscode-extension`, `services/mock-worker`, `packages/contracts`, `packages/db`, `packages/config`.
- [x] **ENG-001**: Setup `docker-compose.yml` with PostgreSQL (metadata) and Redis (rate-limiting & queues).
- [x] **ENG-002**: Setup shared configuration package (`packages/config`) using `pydantic-settings` to load `.env` variables securely for all Python services.

## Phase 1: Contracts and Database Schema
- [x] **ENG-010**: Define Pydantic request/response schemas for Auth and User (`/v1/auth/login`, `/v1/me`) in `packages/contracts`.
- [x] **ENG-011**: Define Pydantic schemas for Models and Usage (`/v1/models`, `/v1/me/usage`) in `packages/contracts`.
- [x] **ENG-012**: Define Pydantic schemas for Coding (`/v1/chat`, `/v1/edits`, `/v1/completions`) in `packages/contracts`.
- [x] **ENG-013**: Initialize SQLAlchemy and Alembic in `packages/db`. Configure database connection strings.
- [x] **ENG-014**: Create SQLAlchemy models for `organizations`, `users`, `api_keys`, `plans`. Generate migration.
- [x] **ENG-015**: Create SQLAlchemy models for `model_registry`, `inference_workers`, `usage_records`, `benchmark_results`. Generate migration.
- [x] **ENG-016**: Create DB seed script to insert default plans (Free, Pro), a mock test organization/user, and initial `model_registry` routes.

## Phase 2: Mock Inference Worker
- [x] **ENG-020**: Initialize `services/mock-worker` as a FastAPI application with a basic `/health` endpoint.
- [x] **ENG-021**: Implement `/worker/v1/generate` in `mock-worker` to return deterministic, mocked SSE streams (simulating a fast LLM).
- [x] **ENG-022**: Implement worker self-registration loop that pings the Gateway's internal worker API (`/internal/workers/heartbeat`) every 10 seconds.

## Phase 3: API Gateway & Auth
- [x] **ENG-030**: Initialize `apps/api` FastAPI app with standard middleware (Request ID, CORS, Structured Logging, Error Handler).
- [x] **ENG-031**: Implement API Key authentication dependency validating Bearer tokens against the `api_keys` table using SHA-256 hash matching.
- [x] **ENG-032**: Implement `/v1/me` and `/v1/me/usage` endpoints to return authenticated user details and quota status.
- [x] **ENG-033**: Implement internal Worker Registry endpoints (`POST /internal/workers/register`, `POST /internal/workers/heartbeat`) to track active inference workers.
- [x] **ENG-034**: Implement Redis-based Token Bucket rate limiting middleware to protect the API from spam.

## Phase 4: API Gateway Core AI Routes
- [x] **ENG-040**: Implement basic Model Router logic. Select an active model from the `model_registry` and verify worker health before forwarding.
- [x] **ENG-041**: Implement `POST /v1/chat` endpoint forwarding to the selected worker and streaming SSE responses to the client.
- [x] **ENG-042**: Implement `POST /v1/edits` endpoint forwarding to the worker.
- [x] **ENG-043**: Implement `POST /v1/completions` endpoint for FIM logic, optimized for $< 30\text{ms}$ gateway overhead.
- [x] **ENG-044**: Implement Usage Telemetry tracking. Trap `ClientDisconnect` / `BackgroundTasks` to record `prompt_tokens`, `completion_tokens`, and `latency_ms` to `usage_records` even if the stream drops.

## Phase 5: VS Code Extension (PrivyCode)
- [x] **ENG-050**: Scaffold `apps/vscode-extension` (TypeScript, Webpack) and set up the VS Code API integration.
- [x] **ENG-051**: Implement extension settings (`privycode.apiUrl`, `privycode.apiKey`) and build a connectivity status bar item (`$(lock) PrivyCode: Connected`).
- [x] **ENG-052**: Implement FIM logic: extract prefix/suffix around cursor and apply a 250ms debounce on keystrokes.
- [x] **ENG-053**: Register `vscode.languages.registerInlineCompletionItemProvider` to call `/v1/completions` and display ghost text.
- [x] **ENG-054**: Scaffold the Webview Sidebar for the Chat UI (React/HTML).
- [x] **ENG-055**: Implement context extraction for Chat (read current active file and active text selection).
- [x] **ENG-056**: Wire the Sidebar Chat UI to `/v1/chat` API with streaming response rendering and markdown syntax highlighting.
- [x] **ENG-057**: Register `Cmd+I` Code Lens / Quick Pick command to capture user instructions over a text selection.
- [x] **ENG-058**: Wire the Edit Code Lens to `/v1/edits` and display the generated diff using VS Code's native diff editor.

## Phase 6: Integration & Benchmarking
- [x] **ENG-060**: Write an end-to-end Python test script simulating an extension user completing a FIM request and Chat request against the Mock Worker.
- [x] **ENG-061**: Build `services/benchmark` Python CLI harness.
- [x] **ENG-062**: Run benchmark harness with sample code snippets to verify exact TTFT (Time To First Token) and latency logging metrics.

## Phase 7: Real GPU Inference & Multi-Backend Engine
- [x] **ENG-070**: Implement multi-backend LLM adapters for vLLM, Ollama, Groq, and Mock in `services/inference_worker`.
- [x] **ENG-071**: Implement semantic FIM context windowing engine (`apps/api/services/fim_context.py`) preserving top-of-file imports and formatting model-specific tags (Qwen, DeepSeek, StarCoder).
- [x] **ENG-072**: Enhance ModelRouter with dynamic fallback and provider degradation handling.
- [x] **ENG-073**: Write unit tests for FIM sliding windowing and LLM adapters (`tests/test_fim_context.py`, `tests/test_inference_adapters.py`).

