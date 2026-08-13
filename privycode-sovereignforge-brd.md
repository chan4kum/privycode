# Business Requirements Document: PrivyCode + SovereignForge

Date: 14 August 2026  
Version: 1.0  
Status: Draft for technical cofounder / investor review

## 1. Executive Summary

PrivyCode + SovereignForge is a two-layer product strategy for low-cost, private, high-performance AI software development and private enterprise AI.

SovereignForge is the private AI infrastructure and control plane. It manages model serving, routing, benchmarking, optimization, deployment, governance, and lifecycle across rented cloud GPUs, private cloud, on-premises infrastructure, and later air-gapped environments.

PrivyCode is the flagship application built on SovereignForge. It is an AI coding assistant and coding agent targeted first at price-sensitive individual developers and small teams who want a cheaper alternative to GitHub Copilot, Cursor, Codex, Cline-style workflows, and enterprise AI coding platforms.

The long-term platform can extend beyond coding into Private RAG and AI Agents, but the MVP should remain focused: build a fast, robust, model-agnostic coding assistant using open-source models, cloud-first rented GPUs, and workload-aware model routing.

The concept is not wholly unique. On-prem LLM deployment, private coding assistants, BYOK coding clients, and optimized inference containers already exist. The realistic opportunity is to build a vendor-neutral optimization and operating layer that continuously identifies the best model + quantization + runtime + GPU configuration for each workload and price target.

## 2. Problem Statement

Individual developers and small teams face three overlapping problems:

1. AI coding tools are becoming essential, but paid plans can feel expensive in price-sensitive markets.
2. Many tools depend on proprietary frontier models, making costs unpredictable and limiting user control.
3. Existing open-source alternatives still leave users to manage model choice, inference providers, local setup, latency, context quality, and cost tradeoffs.

Enterprises face additional problems:

1. Sensitive code, data, and workflows cannot always be sent to public SaaS AI providers.
2. On-prem/private AI deployment is technically difficult: model choice, quantization, GPU sizing, inference runtime, observability, security, and lifecycle management are fragmented.
3. Models change quickly, and enterprises lack continuous workload-specific evaluation to know when to replace or downgrade/upgrade a model.

## 3. Vision

Build a private AI operating layer that makes open-source and self-hosted models practical, efficient, and economically competitive.

Near-term vision:

PrivyCode becomes a low-cost AI coding assistant for developers who want useful coding help below mainstream Copilot/Codex/Cursor price points.

Long-term vision:

SovereignForge becomes the infrastructure-agnostic control plane for private AI workloads: coding, RAG, internal agents, compliance-sensitive copilots, and air-gapped enterprise deployments.

## 4. Product Architecture Principle

The architecture is fixed:

1. SovereignForge: Private AI infrastructure/control plane.
2. PrivyCode: Flagship AI coding application.
3. Future layer: Private RAG applications.
4. Future layer: Private AI Agents.

PrivyCode should not be tightly coupled to one model, one inference engine, one GPU vendor, or one deployment target.

## 5. Goals

### MVP Goals

1. Deliver a usable VS Code-first AI coding assistant using open-source models.
2. Offer a lower-cost developer plan than common paid AI coding tools.
3. Build a cloud-first backend using rented GPUs to avoid early hardware capex.
4. Implement model routing across at least two model classes: fast/cheap and stronger/slower.
5. Benchmark model quality, latency, throughput, and cost per coding task.
6. Support repository context, coding chat, inline edit, basic autocomplete, and simple agentic file edits.
7. Track inference cost per user and enforce allowances so low-cost pricing does not create negative unit economics.

### Enterprise / Later Goals

1. Deploy SovereignForge into private cloud, on-premises, and air-gapped environments.
2. Support Kubernetes-based model serving with observability, policy controls, audit logs, and admin governance.
3. Provide domain-specific model benchmarking and replacement recommendations.
4. Add fine-tuning, LoRA/domain adapters, retrieval augmentation, and private agent orchestration.
5. Support regulated enterprise security requirements: SSO, RBAC, secrets isolation, audit trails, data retention controls, and compliance reporting.

## 6. Non-Goals

### MVP Non-Goals

