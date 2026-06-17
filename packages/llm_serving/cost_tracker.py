from opentelemetry import metrics

from packages.llm_serving.router import ModelRouter
from packages.llm_serving.types import UsageMetadata

meter = metrics.get_meter("packages.llm_serving.cost")
cost_counter = meter.create_counter(
    name="llm.cost.total_usd",
    description="Total estimated cost of LLM queries in USD",
    unit="USD",
)


class CostTracker:
    def __init__(self, router: ModelRouter):
        self.router = router

    def calculate_cost(self, model_name: str, usage: UsageMetadata) -> float:
        model = self.router.models.get(model_name)
        if not model:
            return 0.0

        input_cost = (usage.prompt_tokens / 1000.0) * model.cost_per_1k_input
        output_cost = (usage.completion_tokens / 1000.0) * model.cost_per_1k_output
        total_cost = input_cost + output_cost

        cost_counter.add(total_cost, {"model": model_name})
        return total_cost
