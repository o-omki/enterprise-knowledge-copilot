import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor


def _get_sampler():
    sampler_name = os.getenv("OTEL_TRACES_SAMPLER", "always_on").lower()
    ratio_str = os.getenv("OTEL_TRACES_SAMPLER_ARG", "0.1")
    try:
        ratio = float(ratio_str)
    except ValueError:
        ratio = 0.1

    from opentelemetry.sdk.trace.sampling import (
        ALWAYS_OFF,
        ALWAYS_ON,
        ParentBased,
        TraceIdRatioBased,
    )

    if sampler_name == "always_on":
        return ALWAYS_ON
    elif sampler_name == "always_off":
        return ALWAYS_OFF
    elif sampler_name == "traceidratio":
        return TraceIdRatioBased(ratio)
    elif sampler_name == "parentbased_always_on":
        return ParentBased(ALWAYS_ON)
    elif sampler_name == "parentbased_always_off":
        return ParentBased(ALWAYS_OFF)
    elif sampler_name == "parentbased_traceidratio":
        return ParentBased(TraceIdRatioBased(ratio))
    else:
        return ALWAYS_ON


def setup_tracing(app=None, service_name="enterprise-knowledge-copilot"):
    version = getattr(app, "version", "0.1.0") if app else "0.1.0"
    env = os.getenv("DEPLOYMENT_ENVIRONMENT", "development")

    resource = Resource(
        attributes={
            "service.name": service_name,
            "service.version": version,
            "deployment.environment": env,
        }
    )

    sampler = _get_sampler()
    provider = TracerProvider(resource=resource, sampler=sampler)
    trace.set_tracer_provider(provider)

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317")
    insecure = os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true").lower() == "true"

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=insecure)

    processor = BatchSpanProcessor(exporter)
    provider.add_span_processor(processor)

    # Setup shared MeterProvider using the same Resource configuration with Prometheus reader
    prometheus_reader = PrometheusMetricReader()
    meter_provider = MeterProvider(resource=resource, metric_readers=[prometheus_reader])
    metrics.set_meter_provider(meter_provider)

    if app:
        FastAPIInstrumentor.instrument_app(app)


def get_tracer(name: str):
    return trace.get_tracer(name)


def get_meter(name: str):
    return metrics.get_meter(name)
