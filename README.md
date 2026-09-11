# LLM Code Generation Benchmark

> Compare **Cohere Aya Expanse** and **Meta Llama 4 Scout** on repository-aware code-generation tasks using deterministic validation and **DeepEval**.

## What this project is

This project evaluates a practical software-engineering question:

**When two LLMs are asked to modify an existing repository, which one produces the more useful implementation?**

Both models receive the same repository context and coding task. Their outputs are generated in parallel, checked for basic static evidence, and then judged using the same criteria.

The project does not treat an LLM score as a probability that code is correct. A small utility and a full website require different levels of evidence.

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
          Generated Output
                 |
       +---------+-----------+
       |         |           |
       v         v           v
    Syntax    Security   File Structure
       \         |          /
        \        |         /
         +-------+--------+
                 |
                 v
              DeepEval
                 |
       +---------+---------+---------+
       |                   |         |
       v                   v         v
 Correctness          Readability  Best Practices
                 |
                 v
          Streamlit Dashboard
```

## What happens during generation

Each model receives the same:

1. repository summary
2. repository structure
3. repository source context
4. user task
5. implementation rules

For a single-file task, the model can return the implementation directly. For a larger change, it can return multiple files using:

```text
FILE: app/main.py
```python
...
```

FILE: templates/index.html
```html
...
```
```

The repository context is capped before the request so very large repositories do not create an uncontrolled prompt size. True file-level retrieval/ranking is a future improvement.

## Evaluation

### Deterministic validation

The benchmark checks generated output without executing untrusted model code. Python files can be parsed and compiled, HTML files receive a basic parser check, and obvious hard-coded credential patterns are flagged. These checks provide evidence about the artifact but do not prove functional correctness. Python's documentation distinguishes parsing/compilation from successful runtime behavior. citeturn914181search3

A security finding is treated as a hard failure instead of being averaged away by a high semantic score.

### DeepEval

DeepEval GEval exposes its metric `score` on a **0–1 scale**, while its optional rubric ranges can be written from 0–10. This project therefore uses a **0.70** internal passing threshold and displays scores as 0–10 for readability. citeturn914181search0turn914181search2

| Metric | What it checks |
|---|---|
| **Correctness** | Task compliance, expected behavior, edge cases, runtime risks, and repository integration |
| **Readability** | Naming, formatting, organization, documentation, and maintainability |
| **Best Practices** | Error handling, security, efficiency, modularity, and configuration safety |

The displayed overall score is the arithmetic mean of these three DeepEval scores.

## How to interpret the result

An **8.7/10** result means the evaluator judged the implementation strongly against the defined criteria. It does **not** mean there is an 87% probability that the code is correct.

A defensible benchmark claim needs a fixed task set, repeated runs, executable tests, and statistical reporting.

## Test ladder

### Small task — roughly 10–30 lines

Examples: a helper function, validation rule, focused bug fix, or small API change.

Recommended evidence:

- syntax/compile checks where supported
- security scan
- DeepEval review
- reference implementation when available

### Medium task — several modules

Examples: service + utility + configuration changes.

Recommended evidence:

- structured multi-file output
- validation for every detected file
- expected behavior or reference implementation
- repository integration tests where available
- DeepEval review

### Large task — full feature or website

This is an **integration task**, not one giant code-generation answer.

A serious evaluator should materialize every generated file in an isolated workspace, install dependencies, run the repository's tests, build the application, and perform smoke/browser checks. The current repository deliberately does not execute arbitrary model-generated code.

## Practical answer to “how correct is it?”

For a 10-line Python function, the current system can provide useful evidence that the code parses and compiles, contains no obvious credential pattern, and looks correct to the LLM judge. That still does not establish business-logic correctness unless there are tests or a trusted reference.

For a full website, the current system should **not** say “the website is 90% correct.” Without dependency installation, build, runtime, browser, and end-to-end checks, that number would be misleading.

## Current limitations

- No sandboxed runtime execution yet.
- JavaScript and CSS do not have language-specific syntax validation yet.
- HTML parsing is not equivalent to browser rendering.
- One model run is insufficient for a statistically strong comparison.
- Large repositories can still lose relevant details because broad context is truncated; retrieval-based file selection is the next improvement.
- Provider availability, rate limits, model versions, and API behavior can affect results.
- LLM-as-a-judge can vary between runs.

## Security

- Credentials are loaded from environment variables.
- `.env` is ignored and `.env.example` contains placeholders only.
- Never commit API keys, tokens, passwords, or private configuration.
- Previously exposed credentials were removed from the current branch and should remain revoked/rotated.
- Generated code is not executed on the host machine by this application.
- Any future execution runner should use an isolated sandbox with strict CPU, memory, filesystem, network, and time controls.

**History note:** removing a credential from the latest tree does not erase older Git objects. A complete secret-removal process should also rewrite repository history before considering the history clean.

## Roadmap

- Fixed benchmark task dataset
- Multiple trials per task
- Mean, median, variance, and confidence reporting
- Sandboxed execution and test orchestration
- JavaScript/CSS static checks
- Build and browser smoke tests for web projects
- Latency, token, cost, and failure-rate tracking
- JSON/CSV result export
- CI quality checks
- Additional code-generation models

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

Copy `.env.example` to `.env` and add your own provider credentials. Never commit `.env`.

Run the app:

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Ingest the repository.
3. Describe the code change.
4. Compare both model outputs.
5. Optionally provide reference code.
6. Run evaluation.
7. Review the 0–10 scores **and** the validation evidence.

## Project structure

```text
.
├── app.py
├── model_service.py
├── code_ingestion.py
├── code_validation.py
├── code_evaluation.py
├── requirements.txt
├── pyproject.toml
├── .python-version
├── .env.example
├── .gitignore
├── BENCHMARK.md
├── LICENSE
└── README.md
```

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
