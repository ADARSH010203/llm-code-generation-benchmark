# LLM Code Generation Benchmark

> Compare **Cohere Aya Expanse** and **Meta Llama 4 Scout** on repository-aware Python code generation and evaluate both outputs with **DeepEval**.

## What this project does

This project is a small, reproducible benchmark rather than a generic chatbot. It tests a practical question:

**When two LLMs are asked to add code to an existing repository, how well do their implementations fit the repository and the requested task?**

The application gives both models the same repository context and the same coding task, streams their outputs side by side, and then evaluates the generated code using the same criteria.

## Workflow

```text
GitHub Repository
       |
       v
    GitIngest
       |
       v
Summary + Structure + Source Context
       |
       +-------------------+
       |                   |
       v                   v
Aya Expanse          Llama 4 Scout
       |                   |
       +---------+---------+
                 |
                 v
          Generated Code
                 |
                 v
              DeepEval
                 |
       +---------+---------+---------+
       |                   |         |
       v                   v         v
 Correctness          Readability  Best Practices
       |                   |         |
       +---------+---------+---------+
                 |
                 v
          Streamlit Dashboard
```

## Core components

- `code_ingestion.py` — converts a GitHub repository into model-ready context.
- `model_service.py` — keeps provider/model configuration in one place and streams both models asynchronously.
- `code_evaluation.py` — runs the three DeepEval GEval metrics and produces a 0–10 overall score.
- `app.py` — handles the Streamlit workflow, session state, generation UI, evaluation, and comparison charts.

## Why repository context matters

A code-generation model can produce valid Python while still being a poor contribution to an existing codebase. This benchmark therefore includes the repository summary, structure, and source content in the generation prompt.

The prompt asks the models to preserve existing architecture, naming, configuration patterns, error handling, and security practices instead of treating every request as a greenfield coding problem.

## Evaluation

| Metric | What it checks |
|---|---|
| **Correctness** | Task compliance, functional behavior, edge cases, runtime risks, and integration concerns |
| **Readability** | Naming, formatting, organization, documentation, and maintainability |
| **Best Practices** | Error handling, security, efficiency, modularity, and safe configuration |

Each metric is scored from **0 to 10**. The overall score is the arithmetic mean of the three metrics. A score of **7.0 or higher** is marked as passing.

An optional reference implementation can be supplied to make correctness comparisons more concrete.

### Important interpretation

DeepEval GEval is an **LLM-as-a-judge** approach. It provides a useful comparative signal, but an LLM score is not proof that generated code is executable or production-ready. A stronger benchmark should combine these judgments with automated tests, static analysis, execution checks, latency, token usage, and repeated trials.

## Security

- API credentials are loaded from environment variables, never from source code.
- `.env` is ignored and `.env.example` contains only placeholders.
- Credentials that were previously exposed in the repository were removed from the current branch and should remain revoked/rotated.
- Do not put secrets in source files, notebooks, screenshots, logs, or benchmark outputs.
- For deployment, use the platform's secret-management facility.

**History note:** removing a secret from the latest commit does not automatically remove it from older Git commits. Because the previously exposed credentials were rotated/revoked, they should no longer be usable. A full Git-history rewrite is still recommended before treating the repository history as clean.

## Known limitations

1. **Single-task evaluation:** the current UI evaluates one generation at a time rather than a fixed benchmark suite.
2. **LLM-judge dependence:** scores can vary between evaluation runs and should not be treated as ground truth.
3. **No execution-based correctness yet:** generated code is evaluated semantically, but the project does not currently run arbitrary generated code in a sandbox.
4. **Repository size:** sending a large repository's complete source content to an LLM can increase latency, cost, and context-window pressure.
5. **Model/provider differences:** provider latency, rate limits, model versions, and API behavior can affect comparisons.
6. **No statistical reporting yet:** a single run is not enough to make a strong claim that one model is better overall.

## Roadmap

- Add a fixed set of representative coding tasks.
- Run multiple trials per task and report mean, median, and variance.
- Add execution-based tests in an isolated sandbox.
- Track latency, token usage, failures, and cost.
- Add static analysis and formatting checks.
- Export benchmark results to CSV/JSON.
- Add CI for deterministic project checks.
- Compare additional models using the same evaluation protocol.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
```

### 2. Create a virtual environment

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

### 3. Configure credentials locally

Copy `.env.example` to `.env` and add your own provider credentials. Never commit `.env`.

### 4. Start the application

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Describe the code change you want.
4. Compare the two generated implementations.
5. Optionally provide a reference implementation.
6. Click **Evaluate Latest Generation**.
7. Review the metric scores and evaluator reasoning.

## Project structure

```text
.
├── app.py
├── model_service.py
├── code_ingestion.py
├── code_evaluation.py
├── requirements.txt
├── pyproject.toml
├── .python-version
├── .env.example
├── .gitignore
└── README.md
```

## Technology

- Python 3.12+
- Streamlit
- LiteLLM
- GitIngest
- DeepEval
- Pandas
- Plotly
- Cohere Aya Expanse
- Meta Llama 4 Scout

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
