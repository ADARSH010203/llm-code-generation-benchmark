# LLM Code Generation Benchmark

> A repository-aware benchmark that compares **Cohere Aya Expanse** and **Meta Llama 4 Scout** on the same coding task, then combines deterministic validation with **DeepEval** judging.

## What this project is

This is not a generic coding chatbot. It is an experiment framework for a practical software-engineering question:

**Given the same existing codebase and the same requested change, which model produces the stronger implementation?**

Both models receive the same repository/task inputs. Their outputs are streamed in parallel, checked for obvious deterministic failures, evaluated on code quality, and compared head-to-head.

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
   Task-aware File Ranking
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
             (single or multi-file)
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

## Why repository-aware generation?

A valid standalone function is not necessarily a good change to an existing codebase. The benchmark therefore uses repository summary, structure, and task-ranked source context so the models can follow existing architecture and conventions.

For large repositories, the source is no longer blindly dumped into the model prompt. A lightweight lexical ranker selects the most task-relevant file sections and keeps the request within a bounded context budget. This is intentionally simple and dependency-light; semantic embeddings/vector retrieval are a possible future upgrade.

## Evaluation layers

### Deterministic validation

The benchmark separates objective checks from subjective model judgment:

- Python syntax/compile checks where applicable
- Basic HTML parsing
- Multi-file output detection
- Obvious hard-coded credential pattern scanning
- File and line counts
- Optional restricted Docker checks for generated multi-file workspaces

A passing syntax check does not prove functional correctness.

### DeepEval quality judgment

Three GEval metrics are used:

| Metric | What it checks |
|---|---|
| **Correctness** | Task compliance, expected behavior, edge cases, runtime risks, and repository fit |
| **Readability** | Naming, organization, formatting, documentation, and maintainability |
| **Best Practices** | Error handling, security, efficiency, modularity, and configuration hygiene |

DeepEval scores are kept in their native **0–1** range and shown in the dashboard on a **0–10** display scale. The current pass threshold is **0.70**.

### Pairwise model comparison

Because the benchmark's primary question is comparative, it also runs **ArenaGEval** to select a winner between Aya Expanse and Llama 4 Scout. Pairwise judging is used as a separate signal rather than replacing the individual quality scores.

## Large project and website behavior

A 10-line Python change and a full web application are different evaluation problems.

For a focused change, static checks plus semantic judging can provide useful evidence.

For a multi-file feature, the models are asked to return every changed file using a machine-readable `FILE:` format. The validator can inspect each supported file type.

For a full website or production feature, the benchmark can run the generated multi-file workspace through an optional Docker-based check. The sandbox disables network access, drops Linux capabilities, applies CPU/memory/process limits, and uses a temporary workspace. It does not automatically install dependencies or run arbitrary commands from the repository because those actions would weaken the security boundary.

The correct long-term evaluation path is:

```text
Generate patch
     |
     v
Apply to repository snapshot
     |
     v
Static checks
     |
     v
Isolated tests / build
     |
     v
Smoke / browser checks
     |
     v
Quality + latency + cost + failure metrics
```

## Security model

Repository content is untrusted input. Before model use, the ingestion layer redacts obvious credential patterns and the generation prompt explicitly treats repository comments, documentation, and strings as data rather than instructions.

Generated paths are checked to prevent `..` traversal before they are written to the sandbox. Generated code is not executed by the main Streamlit process.

Previously exposed credentials were revoked/rotated and the corresponding files were removed from the current branch. Removing a file from the latest commit does not erase old Git objects, so a history rewrite is still recommended when historical secrecy matters.

## Reproducible benchmark tasks

`benchmark_tasks.json` contains a starter task set covering bug fixes, features, refactors, security, frontend work, API changes, and multi-file changes.

For a meaningful model comparison, run each task multiple times and report at least:

- mean and median quality scores
- pass/fail rate
- pairwise win rate
- syntax/test/build failure rate
- latency
- token usage and cost when provider data is available

One task and one run are not enough to establish that one model is generally better.

## Known limitations

1. **Retrieval is lexical:** filename and token overlap can still miss semantically related files.
2. **Context can still be incomplete:** a large repository may contain important dependencies outside the selected context.
3. **Sandbox is conservative:** it does not install arbitrary dependencies or execute repository-defined commands by default.
4. **Language coverage is incomplete:** Python and basic HTML receive deterministic parsing; JavaScript/TypeScript/CSS need stronger project-aware validation.
5. **LLM judge variance:** semantic scores may vary between runs.
6. **Task quality matters:** ambiguous tasks can produce misleading benchmark conclusions.
7. **Provider effects matter:** model revisions, rate limits, latency, and provider behavior can affect comparisons.

## Recommended benchmark ladder

```text
Level 1  Focused function / bug fix
         -> retrieval + static checks + DeepEval

Level 2  Multi-file feature
         -> ranked context + multi-file output + validation

Level 3  Full application / website
         -> patch application + isolated test/build + smoke/browser checks
         -> repeated trials + latency/cost/failure reporting
```

## Setup

### 1. Clone

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
```

### 2. Create the environment

```bash
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

### 3. Configure credentials

Copy `.env.example` to `.env` and fill in your provider credentials locally.

The generation models use the provider-specific keys. DeepEval can use the configured evaluation model through its supported environment settings; this project also accepts `DEEPEVAL_MODEL` when you want to select it explicitly.

Never commit real credentials.

### 4. Run

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Describe one concrete coding change.
4. Compare Aya Expanse and Llama 4 Scout outputs.
5. Review the task-ranked files shown in the evaluation section.
6. Optionally provide reference code.
7. Click **Evaluate Latest Generation**.
8. For multi-file output, use **Run Isolated Checks** to run available deterministic checks in Docker.
9. Compare individual scores, evidence level, and the pairwise winner.

## Project structure

```text
.
├── app.py
├── model_service.py
├── code_ingestion.py
├── context_retrieval.py
├── code_validation.py
├── code_evaluation.py
├── sandbox_runner.py
├── benchmark_tasks.json
├── BENCHMARK.md
├── tests/
├── requirements.txt
├── pyproject.toml
├── .python-version
├── .env.example
├── .gitignore
├── LICENSE
└── README.md
```

## Technology

- Python 3.12+
- Streamlit
- LiteLLM
- GitIngest
- DeepEval / GEval / ArenaGEval
- Pandas
- Plotly
- Docker (optional sandbox checks)
- Cohere Aya Expanse
- Meta Llama 4 Scout

## Roadmap

- Improve retrieval with semantic embeddings and dependency-aware file selection.
- Add deterministic JavaScript/TypeScript/CSS project validation.
- Add repository test discovery without blindly executing untrusted scripts.
- Add browser-level smoke tests in an isolated environment.
- Track latency, token usage, failures, and cost per model.
- Run the full task suite repeatedly and export JSON/CSV reports.
- Add CI regression checks for benchmark protocol code.

## License

MIT License — see [`LICENSE`](LICENSE).

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
