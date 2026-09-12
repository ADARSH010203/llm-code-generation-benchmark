# LLM Code Generation Benchmark

Repository-aware AI coding benchmark comparing **Qwen 3.6 27B on Groq** with **NVIDIA Nemotron 3 Super 120B A12B (free) on OpenRouter** under the same task, retrieval context, validation, sandbox, DeepEval, and self-repair policy.

## Models

| Candidate | Provider | Model ID |
|---|---|---|
| Qwen 3.6 27B | Groq | `qwen/qwen3.6-27b` |
| NVIDIA Nemotron 3 Super 120B A12B | OpenRouter | `nvidia/nemotron-3-super-120b-a12b:free` |

Groq documents `qwen/qwen3.6-27b` as a hosted model, while OpenRouter lists the Nemotron free endpoint as zero-priced and rate-limited. citeturn325729search0turn325729search1

## Workflow

```text
GitHub Repository
      ↓
Task-aware Retrieval
      ↓
┌──────────────────┐
↓                  ↓
Groq / Qwen     OpenRouter / Nemotron
↓                  ↓
└────────┬─────────┘
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
Best Candidate + Trace
         ↓
Streamlit Dashboard
```

## Capabilities

- Repository-aware context retrieval with bounded prompts.
- Single-file and multi-file generation using `FILE: path` blocks.
- Python/HTML static validation and credential-pattern scanning.
- Restricted Docker execution with no network access.
- DeepEval correctness, readability, and best-practices scoring.
- Blinded pairwise comparison with ArenaGEval.
- Bounded self-repair based on observed deterministic failures.
- Reproducible tasks in `data/benchmark_tasks.json`.

## Setup

```bash
git clone https://github.com/ADARSH010203/llm-code-generation-benchmark.git
cd llm-code-generation-benchmark
python -m venv .venv
pip install -r requirements.txt
```

Create `.env` from `.env.example`:

```env
GROQ_API_KEY=
OPENROUTER_API_KEY=
DEEPEVAL_MODEL=openrouter/free
```

Run:

```bash
streamlit run app.py
```

## Security

Repository content and model output are treated as untrusted data. Credentials remain in environment variables, generated paths are restricted, and arbitrary generated code is not executed in the Streamlit process. Self-repair attempts are explicitly bounded.

## Structure

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
├── docs/
├── scripts/validate_benchmark.py
├── tests/
├── .github/workflows/ci.yml
├── .env.example
├── pyproject.toml
└── requirements.txt
```

## Roadmap

Dependency-aware retrieval, stronger language-specific execution, browser smoke tests, multi-trial benchmark statistics, JSON/CSV exports, CI regression benchmarks, and patch/PR mode.

## License

MIT License — see `LICENSE`.

## Author

**Adarsh Kumar Singh** — https://github.com/ADARSH010203
