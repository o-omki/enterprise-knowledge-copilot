import structlog
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags

from packages.observability.logging import add_otel_trace_span_ids, configure_logging


def test_configure_logging():
    # Calling configure_logging should run without errors
    configure_logging("test_service", "DEBUG")

    # Verify structlog logger is active
    logger = structlog.get_logger("test_logger")
    assert logger is not None


def test_otel_trace_span_ids_injection():
    # Mock OpenTelemetry span context
    trace_id = 0x1234567890ABCDEF1234567890ABCDEF
    span_id = 0x1234567890ABCDEF
    span_context = SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )

    span = NonRecordingSpan(span_context)

    # Use context manager to set the active span
    with trace.use_span(span):
        # Check trace ID / span ID addition in processor
        event_dict = add_otel_trace_span_ids(None, None, {})
        assert event_dict["trace_id"] == "1234567890abcdef1234567890abcdef"
        assert event_dict["span_id"] == "1234567890abcdef"
