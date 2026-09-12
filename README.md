# LLM Code Generation Benchmark

> A repository-aware benchmark for evaluating AI coding models on the same software-engineering task, combining retrieval, deterministic checks, isolated execution, DeepEval judging, and bounded self-repair.

## What this project does

Given the same existing repository and requested code change, the system compares **Qwen 3.6 27B on Groq** and **NVIDIA Nemotron 3 Super 120B A12B on OpenRouter** under the same context and evaluation policy.

The project is designed to grow from a model benchmark into a **repository-aware AI coding-agent evaluation platform**.

## Project structure

```text
.
├── app.py                         # Streamlit dashboard
├── benchmark/
│   ├── agent.py                  # Validation → execution → semantic judging
│   ├── agent_loop.py             # Bounded self-repair orchestration
│   ├── agent_service.py          # Repair-model adapter
│   ├── evaluation.py             # GEval + ArenaGEval scoring
│   ├── ingestion.py              # GitHub ingestion + credential redaction
│   ├── model_service.py          # Provider/model calls + streaming
│   ├── retrieval.py              # Task-aware repository retrieval
│   ├── sandbox.py                # Restricted Docker checks
│   ├── tasks.py                  # Reproducible benchmark task loader
│   └── validation.py             # Static validation + security checks
├── data/
│   └── benchmark_tasks.json      # Starter benchmark tasks
├── docs/
│   ├── BENCHMARK.md              # Benchmark protocol
│   └── SELF_REPAIR.md             # Self-repair design and safety boundaries
├── scripts/
│   └── validate_benchmark.py     # Task-set validation CLI
├── evals/                         # Future benchmark result artifacts
├── tests/                         # Deterministic unit tests
├── artifacts/                     # Local/generated artifacts
├── .github/workflows/ci.yml       # Compile + task validation + tests
├── .env.example
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

The older root-level implementation modules remain only as thin compatibility shims. The canonical source is the `benchmark/` package.

## Models

| Model | Provider | Model ID |
|---|---|---|
| Qwen 3.6 27B | Groq | `qwen/qwen3.6-27b` |
| NVIDIA Nemotron 3 Super 120B A12B | OpenRouter | `nvidia/nemotron-3-super-120b-a12b:free` |

Both models receive the same task and repository context, and both are evaluated with the same validation, sandbox, semantic judging, and self-repair policy.

## Evaluation workflow

```text
GitHub Repository
      ↓
   GitIngest + Redaction
      ↓
 Task-aware Retrieval
      ↓
 ┌──────────────────────┐
 ↓                      ↓
Qwen 3.6 27B        Nemotron 3 Super
  (Groq)             (OpenRouter)
 ↓                      ↓
 └──────────┬───────────┘
            ↓
 Single / Multi-file Candidate
            ↓
 Candidate Validation
            ↓
 Restricted Docker Sandbox
            ↓
 DeepEval Quality Metrics
            ↓
 ArenaGEval Pairwise Judge
            ↓
 Optional Self-Repair Loop
            ↓
 Best Candidate + Agent Trace
            ↓
 Streamlit Dashboard
```

## Current capabilities

### Repository-aware generation

The prompt builder uses the repository summary, structure, and task-ranked file retrieval instead of dumping the entire repository into every request. Retrieved context is bounded and repository instructions are treated as untrusted data.

### Multi-file code generation

Models can return coordinated changes using:

```text
FILE: path/to/file.py
```python
# complete file contents
```
```

The validator parses multiple files, counts the generated workspace, and applies path-traversal protection before sandboxing.

### Deterministic validation

The benchmark currently checks Python syntax/compilation, lightweight HTML parsing, obvious credential patterns, output structure, file/line counts, and other static evidence before relying on LLM judgment.

### Isolated execution

Generated workspaces can be checked through Docker with no network access, dropped Linux capabilities, read-only root filesystem, resource limits, and a temporary workspace. The system intentionally avoids installing arbitrary dependencies or executing arbitrary repository scripts.

### Agent-style evaluation

`benchmark/agent.py` provides a reusable trajectory:

```text
Candidate
  ↓
