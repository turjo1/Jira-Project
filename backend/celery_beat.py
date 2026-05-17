"""Celery Beat scheduler entrypoint."""
import os
import sys

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tasks import celery_app

if __name__ == "__main__":
    celery_app.worker_main([
        "beat",
        "--loglevel=info",
    ])