1. Do not build a full on-prem enterprise appliance in the MVP.
2. Do not train a foundation model from scratch.
3. Do not promise unlimited usage at very low prices.
4. Do not compete directly with frontier coding agents on maximum capability from day one.
5. Do not attempt support for every IDE initially.
6. Do not build Private RAG and enterprise agents before proving the coding use case.

### Long-Term Non-Goals

1. Do not become locked into one model provider, GPU provider, inference runtime, or cloud.
2. Do not position the product as if private AI deployment itself is novel.

## 7. Target Users

### Primary MVP Users

1. Price-sensitive individual developers.
2. Students and early-career engineers.
3. Freelancers and indie hackers.
4. Developers in India and other cost-sensitive markets.
5. Open-source developers comfortable with OSS models but unwilling to manage infrastructure manually.

### Secondary MVP Users

1. Small teams of 2-20 developers.
2. Startups that need coding assistance but want controlled AI spend.
3. Developers who prefer local/private/BYOK options.

### Later Enterprise Users

1. Regulated enterprises.
2. Banks, insurers, healthcare, defense, government, and critical infrastructure.
3. Enterprises with self-hosted GitHub/GitLab/Bitbucket.
4. Companies that need private AI across coding, documents, internal search, and workflows.
5. System integrators deploying private AI for clients.

## 8. Market and Competition

### Pricing Anchors

Current market examples as checked in August 2026:

1. GitHub Copilot offers Free, Pro at $10/month, Pro+ at $39/month, and Max at $100/month for individuals. Business is $19/user/month.
2. Cursor Pro is $20/month and Teams starts at $40/user/month.
3. OpenAI Codex is included in ChatGPT plans, with Plus at $20/month and higher Pro tiers for heavier usage.
4. Cline is free for individual developers, with users paying for AI inference or using their own keys.
5. Tabnine positions private/enterprise AI code assistant plans around $39/user/month and agentic plans around $59/user/month, with support for self-hosted and air-gapped deployments.
6. Sourcegraph/Cody and Sourcegraph Enterprise focus on deep codebase context, enterprise search, self-hosting, and governance.
7. NVIDIA NIM provides optimized inference microservices and enterprise-ready containers across cloud, data center, workstation, and edge environments.

### Competitive Implication

A simple "cheaper Copilot" claim is weak because:

1. GitHub Copilot already has a free tier and a $10 Pro tier.
2. Cline's open-source client is free and supports BYOK.
3. Cursor, Codex, and Copilot have strong distribution, models, and developer mindshare.
4. Enterprise private AI competitors already exist.

PrivyCode must win on a sharper wedge:

1. Lower effective cost through open-source models and routing.
2. Transparent usage limits and cost controls.
3. Better local/private deployment path than mainstream SaaS tools.
4. Workload-aware optimization rather than fixed-model dependency.
5. Strong support for Indian/global price-sensitive developers.

## 9. Differentiation and Honest Caveats

### What Is Not Unique

1. AI coding assistants are not unique.
2. On-prem/private LLM deployment is not unique.
3. Open-source LLM inference is not unique.
4. BYOK/self-hosted coding clients are not unique.
5. Enterprise AI governance is not unique.

### Potential Differentiation

The potential moat is the optimization/control layer:

1. Workload-aware model optimization: route each task to the cheapest model that is good enough.
2. Continuous evaluation/model replacement: benchmark new models and automatically recommend replacements.
3. Domain-specific benchmarking: evaluate models on the customer's actual languages, frameworks, repositories, and task types.
4. Model + runtime + hardware co-optimization: compare vLLM, SGLang, TensorRT-LLM/NIM-style serving, quantization levels, GPU types, batching, cache strategy, and context strategy.
5. Private deployment portability: develop in cloud, deploy to private cloud/on-prem/air-gapped later.
6. Cost transparency: show per-task and per-user AI cost rather than hiding economics behind "unlimited" marketing.

### Caveat

This moat only becomes real if the system collects high-quality benchmarks, learns from production workloads, and materially lowers cost/latency without unacceptable quality loss.

## 10. Product Architecture

### Logical Architecture

