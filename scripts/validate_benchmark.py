"""Validate the checked-in benchmark task set for CI/local development."""

from __future__ import annotations

from benchmark.tasks import load_tasks


def main() -> int:
    tasks = load_tasks()
    categories = sorted({task.category for task in tasks})
    print(f"Validated {len(tasks)} benchmark tasks across {len(categories)} categories.")
    print("Categories:", ", ".join(categories))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
