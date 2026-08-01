"""Compatibility entrypoint for existing uvicorn commands."""

from app.main import app

__all__ = ["app"]
