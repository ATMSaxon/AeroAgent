"""
Structured logging for AeroSafetyEval.

Per CLAUDE.md §5.1, every experiment run must log:
  model_version, prompt_hash, tool_calls, retrieved_docs,
  timestamps, runtime, hardware.

Usage:
    from aerosafety.logging import get_logger, ExperimentLogger

    log = get_logger("my_module")
    log.info("Starting evaluation run", task_id="task-001")

    with ExperimentLogger(run_id="run-001", output_path=Path("logs/run-001.jsonl")) as el:
        el.log_trace(agent_trace)
"""

from aerosafety.logging.logger import ExperimentLogger, RunIdMismatchError, get_logger

__all__ = ["ExperimentLogger", "RunIdMismatchError", "get_logger"]