```text
Developer / Enterprise User
        |
        v
PrivyCode IDE Extension / CLI / Web Console
        |
        v
SovereignForge API Gateway
        |
        +--> Authentication, tenancy, usage metering
        +--> Policy engine and safety filters
        +--> Context builder and repository index
        +--> Model router
        +--> Evaluation and benchmark service
        +--> Model lifecycle registry
        +--> Observability and cost analytics
        |
        v
Inference Runtime Layer
        |
        +--> vLLM
        +--> SGLang
        +--> TensorRT-LLM / NVIDIA NIM-compatible path
        +--> Embedding / reranking services
        |
        v
GPU / Infrastructure Layer
        |
        +--> Rented cloud GPUs for development and SaaS MVP
        +--> Private cloud
        +--> On-prem Kubernetes
        +--> Air-gapped enterprise deployment
```

### Application Layers

1. PrivyCode: coding chat, autocomplete, inline edit, repo context, lightweight agent.
2. Private RAG: enterprise document/code/search assistant using same model and infrastructure layer.
3. AI Agents: workflow automation, ticket handling, PR review, CI fixers, internal task agents.

## 11. Technology Stack

### MVP Stack

Frontend / client:

1. VS Code extension first.
2. CLI second.
3. Web dashboard for billing, usage, and model status.

Backend:

1. TypeScript or Python FastAPI for API services.
2. PostgreSQL for users, usage, billing metadata, model registry.
3. Redis for queues, rate limits, and short-lived context/cache.
4. Object storage for benchmark logs, model metadata, and eval artifacts.
5. OpenTelemetry + Prometheus/Grafana for metrics.

Inference:

1. vLLM as initial serving runtime.
2. SGLang as benchmark candidate for agent/coding workflows.
3. TensorRT-LLM or NVIDIA NIM-compatible deployment later for enterprise-grade NVIDIA environments.
4. OpenAI-compatible API surface to simplify client integrations.

Deployment:

1. Docker for all services.
2. Kubernetes for cloud and enterprise path.
3. Terraform/OpenTofu for cloud infrastructure.
4. Helm charts for enterprise deployment.

Security:

1. OAuth/email login for MVP.
2. SSO/SAML/OIDC later.
3. Secrets manager for provider keys and tenant config.
4. Encrypted storage and TLS everywhere.

## 12. Infrastructure Design

### MVP: Cloud-First Rented GPU Development

Rationale:

1. Avoid buying GPUs before validating demand.
2. Iterate quickly on model/runtime choices.
3. Use elastic GPU capacity for benchmarks.
4. Keep architecture infrastructure-agnostic from day one.

Initial setup:

1. One control plane environment on a low-cost cloud VM.
2. One or more rented GPU workers on providers such as RunPod, Lambda, CoreWeave, or equivalent.
3. GPU workers pull model images and register with SovereignForge.
4. The model router sends requests based on task type, latency SLA, user tier, and cost budget.

### Enterprise Deployment Path

Later deployment modes:

1. Private cloud SaaS: single-tenant cloud deployment.
2. Customer VPC/VNet: deployed into customer-controlled cloud account.
3. On-prem Kubernetes: deployed to customer GPU servers.
4. Air-gapped: offline model registry, signed containers, offline license, audit export.

## 13. Model Strategy

### Model Principles

1. Use open-source / open-weight models where commercially viable.
2. Stay model-agnostic.
3. Maintain a model registry with quality, latency, cost, context length, license, and deployment constraints.
4. Prefer smaller optimized models for routine tasks and stronger models only when needed.

### Candidate Model Classes

1. Fast coding autocomplete: small/medium code-specialized models.
2. Coding chat and explanation: medium instruction models.
3. Agentic edits and multi-file changes: stronger code/reasoning models.
4. Embeddings: code-aware embedding model for repository context.
5. Reranking: lightweight reranker for context selection.

### Lifecycle Management

Each model must have:

1. Version.
2. License metadata.
3. Supported context length.
4. Quantization variants.
5. Runtime compatibility.
6. Benchmark scores.
7. Cost per 1M tokens or equivalent internal unit.
8. Rollback status.
9. Deprecation status.

## 14. Model Routing and Optimization

Routing inputs:

1. User tier.
2. Task type: autocomplete, chat, inline edit, tests, refactor, PR review.
3. Repository language/framework.
4. Context length required.
5. Latency requirement.
6. Current GPU load.
7. Estimated cost.
8. Historical model success rate.

Routing examples:

1. Autocomplete: small fast model, aggressive caching, low latency.
2. Explanation: medium model, moderate context.
3. Multi-file refactor: stronger model, larger context, higher budget.
4. Free/low-cost plan: route to cheaper model unless quality threshold fails.
5. Enterprise regulated repo: route only to approved private models.

