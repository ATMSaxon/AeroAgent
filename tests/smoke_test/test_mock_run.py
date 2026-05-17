"""
Unit tests for smoke_test/mock_run.py — full pipeline integration.

All tests use MockLLM only. No real API calls.
AEROSAFETY_EVAL_MODE=1 is required (set via monkeypatch).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aerosafety.smoke_test.mock_run import load_task_cards, run_mock_pipeline


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _set_eval_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    """All tests in this module require eval mode."""
    monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")


@pytest.fixture()
def smoke_output_dir(tmp_path: Path) -> Path:
    return tmp_path / "smoke_outputs"


# ---------------------------------------------------------------------------
# TaskCard loader tests
# ---------------------------------------------------------------------------

class TestLoadTaskCards:
    def test_loads_all_cards(self) -> None:
        cards = load_task_cards()
        # 152 total per task specification
        assert len(cards) >= 100

    def test_limit_respected(self) -> None:
        cards = load_task_cards(limit=5)
        assert len(cards) == 5

    def test_notam_family_only(self) -> None:
        cards = load_task_cards(families=["notam"])
        assert all(c.family == "notam_compliance" for c in cards)

    def test_weather_family_only(self) -> None:
        cards = load_task_cards(families=["weather"])
        assert all(c.family == "weather_dispatch" for c in cards)

    def test_all_cards_have_required_fields(self) -> None:
        cards = load_task_cards(limit=10)
        for c in cards:
            assert c.task_id
            assert c.prompt
            assert c.gold_decision
            assert c.severity in ("Low", "Medium", "High", "Critical")

    def test_invalid_family_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown family"):
            load_task_cards(families=["bogus"])

    def test_all_provenance_sources_are_synthetic(self) -> None:
        cards = load_task_cards(limit=20)
        for c in cards:
            # All pilot cards should be SYNTHETIC (no real data yet)
            assert c.provenance.source == "SYNTHETIC", (
                f"Task {c.task_id} has non-SYNTHETIC provenance: {c.provenance.source!r}. "
                "Real data must be explicitly labeled."
            )


# ---------------------------------------------------------------------------
# mock_run pipeline tests
# ---------------------------------------------------------------------------

class TestRunMockPipeline:
    def test_returns_system_results(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1], limit=3, output_dir=smoke_output_dir)
        assert "system_results" in result
        assert "system1" in result["system_results"]

    def test_all_systems_run(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1, 2, 3, 4], limit=3, output_dir=smoke_output_dir)
        assert set(result["system_results"].keys()) == {"system1", "system2", "system3", "system4"}

    def test_system7_runs(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[7], limit=2, output_dir=smoke_output_dir)
        assert "system7" in result["system_results"]

    def test_pipeline_valid(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1, 2], limit=3, output_dir=smoke_output_dir)
        assert result["all_valid"] is True, f"Errors: {result['errors']}"

    def test_jsonl_output_written(self, smoke_output_dir: Path) -> None:
        run_mock_pipeline(systems=[1], limit=3, output_dir=smoke_output_dir)
        jsonl_files = list(smoke_output_dir.rglob("*.jsonl"))
        assert len(jsonl_files) >= 1

    def test_summary_markdown_written(self, smoke_output_dir: Path) -> None:
        run_mock_pipeline(systems=[1], limit=3, output_dir=smoke_output_dir)
        md_files = list(smoke_output_dir.rglob("*.md"))
        assert len(md_files) >= 1

    def test_traces_have_task_ids(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1], limit=3, output_dir=smoke_output_dir)
        traces = result["system_results"]["system1"]["traces"]
        assert len(traces) == 3
        assert all(hasattr(t, "task_id") and t.task_id for t in traces)

    def test_aggregate_has_tsr(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1], limit=3, output_dir=smoke_output_dir)
        agg = result["system_results"]["system1"]["aggregate"]
        assert "tsr" in agg
        assert isinstance(agg["tsr"], float)

    def test_aggregate_has_svr(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1], limit=3, output_dir=smoke_output_dir)
        agg = result["system_results"]["system1"]["aggregate"]
        assert "svr" in agg
        assert 0.0 <= agg["svr"] <= 1.0

    def test_n_total_matches_limit(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1], limit=4, output_dir=smoke_output_dir)
        agg = result["system_results"]["system1"]["aggregate"]
        assert agg["n_total"] == 4

    def test_tsr_ci_present(self, smoke_output_dir: Path) -> None:
        result = run_mock_pipeline(systems=[1], limit=5, output_dir=smoke_output_dir, n_bootstrap=10)
        agg = result["system_results"]["system1"]["aggregate"]
        assert "tsr_ci" in agg
        ci = agg["tsr_ci"]
        assert "ci_lower" in ci
        assert "ci_upper" in ci

    def test_notam_family_only(self, smoke_output_dir: Path) -> None:
        cards = load_task_cards(families=["notam"], limit=5)
        result = run_mock_pipeline(
            systems=[1], families=["notam"], limit=5, output_dir=smoke_output_dir
        )
        traces = result["system_results"]["system1"]["traces"]
        assert len(traces) == len(cards)

    def test_requires_eval_mode(self, monkeypatch: pytest.MonkeyPatch, smoke_output_dir: Path) -> None:
        monkeypatch.delenv("AEROSAFETY_EVAL_MODE")
        with pytest.raises(RuntimeError, match="AEROSAFETY_EVAL_MODE"):
            run_mock_pipeline(systems=[1], limit=2, output_dir=smoke_output_dir)
