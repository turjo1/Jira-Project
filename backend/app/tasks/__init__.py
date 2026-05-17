"""Celery tasks for async job processing."""
from app.tasks.sync import celery_app

__all__ = ["celery_app"]
