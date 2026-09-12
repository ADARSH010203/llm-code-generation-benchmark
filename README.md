# LLM Code Generation Benchmark

> A repository-aware benchmark for evaluating AI coding models on the same software-engineering task, combining retrieval, deterministic checks, isolated execution, DeepEval judging, and bounded self-repair.

## What this project does

Given the same existing repository and requested code change, the system compares **Groq GPT-OSS 120B** and the **OpenRouter Free Router** under the same context and evaluation policy.

The project is designed to grow from a model benchmark into a **repository-aware AI coding-agent evaluation platform**.

## Evaluation workflow

```text
GitHub Repository
      ↓
   GitIngest + Redaction
      ↓
 Task-aware Retrieval
      ↓
 ┌────────────────┐
 ↓                ↓
Groq          OpenRouter
 ↓                ↓
 └───────┬────────┘
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
 Self-Repair & Re-test
         ↓
 Best Candidate + Agent Trace
         ↓
 Streamlit Dashboard
```

## Current capabilities

### Repository-aware generation
The prompt builder uses repository summary, structure, and task-ranked file retrieval instead of dumping the entire repository into every request. Retrieved context is bounded and repository instructions are treated as untrusted data.

### Multi-file code generation
Models can return coordinated changes using `FILE: path` fenced blocks. The validator parses multiple files, counts the generated workspace, and applies path-traversal protection before sandboxing.

### Deterministic validation
The benchmark checks Python syntax/compilation, lightweight HTML parsing, obvious credential patterns, output structure, file/line counts, and other static evidence before relying on LLM judgment.

### Isolated execution
Generated workspaces can be checked through Docker with no network access, dropped capabilities, a read-only root filesystem, resource limits, and a temporary workspace. Arbitrary dependency installation and arbitrary host execution are not enabled.

### Self-repair agent
The bounded agent loop follows:

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

Repair attempts are explicitly limited. The final candidate is ranked using deterministic evidence instead of asking the model to grade itself.

### Reproducible benchmark suite
Tasks live in `data/benchmark_tasks.json` and are loaded through `benchmark/tasks.py`. Validate them locally with:

```bash
python scripts/validate_benchmark.py
```

## Project structure

```text
.
├── app.py
├── benchmark/
│   ├── agent.py
│   ├── agent_loop.py
│   ├── agent_service.py
│   ├── evaluation.py
│   ├── ingestion.py
│   ├── model_service.py
│   ├── retrieval.py
│   ├── sandbox.py
│   ├── tasks.py
│   └── validation.py
├── data/benchmark_tasks.json
├── docs/BENCHMARK.md
├── docs/SELF_REPAIR.md
├── scripts/validate_benchmark.py
├── tests/
├── artifacts/
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

## Metrics

| Metric | Purpose |
|---|---|
| Correctness | Task compliance, intended behavior, edge cases, repository fit |
| Readability | Naming, structure, formatting, documentation, maintainability |
| Best Practices | Error handling, security, efficiency, modularity |
| Validation | Deterministic syntax/security evidence |
| Sandbox | Isolated execution result when available |
| Repair recovery | Whether a failed candidate improves within the bounded budget |
| Pairwise winner | Direct blinded comparison between model candidates |

DeepEval scores remain in native `0–1` internally and are displayed as `0–10`. Current semantic threshold: `0.70`.

## Configuration

Required keys:

```env
GROQ_API_KEY=
OPENROUTER_API_KEY=
```

DeepEval can also use OpenRouter for its LLM-as-a-judge metrics via `USE_OPENROUTER_MODEL=1` and `DEEPEVAL_MODEL=openrouter/free`.

OpenRouter currently provides a free router that selects among available free models; Groq currently provides GPT-OSS models through its API. Availability and rate limits can change. citeturn912851search1turn912851search5

## Setup

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
python -m venv .venv
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add credentials locally. Never commit real API keys.

Run:

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Select a reproducible task or enter a custom coding task.
4. Generate the same task with both providers.
5. Review retrieval evidence and generated files.
6. Run **Evaluate Latest**.
7. Run **Run Isolated Checks** when Docker is available.
8. Run **Self-Repair & Re-test** to give each candidate a bounded repair budget.
9. Review repair attempts, failure evidence, final candidate, scores, sandbox output, and pairwise winner.

## Roadmap

1. Dependency-aware retrieval
2. Stronger language-specific execution
3. Browser smoke tests for generated websites
4. Multi-trial benchmark statistics
5. JSON/CSV result export
6. CI benchmark regression suite
7. Patch/PR generation mode

## Security

Repository content and model output are untrusted. Credentials stay in environment variables, ingestion performs obvious secret redaction, generated paths are restricted, and generated code is not executed in the main Streamlit process. Self-repair is bounded by an explicit attempt budget and Docker checks remain network-isolated.

Previously exposed credentials were revoked/rotated and removed from the current branch. Historical Git objects may still require a separate history rewrite if complete secret removal is needed.

## License

MIT License — see [`LICENSE`](LICENSE).

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
