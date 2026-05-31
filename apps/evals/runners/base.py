"""Base types and abstract runner for the evaluation harness.

Every concrete runner (retrieval, generation, safety, …) inherits from
:class:`BaseRunner` and returns an :class:`EvalResult` so that the report
and regression modules can consume results uniformly.
"""

from __future__ import annotations

import json
import logging
import subprocess
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from apps.evals.config import EvalConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Uniform output contract for every evaluation runner."""

    runner_name: str
    timestamp: str
    dataset_path: str
    config_snapshot: dict[str, Any]
    metrics: dict[str, float]
    per_query: list[dict[str, Any]]
    timings: dict[str, float]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def save_json(self, path: Path) -> None:
        """Persist the result as a pretty-printed JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as fh:
            json.dump(self.to_dict(), fh, indent=2, default=str)
        logger.info("EvalResult written to %s", path)


# ---------------------------------------------------------------------------
# Abstract base runner
# ---------------------------------------------------------------------------


class BaseRunner(ABC):
    """Abstract base class for all evaluation runners.

    Subclasses implement :meth:`run` and return an :class:`EvalResult`.
    The base class provides convenience helpers for dataset loading and
    environment metadata capture.
    """

    name: str = "base"

    def __init__(self, config: EvalConfig) -> None:
        self.config = config

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def load_dataset(path: str | Path) -> list[dict[str, Any]]:
        """Load a JSON evaluation dataset from disk."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Dataset not found: {p}")
        with open(p) as fh:
            data = json.load(fh)
        logger.info("Loaded %d items from %s", len(data), p)
        return data

    @staticmethod
    def capture_metadata() -> dict[str, Any]:
        """Capture runtime metadata for reproducibility."""
        meta: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
        }
        # Git SHA
        try:
            sha = (
                subprocess.check_output(
                    ["git", "rev-parse", "--short", "HEAD"],
                    stderr=subprocess.DEVNULL,
                )
                .decode()
                .strip()
            )
            meta["git_sha"] = sha
        except Exception:
            meta["git_sha"] = "unknown"

        import platform
        import sys

        meta["python_version"] = sys.version
        meta["platform"] = platform.platform()
        return meta

    @staticmethod
    def now_iso() -> str:
        return datetime.now(UTC).isoformat()

    # -- abstract interface --------------------------------------------------

    @abstractmethod
    async def run(self) -> EvalResult:
        """Execute the evaluation and return structured results."""
        ...
