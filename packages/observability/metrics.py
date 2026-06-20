import time

from opentelemetry import metrics
from opentelemetry.metrics import Observation

meter = metrics.get_meter("enterprise-knowledge-copilot")

request_total = meter.create_counter(
    name="http.server.request.total",
    description="Total number of HTTP requests",
    unit="{requests}",
)

active_requests = meter.create_up_down_counter(
    name="http.server.active_requests",
    description="Number of concurrent active HTTP requests",
    unit="{requests}",
)

retrieval_duration = meter.create_histogram(
    name="retrieval.request.duration",
    description="Duration of retrieval requests",
    unit="s",
)

retrieval_total = meter.create_counter(
    name="retrieval.request.total",
    description="Total number of retrieval requests",
    unit="{requests}",
)

retrieval_result_count = meter.create_histogram(
    name="retrieval.result.count",
    description="Distribution of retrieval result set sizes",
    unit="{results}",
)

retrieval_hit_quality = meter.create_histogram(
    name="retrieval.hit.quality",
    description="Top-1 score distribution",
    unit="1",
)

reranking_duration = meter.create_histogram(
    name="reranking.request.duration",
    description="Duration of reranking requests",
    unit="s",
)

reranking_total = meter.create_counter(
    name="reranking.request.total",
    description="Total number of reranking requests",
    unit="{requests}",
)

reranking_candidate_count = meter.create_histogram(
    name="reranking.candidate.count",
    description="Distribution of reranking candidate counts",
    unit="{candidates}",
)

generation_duration = meter.create_histogram(
    name="generation.request.duration",
    description="Duration of generation requests",
    unit="s",
)

generation_total = meter.create_counter(
    name="generation.request.total",
    description="Total number of generation requests",
    unit="{requests}",
)

generation_token_count = meter.create_histogram(
    name="generation.token.count",
    description="Prompt + completion tokens distribution",
    unit="{tokens}",
)

safety_duration = meter.create_histogram(
    name="safety.check.duration",
    description="Duration of safety checks",
    unit="s",
)

safety_check_total = meter.create_counter(
    name="safety.check.total",
    description="Total number of safety checks",
    unit="{checks}",
)

safety_block_total = meter.create_counter(
    name="safety.block.total",
    description="Total number of safety blocks/refusals",
    unit="{blocks}",
)

ingestion_duration = meter.create_histogram(
    name="ingestion.task.duration",
    description="Duration of ingestion tasks",
    unit="s",
)

ingestion_total = meter.create_counter(
    name="ingestion.task.total",
    description="Total number of ingestion tasks",
    unit="{tasks}",
)

ingestion_chunk_count = meter.create_counter(
    name="ingestion.chunk.count",
    description="Total number of chunks indexed",
    unit="{chunks}",
)

cache_hit_counter = meter.create_counter(
    name="llm.cache.hit.total",
    description="LLM response cache hit/miss count",
    unit="{requests}",
)

START_TIME = time.time()


def observe_uptime(options) -> list[Observation]:
    uptime = time.time() - START_TIME
    return [Observation(uptime, {})]


meter.create_observable_gauge(
    name="system.uptime_seconds",
    callbacks=[observe_uptime],
    description="Process uptime in seconds",
    unit="s",
)

_circuit_breakers = {}


def register_circuit_breaker(name: str, cb_instance):
    """Allows LLMClient or other modules to register dynamic circuit breaker instances."""
    _circuit_breakers[name] = cb_instance


def observe_circuit_breaker_state(options) -> list[Observation]:
    observations = []
    state_map = {"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}
    for name, cb in list(_circuit_breakers.items()):
        val = state_map.get(cb.state, 0)
        observations.append(Observation(val, {"circuit_breaker_name": name}))
    # If no circuit breakers are registered yet, return a default observation to keep OTel happy
    if not observations:
        observations.append(Observation(0, {"circuit_breaker_name": "default"}))
    return observations


meter.create_observable_gauge(
    name="llm.circuit_breaker.state",
    callbacks=[observe_circuit_breaker_state],
    description="LLM circuit breaker state: 0=closed, 1=half_open, 2=open",
    unit="1",
)
