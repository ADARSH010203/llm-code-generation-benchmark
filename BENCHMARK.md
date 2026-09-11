# Benchmark Protocol

The benchmark measures **repository-aware code generation**, not only whether an isolated snippet looks plausible.

## Evaluation ladder

### Level 1 — Focused change

Examples: one function, a small bug fix, or a single module change.

Run:

1. Deterministic syntax/security checks.
2. DeepEval correctness, readability, and best-practice judging.
3. Optional reference-based correctness evaluation.

### Level 2 — Multi-file feature

Examples: a small API endpoint, component, or service spanning several files.

Run the same evaluation, but require every changed file in the `FILE:` format. Review retrieval coverage and validate every supported file that is detected.

### Level 3 — Full application / website

A complete website is an integration problem. The target evaluation path is:

1. Apply the generated files/patch to a repository snapshot.
2. Perform deterministic static checks.
3. Run safe tests/build steps inside an isolated environment.
4. Run smoke/browser checks where appropriate.
5. Record failures, timeouts, latency, token usage, and cost.

The current sandbox implements a conservative subset of this ladder. It clones a public repository, overlays the generated multi-file output, and runs only predefined low-risk commands. It disables container networking, drops Linux capabilities, limits CPU/memory/processes, and does not automatically install dependencies or execute arbitrary repository scripts.

## Current implementation

| Signal | Current behavior |
|---|---|
| Repository grounding | GitIngest summary + structure + sanitized source |
| Context selection | Task-aware lexical file ranking with a bounded context budget |
| Prompt safety | Repository content is treated as untrusted data; prompt-injection instructions inside source are not followed |
| Secret exposure | Obvious credential patterns are redacted before model use and scanned in generated output |
| Python syntax | AST parse + compilation without running generated Python in the app process |
| HTML | Lightweight parser validation |
| Multi-file output | `FILE:` blocks are detected and safely materialized |
| Sandbox | Optional Docker checks for a cloned repository snapshot |
| Semantic quality | DeepEval GEval correctness, readability, best practices |
| Relative model choice | DeepEval ArenaGEval pairwise comparison |
| Repeated-trial statistics | Not yet automated; starter task suite is included |
| Operational metrics | Latency/token/cost collection is planned |

## Scoring

DeepEval metrics return scores in the native **0–1** range. The dashboard multiplies those values by 10 for readability. The current per-metric pass threshold is `0.70`.

The overall score is the arithmetic mean of the three GEval scores. It is a quality signal, not a probability that the implementation is correct.

ArenaGEval is used separately for the comparative question: **which candidate is better?** Its result should not be merged into the numerical overall score.

## Large-repository handling

The original architecture could place the full repository source into a single model request. That becomes unreliable as repository size grows.

The current implementation instead ranks candidate file sections against the task and sends a bounded set of relevant sections. This reduces context pressure, but lexical ranking can still miss semantically related files.

For high-quality large-repository evaluation, the next retrieval layer should combine:

- lexical signals
- semantic embeddings
- import/dependency relationships
- repository structure
- task-specific file-type priors

## Security model

The benchmark treats repository content and generated output as untrusted.

Important boundaries:

- Provider credentials stay outside source files.
- Obvious credentials in ingested source are redacted before model use.
- Generated paths cannot escape the sandbox workspace.
- Generated code is not executed by the main Streamlit process.
- Docker execution uses no network, reduced privileges, and resource limits.
- Dependency installation is deliberately not automatic because it would expand the attack surface and make execution behavior repository-dependent.

A clean static scan does not prove that a program has no vulnerabilities.

## Reproducibility

For a meaningful model comparison, record:

- benchmark task ID and task text
- repository URL and exact revision
- model identifier and provider
- generation settings
- evaluation model and metric definitions
- retrieval settings
- number of trials
- timestamp
- failures, timeouts, and execution results

Use the included `benchmark_tasks.json` as the starting task set. Run each task multiple times before making model-level claims.

## Suggested analysis

For each model, report:

```text
Quality score       mean / median / variance
Task pass rate      passed tasks / total tasks
Pairwise win rate   wins / comparisons
Syntax failure rate failed static checks / total
Test/build failure  failed execution checks / executed checks
Latency             time to first token + total generation time
Cost                provider-reported or estimated cost
```

A single task, a single prompt, or a single run should not be presented as evidence that one model is universally better.

## Limitations

1. Lexical retrieval can miss semantically relevant files.
2. Context selection can still omit important dependencies in very large repositories.
3. The sandbox intentionally does not perform arbitrary dependency installation.
4. Browser-level testing is not yet integrated.
5. LLM judge scores are nondeterministic.
6. Model/provider revisions can change results over time.
7. Ambiguous benchmark tasks can invalidate otherwise careful measurements.
