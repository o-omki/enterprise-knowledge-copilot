from pathlib import Path

import yaml
from pydantic import BaseModel

from packages.llm_serving.slo import SLOConfig


class ModelProfile(BaseModel):
    name: str
    capabilities: list[str]
    cost_per_1k_input: float
    cost_per_1k_output: float
    latency_tier: str


class ModelRouter:
    def __init__(self, config_path: str = "configs/models.yaml"):
        self.models = self._load_config(config_path)

    def _load_config(self, config_path: str) -> dict[str, ModelProfile]:
        path = Path(config_path)
        if not path.exists():
            return {
                "gemini-3.1-flash-lite": ModelProfile(
                    name="gemini-3.1-flash-lite",
                    capabilities=["routing", "fast_search"],
                    cost_per_1k_input=0.00025,
                    cost_per_1k_output=0.0015,
                    latency_tier="ultra-fast",
                ),
                "gemini-3.5-flash": ModelProfile(
                    name="gemini-3.5-flash",
                    capabilities=["direct_lookup", "decomposition"],
                    cost_per_1k_input=0.0015,
                    cost_per_1k_output=0.009,
                    latency_tier="fast",
                ),
                "gemini-3.1-pro-preview": ModelProfile(
                    name="gemini-3.1-pro-preview",
                    capabilities=[
                        "multi_hop_synthesis",
                        "comparative_query",
                        "complex_reasoning",
                        "ambiguous_query",
                    ],
                    cost_per_1k_input=0.002,
                    cost_per_1k_output=0.012,
                    latency_tier="standard",
                ),
            }

        with open(path) as f:
            data = yaml.safe_load(f)

        models = {}
        for name, info in data.get("models", {}).items():
            models[name] = ModelProfile(name=name, **info)
        return models

    def select_model(self, query_type_str: str, slo: SLOConfig | None = None) -> ModelProfile:
        slo = slo or SLOConfig()
        eligible_models = [m for m in self.models.values() if query_type_str in m.capabilities]

        if not eligible_models:
            eligible_models = list(self.models.values())

        if slo.priority == "cost":
            eligible_models.sort(key=lambda m: m.cost_per_1k_input)
        elif slo.priority == "latency":
            eligible_models.sort(key=lambda m: (m.latency_tier != "fast", m.cost_per_1k_input))
        else:  # QUALITY
            eligible_models.sort(key=lambda m: (m.latency_tier != "standard", -m.cost_per_1k_input))

        return eligible_models[0]
