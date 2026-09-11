# LLM Code Generation Benchmark

> A repository-aware benchmark that compares **Cohere Aya Expanse** and **Meta Llama 4 Scout** on the same coding task, then combines deterministic validation with **DeepEval** judging.

## Project structure

```text
.
├── app.py                         # Streamlit entry point
├── benchmark/                     # Canonical benchmark implementation
│   ├── __init__.py
│   ├── evaluation.py              # GEval + ArenaGEval scoring
│   ├── ingestion.py               # GitHub ingestion + redaction
│   ├── model_service.py           # Provider/model calls + streaming
│   ├── retrieval.py               # Task-aware repository retrieval
│   ├── sandbox.py                 # Optional isolated checks
│   └── validation.py              # Static validation + security checks
├── data/
│   └── benchmark_tasks.json       # Starter benchmark tasks
├── docs/
│   └── BENCHMARK.md               # Benchmark protocol
├── evals/
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

The former root-level implementation modules are now thin compatibility shims. The source of truth is the `benchmark/` package.

## What this project is

This is an experiment framework for a practical software-engineering question:

**Given the same existing codebase and the same requested change, which model produces the stronger implementation?**

The same repository/task inputs go to Aya Expanse and Llama 4 Scout. Their outputs are streamed in parallel, checked, scored, and compared head-to-head.

## Workflow

```text
GitHub Repository
      ↓
   GitIngest
      ↓
 Sanitized Repository Context
      ↓
 Task-aware File Retrieval
      ↓
 ┌───────────────┐
 ↓               ↓
Aya Expanse   Llama 4 Scout
 ↓               ↓
 └───────┬───────┘
         ↓
 Single / Multi-file Output
         ↓
 ┌───────────────┐
 ↓               ↓
Static Checks   DeepEval
 ↓               ↓
 └───────┬───────┘
         ↓
 ArenaGEval Pairwise Judge
         ↓
 Optional Docker Checks
         ↓
 Streamlit Dashboard
```

## Evaluation

### Deterministic evidence

- Python syntax/compile checks where applicable
- Basic HTML parsing
- Multi-file output parsing
- Obvious credential-pattern scanning
- File and line counts
- Optional restricted Docker checks

### DeepEval judging

| Metric | Purpose |
|---|---|
| Correctness | Task compliance, expected behavior, edge cases, runtime risks, repository fit |
| Readability | Naming, organization, formatting, documentation, maintainability |
| Best Practices | Error handling, security, efficiency, modularity, configuration hygiene |

DeepEval scores stay in their native `0–1` range internally and are displayed on a `0–10` scale. Current threshold: `0.70`.

### Pairwise comparison

ArenaGEval is used separately for the direct question: **which candidate is better?** Its result is not merged into the individual numerical score.

## Large repository / website behavior

A small function and a complete website are different evaluation problems. Large repositories can overwhelm a single prompt, so task-aware retrieval selects candidate files and sends a bounded context.

For multi-file work, models return a structured `FILE:` format and the validator checks the detected files.

For a full website, reliable evaluation requires applying the generated change to a repository snapshot, running tests/builds in isolation, and eventually performing browser smoke tests. The current Docker layer is deliberately conservative and does not install arbitrary dependencies or execute arbitrary repository scripts by default.

## Security

Repository content and model output are treated as untrusted. The ingestion layer redacts obvious credentials, prompts treat repository comments/documentation as data rather than instructions, generated paths are checked for traversal, and provider credentials stay outside source code.

Previously exposed credentials were revoked/rotated and removed from the current branch. Old Git objects may still contain historical material until the history is rewritten.

## Benchmark protocol

See [`docs/BENCHMARK.md`](docs/BENCHMARK.md) for the evaluation ladder, threat model, scoring guidance, reproducibility requirements, and limitations.

Starter tasks are in [`data/benchmark_tasks.json`](data/benchmark_tasks.json).

For meaningful comparisons, use multiple tasks and multiple trials and report quality mean/median, pass rate, pairwise win rate, failure rate, latency, and token/cost data when available.

## Setup

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
python -m venv .venv
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure credentials locally. Never commit real keys.

Run:

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Describe one concrete coding change.
4. Compare Aya Expanse and Llama 4 Scout outputs.
5. Review task-ranked retrieval evidence.
6. Optionally provide reference code.
7. Run **Evaluate Latest Generation**.
8. For multi-file output, run **Run Isolated Checks** when Docker is available.
9. Review scores, validation evidence, sandbox results, and pairwise winner.

## Technology

Python 3.12+, Streamlit, LiteLLM, GitIngest, DeepEval, Pandas, Plotly, Docker (optional), Cohere Aya Expanse, and Meta Llama 4 Scout.

## Roadmap

- Semantic + dependency-aware retrieval
- Stronger JavaScript/TypeScript/CSS validation
- Safe test/build discovery
- Browser-level smoke testing
- Latency/token/cost telemetry
- Multi-trial statistical benchmark reports
- JSON/CSV result export
- CI benchmark regression suite

## License

MIT License — see [`LICENSE`](LICENSE).

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
