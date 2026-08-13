# MVP Product Requirements & Developer User Flows

## 1. Product Vision & Boundaries
**PrivyCode** is a sovereign, privacy-first AI coding companion (VS Code Extension & CLI) powered by the **SovereignForge** self-hostable control plane. It delivers state-of-the-art coding assistance with zero-retention privacy guarantees, customizable model routing, and local/private GPU hosting.

### The MVP boundaries include:
* VS Code Extension for the developer environment.
* SovereignForge API Gateway for authentication, metering, and routing.
* Model Router for traffic direction.
* Inference compute capabilities (vLLM, Mock for dev, and optional Groq for fast mode).
* PostgreSQL for metadata and Redis for caching/queues.

---

## 2. Developer User Flows

### Flow 1: First-Time Setup & Authentication
1. Developer installs the `privycode` VS Code extension from the marketplace (or side-loads the VSIX).
2. Extension prompts for the SovereignForge Endpoint URL (e.g., `http://localhost:8000` for local dev or `https://api.privycode.internal` for self-hosted enterprise).
3. Extension prompts for the API Key (`sk_live_...`).
4. Extension calls `GET /v1/models` and `GET /v1/me/usage` to validate credentials.
5. VS Code status bar icon turns green: `$(lock) PrivyCode: Connected`.

### Flow 2: Ghost-Text Inline Completion (Fill-In-The-Middle)
1. Developer types code in the active editor.
2. Extension debounces keystrokes (e.g., 250ms).
3. Extension extracts the prefix (preceding ~2,000 tokens) and suffix (following ~500 tokens).
4. Sends `POST /v1/completions` with streaming enabled (`stream: true`).
5. SovereignForge routes to an ultra-fast FIM model (e.g., `qwen2.5-coder-7b-instruct` on local GPU or Groq).
6. First token renders inline in `< 200ms`.
7. Developer presses `Tab` to accept the suggestion or continues typing to dismiss it.
8. **Error Handling**: If the connection drops or the worker crashes mid-stream, the extension silently aborts the completion to avoid inserting partial/broken code and resets state.

### Flow 3: Interactive Chat & Multi-File Repository Context
1. Developer opens the sidebar chat (`Ctrl+Shift+L` or `Cmd+Shift+L`).
2. Developer types a question, optionally tagging `@repo` (e.g., `@repo How is authentication handled in this service?`).
3. Extension parses the tag, scans local BM25/AST index, grabs the top 5 relevant file snippets.
4. Bundles snippets into the request payload and sends `POST /v1/chat` with SSE streaming.
5. SovereignForge validates user limits, routes to a large model (e.g., 32B/70B).
6. Code snippets stream to the UI with copyable markdown and "Apply to File" buttons.
7. **Error Handling**: If the worker OOMs mid-stream, the Chat UI displays a graceful inline error ("Connection interrupted. The worker may be overloaded.") while retaining the partial response.

### Flow 4: Inline Diff-Based Code Edits
1. Developer highlights 20 lines of code and presses `Cmd+I` / `Ctrl+I`.
2. Input bar appears: *"Refactor this to use async/await with error boundaries"*.
3. Extension sends `POST /v1/edits` containing the instruction, the highlighted input, and file context.
4. Model generates a structured unified diff or replacement block.
5. VS Code renders an inline native diff editor. 
6. Developer reviews the changes and clicks **Accept (`Cmd+Enter`)** or **Reject (`Escape`)**.
