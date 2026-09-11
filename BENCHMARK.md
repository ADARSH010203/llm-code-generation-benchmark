# Benchmark Protocol

This benchmark compares model outputs using deterministic validation and DeepEval. An LLM score is not treated as a probability of correctness.

## Test ladder

### Small change
Use a focused function or bug fix. Run syntax/compile checks, security scanning, and DeepEval. Add reference code when possible.

### Medium change
Use structured multi-file output and validate every detected source file. Use repository tests when they exist.

### Full feature or website
Treat the result as an integration artifact. A strong evaluation should materialize generated files in an isolated workspace, install declared dependencies, run tests, build the application, and perform smoke/browser checks. The current application deliberately does not execute arbitrary generated code.

## Current evidence

- Both models receive the same task and repository context.
- Python output can be parsed and compiled without executing it.
- HTML output receives a basic parser check.
- Obvious hard-coded credential patterns are flagged.
- DeepEval judges correctness, readability, and best practices.

## Important limitation

A program can compile and still be functionally wrong. A website can contain valid HTML and still fail because of JavaScript, CSS, dependencies, missing assets, or integration problems. The benchmark reports validation evidence separately from the LLM-judge score for that reason.
