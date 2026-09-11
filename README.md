# LLM Code Generation Benchmark

> A repository-aware benchmark that compares **Cohere Aya Expanse** and **Meta Llama 4 Scout** on the same coding task, then combines deterministic validation with **DeepEval** judging.

## What this project is

This is not a generic coding chatbot. It is an experiment framework for a practical software-engineering question:

**Given the same existing codebase and the same requested change, which model produces the stronger implementation?**

Both models receive the same repository/task inputs. Their outputs are streamed in parallel, checked for deterministic failures, evaluated on code quality, and compared head-to-head.

## Workflow

```text
Public GitHub Repository
          |
          v
       GitIngest
          |
          v
 Summary + Structure + Sanitized Source
          |
          v
   Task-aware File Retrieval
          |
          +----------------------+
          |                      |
          v                      v
    Aya Expanse            Llama 4 Scout
          |                      |
          +----------+-----------+
                     |
                     v
              Generated Output
             (single / multi-file)
                     |
          +----------+-----------+
          |                          |
          v                          v
 Deterministic Validation       DeepEval Judges
 syntax / security / format   correctness / readability /
                              best practices
          |                          |
          +------------+-------------+
                       v
               Arena Pairwise Judge
                       |
                       v
             Optional Docker Checks
                       |
                       v
                Streamlit Dashboard
```

## Project structure

```text
.
├── app.py                         # Streamlit entry point
│
├── benchmark/                     # Canonical benchmark implementation
│   ├── __init__.py
│   ├── evaluation.py              # GEval + ArenaGEval scoring
│   ├── ingestion.py               # GitHub ingestion + secret redaction
│   ├── model_service.py            # Provider/model calls and streaming
│   ├── retrieval.py                # Task-aware repository retrieval
│   ├── sandbox.py                  # Optional isolated execution checks
│   └── validation.py               # Static validation and security checks
│
├── data/
│   └── benchmark_tasks.json        # Reproducible starter task set
│
├── docs/
│   └── BENCHMARK.md                # Benchmark protocol and limitations
│
├── evals/                          # Evaluation-suite namespace
├── tests/                          # Deterministic unit tests
├── artifacts/                      # Local benchmark output directory
│   └── .gitkeep
│
├── .github/workflows/ci.yml        # Automated compile/test checks
├── .env.example                    # Local environment template
├── .gitignore
├── .python-version
├── LICENSE
├── pyproject.toml
└── requirements.txt
```

The small root-level Python files that previously contained the implementation are now compatibility shims. The real source of truth lives under `benchmark/`.

## Why repository-aware generation?

A standalone function can look correct while still being a poor contribution to an existing codebase. The benchmark therefore uses repository summary, structure, and task-ranked source context so both models can follow existing architecture and conventions.

Large repositories are no longer blindly dumped into one model request. A lightweight retrieval layer ranks candidate file sections against the task and keeps the selected context bounded. This reduces context pressure, while semantic/vector retrieval and dependency-aware ranking remain future upgrades.

## Evaluation layers

### Deterministic validation

The benchmark separates objective checks from subjective model judgment:

- Python syntax/compile checks where applicable
- Basic HTML parsing
- Multi-file output detection
- Obvious credential-pattern scanning
- File and line counts
- Optional Docker-based repository checks

A passing syntax check does not prove functional correctness.

### DeepEval quality judgment

Three GEval metrics are used:

| Metric | What it checks |
|---|---|
| **Correctness** | Task compliance, expected behavior, edge cases, runtime risks, and repository fit |
| **Readability** | Naming, organization, formatting, documentation, and maintainability |
| **Best Practices** | Error handling, security, efficiency, modularity, and configuration hygiene |

DeepEval scores remain in their native **0–1** range internally and are displayed on a **0–10** scale in the dashboard. The current pass threshold is **0.70**.

### Pairwise model comparison

Because the primary question is comparative, the benchmark also uses **ArenaGEval** to choose a winner between the two outputs. The pairwise result is kept separate from the numerical quality score.

## Small change vs full website

A 10-line Python change and a full web application are different evaluation problems.

For a focused change, retrieval + static checks + semantic judging can provide useful evidence.

For a multi-file feature, the models return every changed file using the `FILE:` format and the validator checks every supported file it can identify.

For a complete website or production feature, semantic judging alone is insufficient. The stronger path is:

```text
Generate patch
    ↓
Apply to repository snapshot
    ↓
Static checks
    ↓
Isolated tests / build
    ↓
Smoke / browser checks
    ↓
Quality + latency + cost + failure metrics
```

The current Docker layer implements a conservative subset: it can overlay generated multi-file output onto a cloned public repository and run predefined low-risk checks without network access. It deliberately does not install arbitrary dependencies or execute repository scripts by default.

## Security model

Repository content and generated output are treated as untrusted.

The benchmark:

- redacts obvious credentials before repository content reaches an LLM provider;
- treats repository comments, documentation, and strings as data rather than instructions;
- rejects generated paths that attempt `..` traversal;
- keeps provider credentials outside source files;
- avoids executing generated code in the main Streamlit process; and
- applies a restricted Docker boundary for optional checks.

A clean static scan does not prove the absence of vulnerabilities. Credentials that were previously exposed in the old repository state were revoked/rotated and removed from the current branch; old Git objects may still exist until history is rewritten.

## Reproducibility

Use `data/benchmark_tasks.json` as the starter task set. For a meaningful comparison, record task ID, repository revision, model identifiers, generation settings, evaluator configuration, retrieval settings, number of trials, timestamp, and failures/timeouts.

For each model, report mean/median quality, pass rate, pairwise win rate, syntax/test/build failures, latency, and token/cost data when available.

## Known limitations

1. Retrieval is currently lexical and can miss semantically related files.
2. Very large repositories can still contain relevant dependencies outside the selected context.
3. Sandbox execution is deliberately conservative and does not perform arbitrary dependency installation.
4. Browser-level testing is not integrated yet.
5. LLM judge scores vary between runs and are not ground truth.
6. Model/provider revisions and rate limits affect comparisons.
7. Ambiguous benchmark tasks can weaken otherwise careful measurements.

## Setup

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add credentials locally. Never commit real keys.

Run the application:

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Describe one concrete coding change.
4. Compare Aya Expanse and Llama 4 Scout outputs.
5. Review the retrieved files used for the task.
6. Optionally provide reference code.
7. Click **Evaluate Latest Generation**.
8. For multi-file output, run **Run Isolated Checks** when Docker is available.
9. Review scores, validation evidence, sandbox results, and the pairwise winner.

## Technology

- Python 3.12+
- Streamlit
- LiteLLM
- GitIngest
- DeepEval / GEval / ArenaGEval
- Pandas / Plotly
- Docker (optional sandbox checks)
- Cohere Aya Expanse
- Meta Llama 4 Scout

## Roadmap

- Semantic embeddings + dependency-aware retrieval
- Stronger JavaScript/TypeScript/CSS validation
- Safe repository test/build discovery
- Browser smoke testing in isolation
- Latency/token/cost telemetry
- Multi-trial statistical benchmark reports
- JSON/CSV result export
- CI regression benchmark suite

## License

MIT License — see [`LICENSE`](LICENSE).

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
