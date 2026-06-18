import pytest

from apps.evals.config import load_eval_config
from apps.evals.runners.serving_runner import ServingRunner


@pytest.mark.asyncio
async def test_serving_runner() -> None:
    config = load_eval_config()
    runner = ServingRunner(config)
    result = await runner.run()

    assert result.runner_name == "serving"
    assert "router_accuracy" in result.metrics
    assert "cache_hit_rate" in result.metrics
    assert "circuit_breaker_trip_rate" in result.metrics
    assert result.metrics["router_accuracy"] == 100.0
    assert result.metrics["cache_hit_rate"] == 80.0
    assert result.metrics["circuit_breaker_trip_rate"] == 100.0
