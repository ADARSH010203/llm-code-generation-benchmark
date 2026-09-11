# LLM Code Generation Benchmark

> A repository-aware benchmark that compares **Cohere Aya Expanse** and **Meta Llama 4 Scout** on the same coding task, then evaluates both implementations with deterministic checks and **DeepEval**.

## What this project is

This is not a generic coding chatbot. The project is designed to answer a practical software-engineering question:

**Given the same existing codebase and the same requested change, which model produces the stronger implementation?**

Both models receive the same repository context and task. Their outputs are streamed in parallel, validated without executing untrusted code, scored on three quality dimensions, and compared head-to-head.

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
               Pairwise Model Judge
                       |
                       v
                Streamlit Dashboard
```

## Why repository-aware generation?

Generating a correct standalone function is easier than making a change that fits an existing application. The benchmark therefore provides repository summary, structure, and source context to both models and asks them to preserve existing patterns instead of treating every task as greenfield development.

For larger repositories, source context is bounded to a configurable request budget. This avoids unbounded prompts, but it also means that context truncation can hide relevant files. That is a known limitation; true file-level retrieval/ranking is a planned improvement.

## What is evaluated?

### 1. Deterministic validation

The benchmark performs checks that do not depend on an LLM judge:

- Python syntax/compilation checks where applicable
- Basic HTML parsing
- Multi-file output detection
- Obvious hard-coded credential pattern scanning
- File and line counts

These checks are evidence, not a correctness guarantee.

### 2. DeepEval quality judgment

Three GEval metrics are used:

| Metric | What it checks |
|---|---|
| **Correctness** | Task compliance, expected behavior, edge cases, runtime risks, and repository fit |
| **Readability** | Naming, organization, formatting, documentation, and maintainability |
| **Best Practices** | Error handling, security, efficiency, modularity, and configuration hygiene |

DeepEval metrics are kept internally on their native **0–1** scale and shown in the UI on a **0–10** display scale. The current pass threshold is **0.70**. DeepEval documents its metric scores as 0–1, while GEval rubrics may still be written with 0–10 score ranges. citeturn899808search3turn899808search5

### 3. Pairwise comparison

Because the project's main question is comparative, it also uses DeepEval's **ArenaGEval** to choose a winner between the two outputs. ArenaGEval is designed for pairwise model/prompt comparisons and uses blinded, randomized positioning to reduce simple position/verbosity bias. citeturn620285search0turn620285search6

## Large project / website behavior

A 10-line Python change and a full web application should not be treated as the same benchmark task.

For a small change, static validation plus semantic judging can provide useful feedback.

For a medium multi-file change, the models must return all required files and the benchmark checks each detected Python/HTML file where it has a validator.

For a full website or production feature, semantic judging alone is insufficient. A serious evaluation should apply the generated patch in an isolated environment, install dependencies, run repository tests, build the application, and perform smoke/browser checks. This project intentionally does **not** execute arbitrary generated code inside the Streamlit process.

This is consistent with modern repository-level coding benchmarks such as SWE-bench, where generated patches are applied to real repositories and verified using repository tests in isolated environments. citeturn565269search4turn565269search7

## Security model

Repository code is untrusted input. Before model use, obvious credential patterns are redacted from ingested source. Generated output is never executed by this application.

Keep provider credentials in local environment files or deployment secret stores. Never commit real values. The repository's `.env.example` documents the required variables without containing credentials.

Credentials that were previously exposed in the old repository state were revoked/rotated and the files were removed from the current branch. Removing a file from the latest commit does not erase it from older Git objects, so a history rewrite is still recommended if the repository needs to be treated as historically clean.

## Evidence and limitations

LLM-as-a-judge is useful but not ground truth. DeepEval itself recommends choosing evaluation techniques based on the task shape, and pairwise judging is specifically useful when the question is which model/version is better. citeturn565269search0turn620285search6

Known limitations:

1. **Context truncation:** very large repositories can exceed the configured source budget and hide relevant files.
2. **No arbitrary execution:** current evaluation does not safely run generated code, install generated dependencies, or run browser tests.
3. **Static language coverage:** syntax checks are currently limited to supported file types; JavaScript/TypeScript/CSS require stronger validators.
4. **LLM judge variance:** semantic scores can change between runs and should not be treated as objective truth.
5. **Single-run noise:** one task and one generation are not enough to establish a general model ranking.
6. **Provider effects:** latency, rate limits, model revisions, and provider behavior can influence results.
7. **Task quality matters:** broken or ambiguous coding tasks can produce misleading benchmark conclusions. Recent audits of software-engineering benchmarks have shown that task quality itself can materially affect evaluation validity. citeturn565269search11

## Recommended benchmark ladder

```text
Level 1  Focused function / bug fix
         -> static checks + DeepEval

Level 2  Multi-file feature
         -> file-aware validation + tests when available

Level 3  Full application / website
         -> isolated patch application
         -> dependency install
         -> tests + build
         -> smoke/browser checks
         -> resource + failure metrics
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

Copy `.env.example` to `.env.local` and fill in the provider credentials locally.

The two generation models use their respective provider keys. DeepEval also requires an evaluation-model credential; by default this project documents an OpenAI-compatible evaluator through `OPENAI_API_KEY` and `DEEPEVAL_MODEL`.

Do not commit `.env`, `.env.local`, or real credentials.

### 4. Run

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Describe one concrete coding change.
4. Compare Aya Expanse and Llama 4 Scout outputs.
5. For multi-file changes, review every returned `FILE:` block.
6. Optionally provide a reference implementation.
7. Click **Evaluate Latest Generation**.
8. Review deterministic evidence, individual scores, and the pairwise winner.

## Project structure

```text
.
├── app.py
├── model_service.py
├── code_ingestion.py
├── code_validation.py
├── code_evaluation.py
├── BENCHMARK.md
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
- Cohere Aya Expanse
- Meta Llama 4 Scout

## Roadmap

- Replace simple truncation with file-aware retrieval/ranking for large repositories.
- Add deterministic JavaScript/TypeScript/CSS validation.
- Add isolated execution for trusted benchmark tasks only.
- Run a fixed dataset of coding tasks with multiple trials.
- Track latency, token usage, failures, and cost.
- Add test/build/browser success as first-class benchmark outcomes.
- Export reproducible JSON/CSV benchmark reports.
- Add CI regression evaluations.

## License

MIT License — see [`LICENSE`](LICENSE).

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