Optimization methods:

1. Quantization: FP16/BF16, FP8, INT8, AWQ/GPTQ where quality permits.
2. KV cache reuse.
3. Prefix caching.
4. Continuous batching.
5. Speculative decoding where supported.
6. Context compression and retrieval.
7. Model distillation later.
8. LoRA/domain adapters for enterprise customers.

## 15. Performance Strategy

### Performance Targets

MVP:

1. Autocomplete p95 latency: under 600 ms for small suggestions where technically feasible.
2. Chat first token latency: under 2.5 seconds for normal requests.
3. Inline edit response: under 8 seconds for small files.
4. Model availability: 99.0% for beta, 99.5% after paid launch.
5. Cost visibility: 100% of AI requests metered by user, model, task type, and GPU worker.

Later:

1. Enterprise uptime target: 99.9% or higher depending on deployment.
2. Autoscaling for GPU workers.
3. Per-tenant SLA dashboards.
4. Workload-specific performance contracts.

### Benchmark Dimensions

1. Latency: time to first token, tokens/sec, end-to-end task time.
2. Quality: pass rate on coding tasks, edit acceptance, compile/test success.
3. Cost: GPU seconds, tokens, cache hit rate, cost per successful task.
4. Reliability: error rate, timeout rate, retry rate.
5. Safety: secret leakage, prompt injection susceptibility, unsafe command suggestions.

## 16. Functional Requirements

### MVP Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| FR-001 | User can install PrivyCode VS Code extension. | Must |
| FR-002 | User can authenticate and select plan. | Must |
| FR-003 | User can ask coding questions with current file context. | Must |
| FR-004 | User can request inline code edits. | Must |
| FR-005 | User can receive autocomplete suggestions. | Must |
| FR-006 | User can index a local repository for context. | Must |
| FR-007 | System can route requests across at least two model profiles. | Must |
| FR-008 | System meters usage by user, model, request type, and estimated cost. | Must |
| FR-009 | System enforces monthly allowances and overage limits. | Must |
| FR-010 | Admin can view model latency, throughput, error rate, and cost. | Must |
| FR-011 | System supports benchmark runs for candidate models. | Should |
| FR-012 | User can choose cheap/balanced/strong mode. | Should |
| FR-013 | User can use BYOK or custom endpoint. | Should |
| FR-014 | System can run basic agentic edits with user approval. | Should |
| FR-015 | Team admin can manage seats. | Later |

### Later Enterprise Functional Requirements

| ID | Requirement | Priority |
|---|---|---|
| EFR-001 | Deploy SovereignForge to customer VPC/private cloud. | Later |
| EFR-002 | Deploy to on-prem Kubernetes. | Later |
| EFR-003 | Support air-gapped installation package. | Later |
| EFR-004 | Support SSO/SAML/OIDC and SCIM. | Later |
| EFR-005 | Provide RBAC and policy-based model access. | Later |
| EFR-006 | Provide audit logs for prompts, outputs, actions, and admin changes. | Later |
| EFR-007 | Support customer-specific benchmarks. | Later |
| EFR-008 | Support approved model registry and lifecycle policies. | Later |
| EFR-009 | Support domain adapters / LoRA fine-tunes. | Later |
| EFR-010 | Support Private RAG and internal agents. | Later |

## 17. Non-Functional Requirements

| Category | MVP Requirement | Later Enterprise Requirement |
|---|---|---|
| Performance | Low latency for autocomplete/chat; cost-aware routing. | SLA-backed performance per deployment. |
| Reliability | Graceful fallback between model workers. | Multi-region or HA on customer infra. |
| Security | TLS, encrypted secrets, least privilege, no training on user code by default. | SSO, RBAC, audit logs, retention controls, air-gap support. |
| Privacy | Do not use private code for model training without explicit opt-in. | Tenant isolation and customer-managed data boundaries. |
| Portability | Dockerized services and clean OpenAI-compatible APIs. | Kubernetes/Helm, offline images, hardware profiles. |
| Observability | Metrics for request cost, latency, errors, GPU utilization. | Compliance-ready audit and governance dashboards. |
| Maintainability | Modular model runtime abstraction. | Pluggable runtimes, model registry, lifecycle automation. |

