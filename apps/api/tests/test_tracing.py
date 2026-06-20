from unittest.mock import MagicMock

import opentelemetry.metrics as otel_metrics
import opentelemetry.sdk.trace as sdk_trace
import opentelemetry.trace as otel_trace
from fastapi import FastAPI
from opentelemetry.sdk.trace.sampling import ALWAYS_OFF, ParentBased, TraceIdRatioBased

from packages.observability import get_meter, get_tracer, setup_tracing


def test_setup_tracing_basic(monkeypatch):
    monkeypatch.setenv("DEPLOYMENT_ENVIRONMENT", "test-env")
    app = FastAPI(version="1.2.3")

    mock_set_trace_provider = MagicMock()
    mock_set_meter_provider = MagicMock()
    monkeypatch.setattr(otel_trace, "set_tracer_provider", mock_set_trace_provider)
    monkeypatch.setattr(otel_metrics, "set_meter_provider", mock_set_meter_provider)

    setup_tracing(app, service_name="test-service")

    # Verify providers are set
    assert mock_set_trace_provider.called
    assert mock_set_meter_provider.called

    provider = mock_set_trace_provider.call_args[0][0]
    assert isinstance(provider, sdk_trace.TracerProvider)

    # Verify resource attributes are set correctly
    resource = provider.resource
    assert resource.attributes["service.name"] == "test-service"
    assert resource.attributes["service.version"] == "1.2.3"
    assert resource.attributes["deployment.environment"] == "test-env"

    # Verify tracer and meter retrieval work
    tracer = get_tracer("test_tracer")
    assert tracer is not None
    meter = get_meter("test_meter")
    assert meter is not None


def test_setup_tracing_sampler_config(monkeypatch):
    mock_set_trace_provider = MagicMock()
    monkeypatch.setattr(otel_trace, "set_tracer_provider", mock_set_trace_provider)

    # Test traceidratio sampler configuration
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "traceidratio")
    monkeypatch.setenv("OTEL_TRACES_SAMPLER_ARG", "0.25")

    setup_tracing(None, service_name="test-sampler-ratio")

    provider = mock_set_trace_provider.call_args[0][0]
    sampler = provider.sampler
    assert isinstance(sampler, TraceIdRatioBased)
    assert sampler.rate == 0.25

    # Test parentbased_always_off sampler configuration
    monkeypatch.setenv("OTEL_TRACES_SAMPLER", "parentbased_always_off")
    mock_set_trace_provider.reset_mock()

    setup_tracing(None, service_name="test-sampler-parent")

    provider = mock_set_trace_provider.call_args[0][0]
    sampler = provider.sampler
    assert isinstance(sampler, ParentBased)
    assert isinstance(sampler._root, type(ALWAYS_OFF))
