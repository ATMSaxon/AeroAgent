"""
Unit tests for reporting utilities — aerosafety/eval/reporting.py

Validates:
1. write_jsonl_log: each line is valid JSON, failures are preserved
2. write_summary_markdown: file contains table headers, metric rows
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from aerosafety.eval.reporting import write_jsonl_log, write_summary_markdown


class TestWriteJSONLLog:
    def test_writes_all_records(self, tmp_path: Path):
        records = [
            {"task_id": "t1", "correct": True, "unsafe": False},
            {"task_id": "t2", "correct": False, "unsafe": True},  # failure preserved
        ]
        path = write_jsonl_log(records, tmp_path / "out.jsonl")
        lines = path.read_text().strip().splitlines()
        assert len(lines) == 2

    def test_each_line_valid_json(self, tmp_path: Path):
        records = [{"task_id": "t1", "value": 0.5}, {"task_id": "t2", "value": 1.0}]
        path = write_jsonl_log(records, tmp_path / "out.jsonl")
        for line in path.read_text().strip().splitlines():
            parsed = json.loads(line)
            assert "task_id" in parsed

    def test_failures_preserved(self, tmp_path: Path):
        records = [
            {"task_id": "safe", "correct": True},
            {"task_id": "unsafe_fail", "correct": False, "unsafe": True, "severity": "Critical"},
        ]
        path = write_jsonl_log(records, tmp_path / "out.jsonl")
        lines = [json.loads(l) for l in path.read_text().strip().splitlines()]
        task_ids = {r["task_id"] for r in lines}
        assert "unsafe_fail" in task_ids

    def test_creates_parent_dir(self, tmp_path: Path):
        nested = tmp_path / "deep" / "nested" / "out.jsonl"
        write_jsonl_log([{"x": 1}], nested)
        assert nested.exists()

    def test_nan_serialised_as_string(self, tmp_path: Path):
        records = [{"task_id": "t1", "value": float("nan")}]
        path = write_jsonl_log(records, tmp_path / "out.jsonl")
        content = path.read_text()
        assert "NaN" in content

    def test_returns_path(self, tmp_path: Path):
        result = write_jsonl_log([], tmp_path / "empty.jsonl")
        assert isinstance(result, Path)
        assert result.exists()


class TestWriteSummaryMarkdown:
    def test_creates_file(self, tmp_path: Path):
        path = write_summary_markdown({"tsr": 0.75}, tmp_path / "summary.md")
        assert path.exists()

    def test_contains_metric_name(self, tmp_path: Path):
        path = write_summary_markdown({"tsr": 0.75, "svr": 0.1}, tmp_path / "summary.md")
        content = path.read_text()
        assert "tsr" in content
        assert "svr" in content

    def test_contains_table_headers(self, tmp_path: Path):
        path = write_summary_markdown({"tsr": 0.75}, tmp_path / "summary.md")
        content = path.read_text()
        assert "Metric" in content
        assert "Value" in content

    def test_ci_dict_rendered(self, tmp_path: Path):
        metrics = {
            "tsr_ci": {
                "point_estimate": 0.75,
                "ci_lower": 0.65,
                "ci_upper": 0.85,
                "n_samples": 100,
            }
        }
        path = write_summary_markdown(metrics, tmp_path / "summary.md")
        content = path.read_text()
        assert "0.7500" in content
        assert "0.6500" in content

    def test_run_metadata_included(self, tmp_path: Path):
        path = write_summary_markdown(
            {"tsr": 0.8},
            tmp_path / "summary.md",
            run_metadata={"model": "gpt-4o", "seed": 42},
        )
        content = path.read_text()
        assert "gpt-4o" in content
        assert "42" in content

    def test_no_fabricated_numbers(self, tmp_path: Path):
        # Verify no hardcoded percentage values appear unrelated to input
        path = write_summary_markdown({"tsr": 0.123456}, tmp_path / "summary.md")
        content = path.read_text()
        assert "0.1235" in content  # formatted to 4 decimal places