## 18. Security and Governance

### MVP Security

1. Encrypt data in transit and at rest.
2. Store secrets outside application code.
3. Redact obvious secrets from logs.
4. Do not log full prompts/outputs by default for individual users unless needed for debugging and explicitly disclosed.
5. Provide user setting to disable cloud context retention.
6. Require confirmation before agentic file edits are applied.

### Later Enterprise Security

1. SSO/SAML/OIDC.
2. SCIM provisioning.
3. RBAC.
4. Per-repository context policies.
5. Approved model list.
6. Prompt/output audit trails.
7. Admin-configurable retention.
8. Customer-managed keys where feasible.
9. Air-gapped model and container distribution.
10. Compliance reports for regulated buyers.

## 19. Pricing and Business Model

### Pricing Strategy

The core pricing lesson is: low price is attractive, but unlimited usage is dangerous.

Recommended MVP pricing:

| Plan | Price | Positioning | Usage Model |
|---|---:|---|---|
| Free | ₹0 / $0 | Trial and adoption | Limited monthly completions/chat |
| Developer | ₹299/month (~$3.5) | Price-sensitive individual | Fixed monthly AI allowance |
| Pro | ₹599/month (~$7) | Daily individual user | Higher allowance, stronger model access |
| Power | ₹999/month (~$12) | Heavy user | Larger context, agent tasks, priority |
| Local/BYOK | ₹999 one-time or ₹199/month | User pays inference | Client + routing + local/custom endpoint |
| Team | ₹499-699/user/month | Small teams | Shared limits, admin, usage dashboard |
| Enterprise | Custom | Private deployment | Annual contract + deployment/support |

### Unit Economics Requirements

1. Every plan must have hard or soft usage limits.
2. Free users must be routed to cheapest acceptable models.
3. Developer plan must avoid expensive long-running agent tasks.
4. Pro/Power plans can include stronger models but must meter usage.
5. BYOK/local mode reduces inference cost burden and can improve margin.
6. Enterprise revenue should come from annual platform licensing, deployment, support, and optimization services.

## 20. Initial Cloud-First Cost Estimates

These are planning estimates only. Actual costs depend on tokens, concurrency, model size, cache efficiency, GPU availability, and provider discounts.

### GPU Price Assumptions

Based on publicly visible cloud GPU pricing checked in August 2026:

1. RunPod GPU pods show approximate hourly pricing such as L40S around $0.99/hour, A100 80GB around $1.39-$1.49/hour, and H100 around $2.89-$2.99/hour.
2. RunPod serverless lists higher hourly equivalents, such as L40/L40S class around $1.75/hour and H100 around $4.55/hour.
3. CoreWeave public examples show multi-GPU instance pricing such as 8x L40S at $18/hour and 8x A100 at $21.60/hour, with lower spot pricing for some A100 capacity.

### MVP Development Cost Scenario

| Item | Assumption | Monthly Estimate |
|---|---|---:|
| Control plane VM/database/cache | Small production-like environment | $100-$300 |
| Dev GPU | 1x L40S, 8 hrs/day, 22 days/month at ~$0.99/hr | ~$174 |
| Benchmark GPU bursts | 1x H100, 40 hrs/month at ~$3/hr | ~$120 |
| Storage/logging/bandwidth | Models, logs, artifacts | $50-$250 |
| Monitoring/misc | Metrics, backups, domains | $50-$150 |
| Total early dev infra | Lean cloud-first setup | ~$500-$1,000/month |

### Paid Beta Inference Scenario

| Scenario | Assumption | Monthly Estimate |
|---|---|---:|
| Lean beta | 1x L40S mostly business hours + limited serverless bursts | $500-$1,500 |
| Small paid launch | 1-3 GPU workers with autoscaling and queueing | $1,500-$5,000 |
| Heavy agent usage | H100/A100 capacity for larger models and concurrency | $5,000+ |

### Pricing Feasibility Note

A ₹299/month plan is feasible only if:

1. Usage allowance is limited.
2. Most tasks route to small/medium optimized models.
3. Autocomplete is aggressively cached and batched.
4. Heavy agent tasks are excluded or charged separately.
5. Power users upgrade or bring their own inference.

## 21. MVP Scope

### MVP Must Include

