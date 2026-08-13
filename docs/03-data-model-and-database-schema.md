# Data Model & Database Schema

## 1. Entity Relationship Overview
The database uses PostgreSQL to handle metadata and usage telemetry while adhering strictly to zero-retention policies for source code and prompts.

**Core Entities**:
* `Organizations`: Top-level tenant.
* `Users`: Developers within an organization.
* `API Keys`: Hashed access keys.
* `Model Registry`: Configured inference routes and pricing.
* `Usage Records`: Anonymized telemetry (token counts, latency, status) containing NO code.

## 2. PostgreSQL DDL (`schema.sql`)

```sql
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Organizations
CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    privacy_tier VARCHAR(50) DEFAULT 'zero_retention' 
      CHECK (privacy_tier IN ('zero_retention', 'strict_private', 'audit_enabled')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(150),
    role VARCHAR(50) DEFAULT 'developer' CHECK (role IN ('owner', 'admin', 'developer', 'viewer')),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_org_id ON users(org_id);
CREATE INDEX idx_users_email ON users(email);

-- API Keys (Store SHA-256 hash only)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    key_hash VARCHAR(64) UNIQUE NOT NULL,
    key_prefix VARCHAR(12) NOT NULL,
    name VARCHAR(100) NOT NULL DEFAULT 'Default Key',
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);
CREATE INDEX idx_api_keys_user ON api_keys(user_id);

-- Plans
CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(50) UNIQUE NOT NULL,
    monthly_request_limit INT,
    monthly_token_limit INT,
    max_context_tokens INT DEFAULT 32768,
    strong_model_allowed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Model Registry & Routing Profiles
CREATE TABLE model_registry (
    id VARCHAR(100) PRIMARY KEY,
    display_name VARCHAR(150) NOT NULL,
    provider VARCHAR(50) NOT NULL CHECK (provider IN ('vllm', 'mock', 'groq', 'byok')),
    worker_url VARCHAR(255) NOT NULL,
    context_window INT NOT NULL DEFAULT 32768,
    cost_per_1k_prompt_tokens NUMERIC(10, 6) DEFAULT 0.000000,
    cost_per_1k_completion_tokens NUMERIC(10, 6) DEFAULT 0.000000,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Inference Workers
CREATE TABLE inference_workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL,
    runtime VARCHAR(50) NOT NULL,
    base_url VARCHAR(255) NOT NULL,
    status VARCHAR(50) DEFAULT 'offline',
    max_context_tokens INT DEFAULT 32768,
    last_heartbeat_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Usage Records (Anonymized token telemetry - ZERO code stored)
CREATE TABLE usage_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    inference_worker_id UUID REFERENCES inference_workers(id),
    endpoint VARCHAR(50) NOT NULL,
    model_id VARCHAR(100) NOT NULL REFERENCES model_registry(id),
    prompt_tokens INT NOT NULL,
    completion_tokens INT NOT NULL,
    total_tokens INT GENERATED ALWAYS AS (prompt_tokens + completion_tokens) STORED,
    latency_ms INT NOT NULL,
    status_code INT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_user_date ON usage_records(user_id, recorded_at);
CREATE INDEX idx_usage_model ON usage_records(model_id);

-- Benchmark Results
CREATE TABLE benchmark_results (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    model_id VARCHAR(100) NOT NULL REFERENCES model_registry(id) ON DELETE CASCADE,
    benchmark_name VARCHAR(150) NOT NULL,
    quality_score NUMERIC(5, 2),
    latency_ms INT,
    estimated_cost NUMERIC(10, 6),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Repositories (Local index tracking metadata)
CREATE TABLE repositories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    local_hash VARCHAR(100) NOT NULL,
    name VARCHAR(255) NOT NULL,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Repository Files (File-level metadata tracking)
CREATE TABLE repo_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repository_id UUID NOT NULL REFERENCES repositories(id) ON DELETE CASCADE,
    path TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    token_count INT,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

## 3. Data Retention Rules
* **Prompts/Code**: Not retained. Processed exclusively in-memory (RAM) and immediately garbage collected after streaming ends.
* **Usage Records**: Retained for a maximum of 90 days. A scheduled cron job will `DELETE FROM usage_records WHERE recorded_at < NOW() - INTERVAL '90 days'`.

## 4. Redis Schema (Rate Limiting)
To support high-frequency checks without overloading Postgres, the Gateway uses Redis for rate limit enforcement via a Token Bucket algorithm.
* **Key Format**: `ratelimit:{user_id}:{endpoint}`
* **Data Structure**: Redis Hash holding `tokens` (current capacity) and `last_refill` (timestamp).
* **TTL**: Keys expire after 1 hour of inactivity to save memory.
