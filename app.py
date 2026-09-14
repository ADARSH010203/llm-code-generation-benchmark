"""Compatibility import for deployments that historically targeted ``app:app``.

Run the new browser interface with ``uvicorn server:app --reload``.
"""

from server import app

__all__ = ["app"]
