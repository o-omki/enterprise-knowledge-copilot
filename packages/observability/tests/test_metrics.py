from opentelemetry.metrics import Observation

import packages.observability.metrics as _metrics_module
from packages.observability.metrics import (
    active_requests,
    observe_circuit_breaker_state,
    observe_uptime,
    register_circuit_breaker,
    request_total,
    retrieval_total,
)


class MockCircuitBreaker:
    def __init__(self, state="CLOSED"):
        self.state = state


def test_metrics_registration():
    assert request_total is not None
    assert active_requests is not None
    assert retrieval_total is not None


def test_uptime_observation():
    obs = list(observe_uptime(None))
    assert len(obs) == 1
    assert isinstance(obs[0], Observation)
    assert obs[0].value >= 0.0


def test_circuit_breaker_observation():
    # Save and restore the original contents so this test
    # is fully isolated from import order.
    original = dict(_metrics_module._circuit_breakers)
    try:
        _metrics_module._circuit_breakers.clear()

        obs = list(observe_circuit_breaker_state(None))
        assert len(obs) == 1
        assert obs[0].value == 0
        assert obs[0].attributes["circuit_breaker_name"] == "default"

        # Register mock breaker and test state mappings
        cb = MockCircuitBreaker("OPEN")
        register_circuit_breaker("test_cb", cb)

        obs = list(observe_circuit_breaker_state(None))
        # Filter observations to find test_cb
        test_obs = [o for o in obs if o.attributes.get("circuit_breaker_name") == "test_cb"]
        assert len(test_obs) == 1
        assert test_obs[0].value == 2  # OPEN mapped to 2
    finally:
        _metrics_module._circuit_breakers.clear()
        _metrics_module._circuit_breakers.update(original)
