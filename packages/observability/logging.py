import logging
import os
import sys

import structlog
from opentelemetry import trace


def add_otel_trace_span_ids(logger, log_method, event_dict):
    """Processor to inject OpenTelemetry trace and span ID if active."""
    span = trace.get_current_span()
    if span and span.get_span_context().is_valid:
        event_dict["trace_id"] = trace.format_trace_id(span.get_span_context().trace_id)
        event_dict["span_id"] = trace.format_span_id(span.get_span_context().span_id)
    return event_dict


def configure_logging(service_name: str, log_level: str = "INFO"):
    """Configures centralized structured logging for the application.

    Supports console rendering (for local dev) and JSON rendering (for prod/Jaeger correlation).
    """
    level = getattr(logging, log_level.upper(), logging.INFO)

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        add_otel_trace_span_ids,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    log_format = os.getenv("LOG_FORMAT", "json").lower()

    if log_format == "console":
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    # Remove existing handlers to avoid duplicates
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(level)

    # Prevent uvicorn/etc from writing directly via their own formats
    for name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
        logger_obj = logging.getLogger(name)
        logger_obj.handlers = []
        logger_obj.propagate = True

    structlog.contextvars.bind_contextvars(service=service_name)


def bind_request_context(request_id: str, session_id: str, **kwargs):
    """Binds request/session metadata to thread/async-local context."""
    structlog.contextvars.bind_contextvars(request_id=request_id, session_id=session_id, **kwargs)
