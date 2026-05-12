"""Tests for the Pipeline / Stage / SimContext framework."""

from typing import Any

import pytest

from ap_ira_lib.pipeline.base import Pipeline, SimContext, Stage


# ── Concrete Stage helpers ────────────────────────────────────────────────────


class DoubleStage(Stage):
    stage_id = "double"

    def run(self, ctx: SimContext) -> dict[str, Any]:
        return {"doubled": ctx.data.get("value", 0) * 2}


class AddStage(Stage):
    stage_id = "add"

    def run(self, ctx: SimContext) -> dict[str, Any]:
        return {"total": ctx.data.get("doubled", 0) + 10}


class TagStage(Stage):
    stage_id = "tag"

    def run(self, ctx: SimContext) -> dict[str, Any]:
        return {"tag": self.config.get("label", "default")}


# ── SimContext ────────────────────────────────────────────────────────────────


@pytest.fixture
def ctx():
    return SimContext(
        scenario="A",
        start_month=0,
        time=2023,
        sim_index=0,
        matching="hourly",
        technologies=["AP SMR", "AP AEC"],
        L=480,
        policy=True,
        is_cbam=False,
        data={"value": 5},
    )


def test_simcontext_fields(ctx):
    assert ctx.scenario == "A"
    assert ctx.start_month == 0
    assert ctx.time == 2023
    assert ctx.L == 480
    assert ctx.policy is True
    assert ctx.is_cbam is False


def test_simcontext_technologies(ctx):
    assert "AP SMR" in ctx.technologies
    assert "AP AEC" in ctx.technologies


def test_simcontext_data_default():
    c = SimContext(
        scenario="B", start_month=84, time=2030, sim_index=1,
        matching="monthly", technologies=[], L=240, policy=False, is_cbam=True,
    )
    assert c.data == {}


# ── Pipeline ──────────────────────────────────────────────────────────────────


def test_pipeline_runs_stages_in_order(ctx):
    pipeline = Pipeline([DoubleStage(), AddStage()])
    result = pipeline.run(ctx)
    assert result.data["doubled"] == 10   # 5 * 2
    assert result.data["total"] == 20     # 10 + 10


def test_pipeline_returns_simcontext(ctx):
    result = Pipeline([DoubleStage()]).run(ctx)
    assert isinstance(result, SimContext)


def test_pipeline_preserves_existing_data(ctx):
    result = Pipeline([DoubleStage()]).run(ctx)
    assert result.data["value"] == 5      # original key untouched
    assert "doubled" in result.data       # stage output added


def test_empty_pipeline_leaves_data_unchanged(ctx):
    result = Pipeline([]).run(ctx)
    assert result.data == {"value": 5}


def test_pipeline_later_stage_sees_earlier_output(ctx):
    # AddStage reads 'doubled', which DoubleStage writes — order matters
    result = Pipeline([DoubleStage(), AddStage()]).run(ctx)
    assert result.data["total"] == 20

    # If reversed, AddStage runs first and sees doubled=0 (not yet set)
    ctx2 = SimContext(
        scenario="A", start_month=0, time=2023, sim_index=0,
        matching="hourly", technologies=[], L=480, policy=True, is_cbam=False,
        data={"value": 5},
    )
    result2 = Pipeline([AddStage(), DoubleStage()]).run(ctx2)
    assert result2.data["total"] == 10    # doubled was 0 when AddStage ran


# ── Stage ─────────────────────────────────────────────────────────────────────


def test_stage_default_config():
    assert DoubleStage().config == {}


def test_stage_stores_config():
    stage = TagStage(config={"label": "hello"})
    assert stage.config["label"] == "hello"


def test_stage_config_used_in_run(ctx):
    stage = TagStage(config={"label": "scenario_A"})
    result = Pipeline([stage]).run(ctx)
    assert result.data["tag"] == "scenario_A"
