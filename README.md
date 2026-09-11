# LLM Code Generation Benchmark

> Repository-aware LLM code-generation benchmark with task-aware retrieval, deterministic validation, DeepEval scoring, pairwise model comparison, and optional isolated checks.

## Clean project structure

```text
.
├── app.py                         # Streamlit entry point
│
├── benchmark/                     # Canonical application code
│   ├── __init__.py
│   ├── evaluation.py              # GEval + ArenaGEval
│   ├── ingestion.py               # GitHub ingestion + redaction
│   ├── model_service.py           # LLM calls and streaming
│   ├── retrieval.py               # Task-aware file retrieval
│   ├── sandbox.py                 # Optional isolated execution checks
│   └── validation.py              # Static validation and security checks
│
├── data/
│   └── benchmark_tasks.json       # Starter benchmark tasks
│
├── docs/
│   └── BENCHMARK.md               # Benchmark protocol
│
├── evals/                         # Evaluation suite namespace
├── tests/                         # Deterministic tests
├── artifacts/                     # Local benchmark output directory
│
├── .github/workflows/ci.yml
├── .env.example
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

The former root-level implementation modules are thin compatibility shims. The source of truth is `benchmark/`.

## What this project does

The benchmark answers a practical software-engineering question:

**Given the same existing codebase and the same requested change, which model produces the stronger implementation?**

The same repository context and task are sent to **Cohere Aya Expanse** and **Meta Llama 4 Scout**. Their outputs are streamed in parallel, validated, evaluated with DeepEval, and compared head-to-head.

## Workflow

```text
GitHub Repository
      ↓
   GitIngest
      ↓
 Sanitized Repository Context
      ↓
 Task-aware Retrieval
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

Deterministic checks and LLM judging are kept separate.

| Layer | Checks |
|---|---|
| Deterministic | Python syntax/compile, basic HTML parsing, multi-file parsing, credential patterns, file/line counts |
| DeepEval | Correctness, readability, best practices |
| Pairwise | Which candidate is better overall? |
| Sandbox | Optional isolated repository checks for generated multi-file output |

DeepEval metric values remain in their native `0–1` range internally and are displayed on a `0–10` scale. Current threshold: `0.70`.

## Large repository handling

The original flat workflow could overwhelm a model by sending the complete repository every time. The current retrieval layer ranks candidate file sections against the task and sends a bounded context instead.

This improves context efficiency, but lexical retrieval is not perfect. Very large repositories can still require semantic embeddings and dependency-aware retrieval.

## Small task vs full website

A ten-line function and a complete website should not receive the same evidence standard.

For a focused Python change, static validation plus DeepEval can provide a useful comparative signal.

For a multi-file feature, the models return structured `FILE:` blocks and the validator checks the detected files.

For a full website, reliable evaluation requires applying the generated change to a repository snapshot, running tests/builds in isolation, and eventually performing browser smoke tests. The current sandbox deliberately avoids arbitrary dependency installation and arbitrary repository-script execution.

## Security

Repository content and model output are untrusted input.

The benchmark redacts obvious credentials before model use, treats repository comments/documentation as data rather than instructions, rejects unsafe generated paths, and keeps provider credentials outside source files. Docker checks use network isolation and resource limits.

Previously exposed credentials were revoked/rotated and removed from the current branch. Old Git objects may still contain historical material until history is rewritten.

## Benchmark tasks and reproducibility

Starter tasks are stored in `data/benchmark_tasks.json`. The detailed protocol is in `docs/BENCHMARK.md`.

For meaningful comparisons, run multiple tasks and multiple trials and record:

```text
mean / median score
pass rate
pairwise win rate
syntax / test / build failure rate
latency
token usage / cost when available
model + repository revision
```

One task and one run should not be presented as a universal model ranking.

## Setup

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
python -m venv .venv
pip install -r requirements.txt
```

Copy `.env.example` to `.env`, add your provider credentials locally, and never commit real keys.

Run:

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Describe one concrete coding change.
4. Compare the two model outputs.
5. Review the retrieved files.
6. Optionally provide a reference implementation.
7. Run **Evaluate Latest Generation**.
8. For multi-file output, run **Run Isolated Checks** when Docker is available.
9. Review quality scores, deterministic evidence, sandbox results, and pairwise winner.

## Technology

Python 3.12+, Streamlit, LiteLLM, GitIngest, DeepEval, Pandas, Plotly, Docker (optional), Cohere Aya Expanse, and Meta Llama 4 Scout.

## Roadmap

- Semantic + dependency-aware retrieval
- Stronger JavaScript/TypeScript/CSS validation
- Safe test/build discovery
- Browser smoke testing
- Latency/token/cost telemetry
- Multi-trial statistical reports
- JSON/CSV result export
- CI benchmark regression suite

## License

MIT License — see [`LICENSE`](LICENSE).

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
