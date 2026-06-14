"""Celery application factory.

Broker and result backend both use Redis (separate DB indices).

Usage::

    celery -A apps.worker.celery_app worker --loglevel=info
"""

import os

from celery import Celery

_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")

app = Celery(
    "enterprise_knowledge_copilot",
    broker=_BROKER_URL,
    backend=_RESULT_BACKEND,
    include=["apps.worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)
