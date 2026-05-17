"""
Unit tests for smoke_test/report.py — comparison report generation.

No LLM calls. Tests use synthetic metric dicts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from aerosafety.smoke_test.report import generate_comparison_report


def _fake_results(tsr: float = 0.6, svr: float = 0.3) -> dict:
    """Build a minimal fake EvalRunner result dict for testing."""
    return {
        "aggregate": {
            "tsr": tsr,
            "tsr_ci": {"point_estimate": tsr, "ci_lower": tsr - 0.1, "ci_upper": tsr + 0.1, "n_samples": 5},
            "svr": svr,
            "svr_ci": {"point_estimate": svr, "ci_lower": svr - 0.05, "ci_upper": svr + 0.05, "n_samples": 5},
            "scor": 0.2,
            "evidence_faithfulness": {"citation_rate": 0.8, "unsupported_claim_rate": 0.1,
                                       "hallucinated_evidence_rate": 0.0, "contradiction_rate": 0.05},
            "tool_use_reliability": {"required_tool_call_rate": 0.7, "correct_selection_rate": 0.9,
                                      "correct_input_rate": 0.85, "correct_interpretation_rate": 0.8,
                                      "misuse_rate": 0.1},
            "swfr": 0.4,
            "swfr_ci": {"point_estimate": 0.4, "ci_lower": 0.3, "ci_upper": 0.5, "n_samples": 5},
            "cass": 0.55,
            "n_total": 5,
        }
    }


class TestGenerateComparisonReport:
    def test_creates_file(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        result = generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
        )
        assert result == path
        assert path.exists()

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "nested" / "dir" / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
        )
        assert path.exists()

    def test_mock_disclaimer_present(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
            mock=True,
        )
        content = path.read_text()
        assert "MOCK RUN" in content
        assert "no research value" in content.lower() or "mock" in content.lower()

    def test_no_mock_disclaimer_when_not_mock(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
            mock=False,
        )
        content = path.read_text()
        assert "WARNING — MOCK RUN" not in content

    def test_system_name_in_output(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results(), "system4": _fake_results(tsr=0.7)},
            output_path=path,
            mock=True,
        )
        content = path.read_text()
        assert "system1" in content
        assert "system4" in content

    def test_metrics_header_present(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
        )
        content = path.read_text()
        assert "TSR" in content
        assert "SVR" in content
        assert "SCOR" in content
        assert "SWFR" in content
        assert "CASS" in content

    def test_run_label_in_title(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
            run_label="Test Pilot Run",
        )
        content = path.read_text()
        assert "Test Pilot Run" in content

    def test_run_metadata_in_output(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
            run_metadata={"model": "mock/test", "seed": 42},
        )
        content = path.read_text()
        assert "mock/test" in content

    def test_multi_system_all_rows_present(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={
                "system1": _fake_results(tsr=0.5),
                "system2": _fake_results(tsr=0.6),
                "system3": _fake_results(tsr=0.7),
                "system4": _fake_results(tsr=0.8),
            },
            output_path=path,
            mock=True,
        )
        content = path.read_text()
        for s in ["system1", "system2", "system3", "system4"]:
            assert s in content

    def test_empty_system_results_produces_file(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(system_results={}, output_path=path)
        assert path.exists()

    def test_ci_notation_in_output(self, tmp_path: Path) -> None:
        path = tmp_path / "report.md"
        generate_comparison_report(
            system_results={"system1": _fake_results()},
            output_path=path,
        )
        content = path.read_text()
        # CI lower/upper values should appear
        assert "[" in content
