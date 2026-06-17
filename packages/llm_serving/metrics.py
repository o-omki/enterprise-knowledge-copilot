from opentelemetry import metrics

meter = metrics.get_meter("packages.llm_serving")

request_counter = meter.create_counter(
    name="llm.requests.total",
    description="Total number of LLM requests",
    unit="{requests}",
)

error_counter = meter.create_counter(
    name="llm.requests.errors",
    description="Total number of LLM request errors",
    unit="{errors}",
)

latency_histogram = meter.create_histogram(
    name="llm.request.duration",
    description="Duration of LLM requests",
    unit="s",
)

token_counter = meter.create_counter(
    name="llm.tokens.total",
    description="Total number of tokens used",
    unit="{tokens}",
)