Validation
  ↓
Isolated execution
  ↓
Semantic evaluation
  ↓
Observable trace
```

### Bounded self-repair

`benchmark/agent_loop.py` adds a real model-driven recovery loop:

```text
Generate
   ↓
Validate
   ↓
Sandbox test
   ↓
Failure evidence
   ↓
Repair model
   ↓
Re-test
   ↓
Best candidate
```

The Streamlit dashboard exposes a **Self-Repair & Re-test** action and a configurable repair budget. Each repair attempt receives the original task, bounded repository context, current candidate, and compact deterministic failure evidence. The final candidate is selected using deterministic evidence rather than asking the model to grade itself.

### Reproducible benchmark suite

Tasks are stored in `data/benchmark_tasks.json` and loaded through `benchmark/tasks.py`. Each task has a stable ID, category, language, and task description.

Validate the task suite locally with:

```bash
python scripts/validate_benchmark.py
```

## Metrics

| Metric | Purpose |
|---|---|
| Correctness | Task compliance, intended behavior, edge cases, repository fit |
| Readability | Naming, structure, formatting, documentation, maintainability |
| Best Practices | Error handling, security, efficiency, modularity |
| Validation | Deterministic syntax/security evidence |
| Sandbox | Isolated execution result when available |
| Repair recovery | Whether a failed candidate can be improved within the bounded budget |
| Pairwise winner | Direct blinded comparison between model candidates |

DeepEval scores remain in their native `0–1` range internally and are displayed as `0–10` in the UI. The current semantic threshold is `0.70`.

## Roadmap

The foundation is now ready for the next evaluation layer:

1. **Dependency-aware retrieval** — include imports, callers, tests, and related configuration instead of only lexical matches.
2. **Language-specific execution** — stronger JavaScript/TypeScript/Python test and build discovery with explicit allow-lists.
3. **Browser smoke tests** — evaluate generated websites through a separately isolated browser runner.
4. **Benchmark statistics** — run multiple trials and report pass rate, mean/median score, pairwise win rate, failure categories, latency, and cost.
5. **Result export** — save benchmark runs as JSON/CSV for reproducible comparisons.
6. **CI regression benchmarks** — run a small stable benchmark subset on pull requests to detect quality regressions.
7. **Patch/PR mode** — turn a validated best candidate into a reviewable patch instead of directly modifying a repository.

## Security model

Repository content and model output are untrusted. Credentials are expected to stay in environment variables, ingestion performs obvious secret redaction, generated paths are restricted to the sandbox workspace, and arbitrary generated code is not executed in the main Streamlit process.

Self-repair is bounded by an explicit attempt budget. Empty repair responses stop the loop, and candidate ranking uses deterministic evidence. Docker checks remain network-isolated with resource limits.

Previously exposed credentials were revoked/rotated and removed from the current branch. Historical Git objects may still require a separate history rewrite if complete secret removal is needed.

## Setup

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
python -m venv .venv
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add credentials locally. Never commit real API keys.

Run the dashboard:

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Select a reproducible benchmark task or enter a custom coding task.
4. Generate the same task with both models.
5. Review retrieval evidence and multi-file output.
6. Run **Evaluate Latest** for static + semantic scoring.
7. Run **Run Isolated Checks** when Docker is available.
8. Run **Run Agent Evaluation** for the validation → sandbox → judge trace.
9. Set the repair budget and run **Self-Repair & Re-test** to let each model attempt bounded recovery from concrete failures.
10. Review repair attempts, failure evidence, final candidate, scores, sandbox output, and pairwise winner.

## Technology

Python 3.12+, Streamlit, LiteLLM, GitIngest, DeepEval, Pandas, Plotly, Docker (optional), Groq Qwen 3.6 27B, and OpenRouter NVIDIA Nemotron 3 Super 120B A12B.

## License

MIT License — see [`LICENSE`](LICENSE).

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
