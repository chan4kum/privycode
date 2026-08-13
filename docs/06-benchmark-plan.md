# Benchmark & Evaluation Framework Plan

## 1. Target Models for Evaluation
To measure the effectiveness and responsiveness of SovereignForge, the benchmark harness will evaluate these key model tiers:

1. **Primary MVP Model (Quality/Chat)**: `Qwen/Qwen2.5-Coder-32B-Instruct` 
   * Targeted for high-quality chat and diff-edits. Fits on a single A100/H100 80GB or dual A6000 48GB.
2. **FIM Fast Tier Model (Speed/Autocomplete)**: `Qwen/Qwen2.5-Coder-7B-Instruct` 
   * Designed for ultra-low latency keystroke-level completions.
3. **Cloud Fast Baseline**: `Groq/llama-3.3-70b-versatile` or `Groq/qwen-2.5-coder-32b` 
   * Used as the reference baseline for speed ($> 250\text{ tokens/sec}$).

## 2. Evaluation Metrics & KPIs
The benchmark runner will record the following metrics for every executed run:
* **TTFT (Time To First Token)**: Must be $< 250\text{ms}$ for inline completions to avoid perceived lag.
* **Throughput (Tokens Per Second)**: Must be $> 40\text{ tokens/sec}$ per active stream for chat.
* **Accuracy (Pass@1)**: HumanEval pass rate must exceed 75% for 32B class models.
* **Diff Precision**: Percentage of generated diffs that apply cleanly without breaking AST constraints ($> 85\%$).
* **VRAM Efficiency**: Measurement of KV Cache Paged Attention utilization under load.

## 3. Benchmark Suite Tasks
The test harness runs the following automated scenarios:

* **Task Set A (Syntactic FIM)**: 
  * 100 code-completion positions across Python, TypeScript, Go, and Rust. 
  * *Metric*: Exact AST match & compile rate.
* **Task Set B (Unit Test Generation)**: 
  * Generate unit tests for 20 complex functions. 
  * *Metric*: Pytest/Jest pass rate.
* **Task Set C (Refactoring & Edits)**: 
  * 30 instruction-based edits (e.g., synchronous to async, adding type hints). 
  * *Metric*: Unified diff application cleanly with 0 syntax errors.
* **Task Set D (Multi-File Contextual Q&A)**: 
  * 20 repo-level architectural questions with context chunks injected into the prompt. 
  * *Metric*: Graded by a stronger LLM (e.g., GPT-4o) or expert human rubric score (1-5).
