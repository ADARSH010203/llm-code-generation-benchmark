# Benchmark Protocol

The benchmark is designed to measure **repository-aware code generation**, not just whether an isolated snippet looks plausible.

## Evaluation ladder

### Level 1 — Focused change

Examples: one function, a small bug fix, or a single module change.

Run:

1. Deterministic syntax/security checks.
2. DeepEval correctness, readability, and best-practice judging.
3. Optional reference-based correctness evaluation.

### Level 2 — Multi-file feature

Examples: adding a small API endpoint, component, or service that spans several files.

Run the same evaluation, but require the models to return every changed file using the `FILE:` format. Validate every supported source file that is detected.

### Level 3 — Full application / website

A complete website is an integration problem. A strong benchmark should:

1. Apply the generated patch in an isolated workspace.
2. Install dependencies from the generated/project lockfiles.
3. Run the repository's tests.
4. Build the application.
5. Run smoke or browser checks where appropriate.
6. Capture failures, latency, token usage, and resource cost.

The current Streamlit application intentionally stops before arbitrary code execution. This avoids turning an interactive evaluator into an execution environment for untrusted model output.

## What the current implementation measures

| Signal | Current behavior |
|---|---|
| Repository grounding | GitIngest summary + structure + bounded source context |
| Secret exposure | Obvious credential patterns are redacted from ingested source and flagged in generated output |
| Python syntax | AST parse + compilation without executing the generated program |
| HTML | Lightweight parser validation |
| Multi-file output | `FILE:` blocks are detected and counted |
| Semantic quality | DeepEval GEval correctness, readability, best practices |
| Relative model choice | DeepEval ArenaGEval pairwise comparison |
| Statistical reliability | Not yet available; multi-run benchmark dataset is planned |

## Scoring

DeepEval metric scores are kept in their native **0–1** range. The dashboard multiplies them by 10 for human-readable display. The current per-metric pass threshold is `0.70`.

The overall score is the arithmetic mean of the three GEval metrics. It is a quality signal, not a probability that the code is correct.

For the model-selection question, the benchmark also uses a pairwise ArenaGEval comparison. Pairwise judging is appropriate when the question is “which candidate is better?” rather than “does this single candidate pass a fixed bar?”

## Large-repository handling

Repository source is capped by `MAX_CONTEXT_CHARS` before generation. This prevents an uncontrolled prompt from growing with repository size, but simple truncation can hide the exact file needed for a task.

This is why **file-aware retrieval/ranking is a planned improvement**. Until that exists, results from very large repositories should be considered lower-confidence.

## Threat model

The benchmark treats both repository content and model output as untrusted input.

It therefore avoids executing generated code, avoids placing repository credentials directly into prompts when obvious secret patterns can be detected, and keeps provider credentials in environment variables.

Static checks are intentionally conservative. A security scan that reports “clean” does not prove the absence of vulnerabilities, and a successful syntax check does not prove functional correctness.

## Reproducibility requirements

For a meaningful published comparison, fix and record:

- task text and task dataset version
- repository commit / revision
- model identifiers
- generation settings
- evaluation model and metric definitions
- number of trials
- time of evaluation
- failures and timeouts

A single run should not be presented as a universal ranking.
