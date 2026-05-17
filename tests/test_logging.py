"""Smoke tests for aerosafety.logging."""

import json
from pathlib import Path

import pytest

from aerosafety.io import AgentTrace
from aerosafety.logging import ExperimentLogger, RunIdMismatchError, get_logger


def test_experiment_logger_writes_jsonl(
    minimal_agent_trace: AgentTrace, log_dir: Path
) -> None:
    # Logger run_id must match the fixture's trace run_id ("test-run-001")
    out = log_dir / "test-run-001.jsonl"
    with ExperimentLogger("test-run-001", out) as el:
        el.log_trace(minimal_agent_trace)
        el.log_trace(minimal_agent_trace)
    assert el.traces_written == 2

    lines = out.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["task_id"] == minimal_agent_trace.task_id
    assert rec["run_id"] == "test-run-001"
    assert "hardware" in rec


def test_experiment_logger_raises_if_dir_missing(
    minimal_agent_trace: AgentTrace, tmp_path: Path
) -> None:
    out = tmp_path / "nonexistent_dir" / "run.jsonl"
    with pytest.raises(FileNotFoundError):
        with ExperimentLogger("run-x", out) as el:
            el.log_trace(minimal_agent_trace)


def test_experiment_logger_raises_on_existing_file(
    minimal_agent_trace: AgentTrace, log_dir: Path
) -> None:
    out = log_dir / "dup.jsonl"
    out.touch()
    with pytest.raises(FileExistsError):
        with ExperimentLogger("run-dup", out):
            pass


def test_experiment_logger_not_open_raises(
    minimal_agent_trace: AgentTrace, log_dir: Path
) -> None:
    el = ExperimentLogger("run-x", log_dir / "x.jsonl")
    with pytest.raises(RuntimeError):
        el.log_trace(minimal_agent_trace)


def test_experiment_logger_rejects_mismatched_run_id(
    minimal_agent_trace: AgentTrace, log_dir: Path
) -> None:
    out = log_dir / "other-run.jsonl"
    with pytest.raises(RunIdMismatchError, match="logger run_id 'other-run' does not match trace run_id 'test-run-001'"):
        with ExperimentLogger("other-run", out) as el:
            el.log_trace(minimal_agent_trace)


def test_get_logger_returns_logger() -> None:
    log = get_logger("test")
    assert log is not None
