# Benchmark Protocol

This repository is designed to compare code-generation models, not to claim that an LLM score is the probability that code is correct.

## Recommended test ladder

### 1. Small change
Use a focused task such as adding one function or fixing one bug. Record the generated code, deterministic syntax/security checks, and DeepEval scores.

### 2. Medium change
Ask for a change spanning a few modules. Use the multi-file output format and check every detected source file. Supply a reference implementation when practical.

### 3. Full feature / website
Treat this as an integration task. The model should return all files it creates or changes. Semantic evaluation alone is insufficient; a serious benchmark should also install dependencies, build the project, run tests, and perform a smoke test in an isolated environment.

## What the current implementation verifies

- Model outputs are generated under the same task and repository context.
- Python files can be parsed and compiled without running them.
- HTML files receive a basic parser check.
- Obvious hard-coded credential patterns are flagged.
- DeepEval judges correctness, readability, and best practices.

## What it does not verify yet

- Application runtime behavior
- Browser behavior for JavaScript/CSS
- Dependency installation success
- End-to-end integration
- Functional tests or test coverage
- Performance under load
- Security of arbitrary generated code execution

## Why this matters

A 20-line utility and a 200-file website should not be evaluated as if they were the same kind of task. The benchmark therefore reports deterministic evidence separately from the LLM judge and keeps execution verification explicitly false until a sandboxed test runner is added.

## Next benchmark milestone

The next step is an isolated execution harness that accepts a generated multi-file artifact, installs only declared dependencies, applies CPU/memory/time limits, runs a known test suite, and records pass/fail, latency, and resource usage. That result can then be combined with DeepEval rather than replaced by it.
