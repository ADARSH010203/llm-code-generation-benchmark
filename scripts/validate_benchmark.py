"""Validate the checked-in benchmark task set for CI/local development."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the repository root importable when this file is executed directly
# with `python scripts/validate_benchmark.py` from the repository root.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from benchmark.tasks import load_tasks


def main() -> int:
    tasks = load_tasks()
    categories = sorted({task.category for task in tasks})
    print(f"Validated {len(tasks)} benchmark tasks across {len(categories)} categories.")
    print("Categories:", ", ".join(categories))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
