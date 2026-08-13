# Security & Privacy Design

## 1. Zero-Data-Retention (ZDR) Core Rules
1. **No Code Persistence**: Prompt texts, source code snippets, highlighted lines, and AST chunks are streamed strictly in-memory (RAM) through the Gateway to the Inference Worker. They are NEVER written to disk, database, or durable object storage.
2. **Local In-Memory Extension Indexing**: Repository file indexing (BM25 & ctags/AST) runs locally inside the developer's VS Code process. Only the top $K$ relevant snippets selected for a specific prompt leave the client.

## 2. Telemetry and Logging Sanitation
All HTTP access logs and telemetry events must sanitize the `messages`, `prompt`, `diff`, and `input` fields before emission. Logs must only capture anonymized operational metrics.

```python
# Logging Filter Schema
log_payload = {
    "request_id": req.id,
    "user_id": user.id,
    "endpoint": req.url.path,
    "model": req.body.model,
    "prompt_token_count": prompt_tokens, # ONLY token counts
    "completion_token_count": completion_tokens,
    "latency_ms": elapsed_time
}
```

## 3. API Key Handling
* Keys are generated once and only displayed to the user at creation time.
* The backend stores only a one-way SHA-256 hash of the key in the database alongside an identifiable prefix (e.g., `sk_live_abc1`).
* If a key is lost, it cannot be recovered and must be rotated/regenerated.

## 4. External Provider Routing Policy
* **Local / Private GPU (Default)**: Fully air-gapped capable; traffic never leaves the private VPC/cluster.
* **Groq Acceleration Mode (Optional Opt-in)**: Requires explicit organization and developer consent toggled in settings. Code sent is strictly ephemeral per Groq's zero-retention terms.
* **Policy Flag**: `external_inference_allowed = false`
When this policy is set, the Model Router is strictly forbidden from routing traffic to external endpoints (Groq, OpenAI, Anthropic) even as a fallback.

## 5. Enterprise Future Path
* **Air-gapped deployment**: Future support for Helm/Kubernetes packaging to run SovereignForge on entirely isolated networks with zero external internet access.
* **Role-Based Access Control (RBAC)**: Support for custom roles beyond Developer/Admin (e.g., specific repository model access).
* **SSO/SAML**: Enterprise identity provider integration for automated onboarding and offboarding.
