# LLM Code Generation Benchmark

Repository-aware AI coding benchmark comparing Qwen 3.6 27B on Groq with NVIDIA Nemotron 3 Super 120B A12B on OpenRouter.

## Models

- Groq: `qwen/qwen3.6-27b`
- OpenRouter: `nvidia/nemotron-3-super-120b-a12b:free`

The same repository context and coding task are sent to both models, followed by validation, sandbox checks, DeepEval, pairwise comparison, and bounded self-repair.

## Setup

```bash
pip install -r requirements.txt
streamlit run app.py
```

```env
GROQ_API_KEY=
OPENROUTER_API_KEY=
DEEPEVAL_MODEL=openrouter/free
```

Never commit real API keys.
