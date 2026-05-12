"""Abstract base classes for the pipeline framework."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SimContext:
    """Carries all shared state through a single simulation iteration.

    Grows as stages run — each stage reads from ``data`` and writes new keys.
    """
    scenario: str
    start_month: int
    time: int
    sim_index: int
    matching: str
    technologies: list[str]
    L: int
    policy: bool
    is_cbam: bool
    data: dict[str, Any] = field(default_factory=dict)


class Stage(ABC):
    """One logical step in the calculation pipeline."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    @property
    @abstractmethod
    def stage_id(self) -> str:
        """Unique identifier matching the ``id`` field in the YAML config."""

    @abstractmethod
    def run(self, ctx: SimContext) -> dict[str, Any]:
        """Execute this stage.

        Returns a dict whose keys will be merged into ``ctx.data``.
        """


class Pipeline:
    """Ordered sequence of stages that runs against a SimContext."""

    def __init__(self, stages: list[Stage]):
        self.stages = stages

    def run(self, ctx: SimContext) -> SimContext:
        for stage in self.stages:
            outputs = stage.run(ctx)
            ctx.data.update(outputs)
        return ctx
