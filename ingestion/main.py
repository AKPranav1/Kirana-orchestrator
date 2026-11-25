"""Compatibility entry point. Run from repository root: uvicorn backend.app:app."""
from backend.app import app

__all__ = ["app"]