1. VS Code extension.
2. Coding chat with current-file and selected-code context.
3. Inline edit/apply patch workflow.
4. Basic autocomplete.
5. Repository indexing for local context.
6. Cloud-hosted SovereignForge control plane.
7. vLLM-based inference worker.
8. At least two model profiles: cheap/fast and stronger.
9. Usage metering and plan limits.
10. Basic benchmark harness.
11. Admin dashboard for model health and cost.

### MVP Should Include

1. BYOK/custom endpoint support.
2. CLI.
3. Cheap/balanced/strong mode switch.
4. Simple agentic edit with user approval.
5. Public benchmark page to build trust.

### Excluded From MVP

1. Full enterprise on-prem installer.
2. Air-gapped deployment.
3. Fine-tuning pipeline.
4. Private RAG product.
5. Full multi-agent workflow orchestration.
6. Formal compliance certifications.
7. JetBrains and Visual Studio support.

## 22. Phased Roadmap

### Phase 0: Technical Validation, 2-4 Weeks

1. Benchmark 3-5 open coding models.
2. Compare vLLM and SGLang for target workloads.
3. Measure cost per task on L40S/A100/H100 class GPUs.
4. Build simple router prototype.
5. Validate autocomplete latency feasibility.

Exit criteria:

1. One cheap model and one stronger model selected.
2. Initial cost model completed.
3. Prototype chat/edit flow working.

### Phase 1: MVP Alpha, 6-8 Weeks

1. VS Code extension.
2. Cloud API.
3. Repository context.
4. Chat, inline edit, basic autocomplete.
5. Usage metering.
6. Admin metrics.

Exit criteria:

1. 50-100 alpha users.
2. Daily active usage by at least 30% of invited users.
3. Cost per active user measured.

### Phase 2: Paid Beta, 8-12 Weeks

1. Developer and Pro plans.
2. Billing integration.
3. BYOK/custom endpoint option.
4. Benchmark reports.
5. Model routing improvements.
6. Basic team plan.

Exit criteria:

1. 500+ registered users.
2. 50+ paid users.
3. Gross margin positive on normal users.
4. Heavy-user cost controls working.

### Phase 3: Team and Private Deployment Preview, 3-6 Months

1. Team admin dashboard.
2. Shared usage pools.
3. Policy controls.
4. Private cloud deployment prototype.
5. Customer-specific benchmarks.
6. Initial enterprise pilots.

Exit criteria:

1. 3-5 pilot teams.
2. Demonstrated cost/performance advantage on real workloads.
3. One private deployment proof of concept.

### Phase 4: SovereignForge Enterprise, 6-12 Months

1. Kubernetes/Helm deployment.
2. SSO/RBAC/audit logs.
3. Model lifecycle and replacement workflows.
4. Domain adapters.
5. Private RAG beta.
6. Air-gapped design validation.

Exit criteria:

1. First annual enterprise contract.
2. Repeatable private deployment runbook.
3. Demonstrable moat in workload-aware optimization.

## 23. KPIs

### Product KPIs

1. Weekly active users.
2. Daily active developers.
3. Completion acceptance rate.
4. Inline edit acceptance rate.
5. Chat-to-code conversion rate.
6. Agent task success rate.
7. Retention after 7, 30, and 90 days.

### Performance KPIs

1. p50/p95 autocomplete latency.
2. p50/p95 chat first-token latency.
3. Tokens/sec by model/runtime/GPU.
4. GPU utilization.
5. Cache hit rate.
6. Error and timeout rate.

### Business KPIs

1. Free-to-paid conversion.
2. Monthly recurring revenue.
3. Average revenue per user.
4. Gross margin by plan.
5. Inference cost per active user.
6. Churn.
7. Upgrade rate from Developer to Pro/Power.

### Enterprise KPIs

1. Number of pilots.
2. Pilot-to-paid conversion.
3. Deployment time.
4. Benchmark improvement over customer baseline.
5. Cost reduction versus frontier API baseline.
6. Security review pass rate.

## 24. Edge Cases, Risks, and Mitigations

