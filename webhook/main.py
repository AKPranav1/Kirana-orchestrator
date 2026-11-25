"""Compatibility entry point; Twilio is an optional adapter on the same backend."""
from backend.app import app

__all__ = ["app"]
