# LLM Code Generation Benchmark

> Compare **Cohere Aya Expanse** and **Meta Llama 4 Scout** on repository-aware Python code generation and evaluate outputs with **DeepEval**.

## Overview

An interactive Streamlit benchmark for comparing two LLMs on code-generation tasks grounded in an existing GitHub repository.

### Workflow

1. Ingest a GitHub repository with GitIngest.
2. Build repository-aware prompts from the ingested context.
3. Stream Aya Expanse and Llama 4 Scout responses in parallel through LiteLLM.
4. Optionally provide reference code.
5. Evaluate generated code with DeepEval GEval metrics.
6. Compare model scores and evaluator reasoning in the Streamlit dashboard.

## Architecture

```text
GitHub Repository
       |
       v
   GitIngest
       |
       v
Repository Context
       |
   +---+---+
   |       |
   v       v
Aya      Llama 4 Scout
   |       |
   +---+---+
       |
 Generated Code
       |
       v
    DeepEval
       |
 +-----+-----+----------+
 |           |          |
Correctness Readability Best Practices
       |
       v
Streamlit Dashboard
```

## Features

- Repository-aware code generation
- Parallel streaming responses
- Optional reference / ground-truth code
- DeepEval GEval evaluation
- Side-by-side model comparison
- Interactive Plotly visualization
- Detailed evaluator reasoning

## Tech Stack

- Python 3.12+
- Streamlit
- LiteLLM
- Cohere Aya Expanse
- Meta Llama 4 Scout
- GitIngest
- DeepEval
- Pandas / Plotly
- python-dotenv

## Project Structure

```text
.
├── app.py                 # Streamlit UI and application flow
├── model_service.py       # LLM calls and parallel streaming
├── code_ingestion.py      # GitHub repository ingestion
├── code_evaluation.py     # DeepEval metrics and scoring
├── requirements.txt
├── pyproject.toml
├── .python-version
├── .env.example
├── assets/
└── README.md
```

## Setup

### 1. Clone

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
```

### 2. Environment

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

### 3. API keys

Create `.env` locally from `.env.example`:

```env
CEREBRAS_API_KEY=your_cerebras_api_key
COHERE_API_KEY=your_cohere_api_key
```

Never commit `.env` or real API keys.

### 4. Run

```bash
streamlit run app.py
```

## Usage

1. Enter a public GitHub repository URL.
2. Click **Ingest Repository**.
3. Enter a coding request.
4. Compare Aya Expanse and Llama 4 Scout outputs.
5. Optionally add reference code.
6. Click **Evaluate Generated Code**.
7. Review correctness, readability, and best-practice scores.

## Evaluation Methodology

| Metric | Evaluates |
|---|---|
| Correctness | Functionality, edge cases, runtime risks, expected behavior |
| Readability | Naming, formatting, documentation, structure |
| Best Practices | Error handling, security, efficiency, modularity |

The dashboard reports the arithmetic mean of the three metric scores as the overall score. Because GEval uses an LLM judge, results should be treated as a comparative signal rather than absolute proof of correctness.

## Security

- Keep `.env` local.
- Rotate credentials that were ever committed publicly.
- Never store secrets in source files, notebooks, screenshots, or logs.
- Use deployment/CI secret stores for hosted environments.

## Roadmap

- Add a reusable coding-task benchmark dataset
- Run multiple trials and report mean / variance
- Track latency, token usage, and error rate
- Add automated tests
- Add CI linting and test checks
- Export benchmark reports
- Compare additional open LLMs

## License

No license is currently declared. Add a license before encouraging external reuse or contributions.

## Author

**Adarsh Kumar Singh** — [GitHub](https://github.com/ADARSH010203)