| Risk / Edge Case | Impact | Mitigation |
|---|---|---|
| Low-cost users consume too much GPU | Negative margins | Usage allowances, throttling, cheaper routing, paid overages |
| Open-source model quality is weaker than Copilot/Codex | Poor retention | Focus on routine coding first; route hard tasks to stronger models or BYOK |
| Autocomplete latency too high | Bad UX | Small models, caching, colocated workers, streaming, local option |
| GPU supply/prices fluctuate | Cost instability | Multi-provider design, spot/reserved mix, autoscaling, model efficiency |
| Competitors lower pricing | Weak price wedge | Differentiate on private/local, transparency, optimization, Indian pricing |
| Cline/free BYOK reduces willingness to pay | Acquisition challenge | Offer managed low-cost inference, better defaults, benchmarks, local mode |
| Enterprise sales cycle is long | Slow revenue | Start with individual/team wedge before enterprise |
| Air-gapped deployments are complex | Delivery risk | Treat as later capability, design packaging early but do not MVP it |
| Model licenses restrict commercial use | Legal risk | Model registry must track license and allowed use |
| Private code leakage via logs/context | Trust failure | Redaction, retention controls, privacy defaults |
| Prompt injection in repositories | Security issue | Context filters, tool permissions, user approval for actions |
| Model hallucinated code causes bugs | Quality issue | Test-aware workflows, diffs, explanations, rollback |
| Overbuilding platform before app traction | Execution risk | PrivyCode MVP first; SovereignForge grows only as needed |

## 25. Feasibility Assessment

### Technical Feasibility

Feasible, but quality and latency are the hardest constraints. Existing open-source models, vLLM/SGLang, Kubernetes, and rented GPUs make the infrastructure achievable. The challenge is not serving a model; the challenge is delivering acceptable coding UX at a low cost.

### Commercial Feasibility

Feasible if the product does not rely only on being cheaper. ₹299/month can work for limited usage, but heavy users require Pro/Power, BYOK, local mode, or overages. Enterprise revenue is attractive but should come after proving the core optimization layer.

### Differentiation Feasibility

The moat is feasible but not automatic. It requires:

1. Continuous benchmark data.
2. Real workload telemetry.
3. Strong model/runtime/hardware experimentation.
4. Clear cost-performance reporting.
5. Repeatable enterprise deployment patterns.

## 26. Open Decisions

1. Which first IDE: VS Code only, or VS Code + JetBrains?
2. Which initial models are commercially safe and performant enough?
3. Should local/BYOK mode be in MVP or paid beta?
4. Should the backend be TypeScript, Python, or mixed?
5. Which GPU provider should be primary for MVP?
6. What is the exact monthly usage allowance for ₹299 and ₹599 plans?
7. Will PrivyCode support proprietary fallback models for hard tasks?
8. How much prompt/output data can be stored for debugging while preserving trust?
9. Should SovereignForge be branded visibly in the MVP or remain backend infrastructure?
10. Which benchmark suite becomes the public trust signal?

## 27. Recommended Immediate Next Steps

1. Build a benchmark harness for coding tasks before polishing the app.
2. Test 3-5 open-source coding models on real coding workflows.
3. Measure GPU cost per accepted completion/edit/chat answer.
4. Prototype VS Code chat + inline edit with a vLLM backend.
5. Define hard usage limits for ₹299 and ₹599 plans.
6. Recruit 20-50 developers who currently hesitate to pay for Copilot/Codex/Cursor.
7. Validate whether they prefer managed cheap inference, BYOK, or local mode.

## 28. Source Notes

Market and infrastructure references checked in August 2026:

1. GitHub Copilot pricing: https://github.com/features/copilot/plans
2. GitHub Copilot license pricing docs: https://docs.github.com/en/billing/concepts/product-billing/github-copilot-licenses
3. Cursor pricing: https://cursor.com/pricing
4. OpenAI ChatGPT pricing: https://openai.com/chatgpt/pricing
5. OpenAI Codex pricing: https://chatgpt.com/codex/pricing/
6. Cline pricing: https://cline.bot/pricing
7. Tabnine pricing: https://www.tabnine.com/pricing/
8. Sourcegraph pricing: https://sourcegraph.com/pricing
9. NVIDIA NIM overview: https://www.nvidia.com/en-us/ai-data-science/products/nim-microservices/
10. NVIDIA NIM developer page: https://developer.nvidia.com/nim
11. RunPod GPU pricing: https://www.runpod.io/pricing
12. CoreWeave pricing: https://coreweave.com/pricing
