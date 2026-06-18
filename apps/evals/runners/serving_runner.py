"""Evaluation runner for systems-level serving components.

Evaluates:
1. ModelRouter capability mapping and SLO priority enforcement.
2. ResponseCache hit/miss correctness and hit rate calculation.
3. CircuitBreaker state transitions (trip, block, and recovery).
"""

from __future__ import annotations

import asyncio
import logging
import time

from apps.evals.runners.base import BaseRunner, EvalResult
from packages.llm_serving.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from packages.llm_serving.config import LLMServingConfig
from packages.llm_serving.response_cache import ResponseCache
from packages.llm_serving.router import ModelRouter
from packages.llm_serving.slo import SLOConfig, SLOPriority
from packages.llm_serving.types import LLMMessage, LLMRequest, LLMResponse, UsageMetadata

logger = logging.getLogger(__name__)


class MockRedis:
    """Mock Redis client for ResponseCache testing."""

    def __init__(self) -> None:
        self.store: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value


class ServingRunner(BaseRunner):
    """Benchmarks systems-level serving components."""

    name = "serving"

    async def run(self) -> EvalResult:
        dataset = self.load_dataset(self.config.datasets.serving)

        overall_start = time.perf_counter()

        # 1. Evaluate ModelRouter Accuracy
        router_success = 0
        router_total = len(dataset)
        router_cases = []

        router = ModelRouter()

        for item in dataset:
            scenario = item.get("scenario", "")
            capability = item["capability"]
            priority_str = item["slo_priority"]
            expected = item["expected_model"]

            priority = SLOPriority(priority_str)
            slo = SLOConfig(priority=priority)

            selected_profile = router.select_model(capability, slo)
            matched = selected_profile.name == expected

            if matched:
                router_success += 1

            router_cases.append(
                {
                    "scenario": scenario,
                    "capability": capability,
                    "priority": priority_str,
                    "expected": expected,
                    "actual": selected_profile.name,
                    "status": "pass" if matched else "fail",
                }
            )

        router_accuracy = (router_success / router_total * 100.0) if router_total > 0 else 100.0

        # 2. Evaluate ResponseCache Hit Rate Correctness
        cache_config = LLMServingConfig(cache_enabled=True, cache_ttl_sec=60)
        mock_redis = MockRedis()
        cache = ResponseCache(config=cache_config, redis_client=mock_redis)

        dummy_response = LLMResponse(
            text="Cached Answer",
            usage=UsageMetadata(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )

        cache_total_lookups = 10
        cache_hits = 0
        cache_misses = 0

        # Run 10 cache trials (2 misses, 8 hits)
        for i in range(1, 11):
            req = LLMRequest(
                messages=[LLMMessage(role="user", content=f"Cache Test Query {i}")],
                model="gemini-3.5-flash",
                temperature=0.2,
                max_tokens=100,
            )

            if i <= 2:
                # Misses: Look up keys that were never set
                res = await cache.get(req)
                if res is None:
                    cache_misses += 1
            else:
                # Hits: Set key first, then look it up
                await cache.set(req, dummy_response)
                res = await cache.get(req)
                if res and res.text == dummy_response.text:
                    cache_hits += 1

        cache_hit_rate = cache_hits / cache_total_lookups * 100.0
        cache_passed = (cache_misses == 2) and (cache_hits == 8)

        # 3. Evaluate CircuitBreaker state transitions
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=0.05)
        cb_success_transitions = 0
        cb_total_checks = 4

        call_count = 0

        async def mock_fail():
            nonlocal call_count
            call_count += 1
            raise RuntimeError("Backend Timeout")

        async def mock_succeed():
            return "Success"

        # Call failing function 3 times to trip circuit breaker
        for _ in range(3):
            try:
                await cb.execute(mock_fail)
            except RuntimeError:
                pass

        # Transition 1: CB state must be OPEN
        if cb.state == "OPEN":
            cb_success_transitions += 1

        # Transition 2: Call must be blocked without calling the mock function
        try:
            await cb.execute(mock_fail)
        except CircuitBreakerOpenException:
            if call_count == 3:  # mock_fail was NOT invoked a 4th time
                cb_success_transitions += 1

        # Sleep to exceed recovery timeout
        await asyncio.sleep(0.06)

        # Transition 3: State check must transition to HALF_OPEN
        cb.check_state()
        if cb.state == "HALF_OPEN":
            cb_success_transitions += 1

        # Transition 4: Call success mock function to reset state to CLOSED
        try:
            res = await cb.execute(mock_succeed)
            if res == "Success" and cb.state == "CLOSED" and cb.failures == 0:
                cb_success_transitions += 1
        except Exception:
            pass

        cb_trip_rate = cb_success_transitions / cb_total_checks * 100.0

        overall_elapsed_s = time.perf_counter() - overall_start

        metrics = {
            "router_accuracy": round(router_accuracy, 1),
            "cache_hit_rate": round(cache_hit_rate, 1),
            "circuit_breaker_trip_rate": round(cb_trip_rate, 1),
        }

        per_query = [
            {"test_suite": "ModelRouter", "details": router_cases},
            {
                "test_suite": "ResponseCache",
                "details": (
                    f"Total Lookups: {cache_total_lookups}, "
                    f"Hits: {cache_hits}, Misses: {cache_misses}, "
                    f"Passed: {cache_passed}",
                ),
            },
            {
                "test_suite": "CircuitBreaker",
                "details": (
                    f"Total Checks: {cb_total_checks}, Passed Checks: {cb_success_transitions}",
                ),
            },
        ]

        return EvalResult(
            runner_name=self.name,
            timestamp=self.now_iso(),
            dataset_path=self.config.datasets.serving,
            config_snapshot={
                "models_config_path": "configs/models.yaml",
                "cache_enabled": True,
                "circuit_breaker_threshold": 3,
            },
            metrics=metrics,
            per_query=per_query,
            timings={
                "total_elapsed_s": round(overall_elapsed_s, 4),
            },
            metadata=self.capture_metadata(),
        )
