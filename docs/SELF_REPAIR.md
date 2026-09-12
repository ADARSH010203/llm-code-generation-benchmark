# Self-Repair Agent

The benchmark now supports a bounded generate → validate → sandbox → repair loop.

## Flow

```text
Initial candidate
      ↓
Static validation
      ↓
Isolated deterministic checks
      ↓
Failure evidence
      ↓
Repair model
      ↓
Re-test
      ↓
Best candidate / pass
```

The loop has a configurable retry budget and never executes generated code directly in the Streamlit process. Repository-backed checks use the existing restricted Docker sandbox.

## Why it matters

A coding agent should be evaluated on whether it can recover from concrete failures, not only on its first response. Each repair request contains the task, bounded repository context, current candidate, and observed deterministic failure evidence.

## Safety boundaries

- Maximum repair attempts are explicitly bounded.
- Empty repair responses stop the loop.
- Candidate ranking is based on deterministic evidence rather than an LLM deciding that its own output is correct.
- Docker checks remain network-isolated with resource limits.
- Arbitrary dependency installation and arbitrary host execution are not enabled.
