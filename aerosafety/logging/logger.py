"""
Structured experiment logger for AeroSafetyEval.

Design constraints (CLAUDE.md §8.1, §5.1):
- No silent failure: every write error raises immediately.
- Every AgentTrace is serialised as a single JSONL line for append-safe
  concurrent writes and line-by-line streaming analysis.
- Hardware snapshot is captured once per ExperimentLogger instantiation.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import platform
import socket
import sys
from pathlib import Path
from typing import Any, Optional

from aerosafety.io import AgentTrace


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class RunIdMismatchError(ValueError):
    """Raised when a trace's run_id does not match the ExperimentLogger's run_id."""


# ---------------------------------------------------------------------------
# Standard Python logger (text console output)
# ---------------------------------------------------------------------------

def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Return a structlog-style Python logger that writes JSON lines to stderr.

    We deliberately write to stderr so that stdout remains clean for any
    piped-output workflows.
    """
    logger = logging.getLogger(f"aerosafety.{name}")
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(_JsonFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(level)
    return logger


class _JsonFormatter(logging.Formatter):
    """Emit each log record as a single JSON line."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        payload: dict[str, Any] = {
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        # Merge any extra kwargs passed via logging.info(..., extra={...})
        for key, val in record.__dict__.items():
            if key not in _STDLIB_LOG_ATTRS and not key.startswith("_"):
                payload[key] = val
        return json.dumps(payload, default=str, ensure_ascii=False)


_STDLIB_LOG_ATTRS = frozenset(logging.LogRecord(
    "", 0, "", 0, "", (), None
).__dict__.keys()) | {"message", "asctime"}


# ---------------------------------------------------------------------------
# ExperimentLogger
# ---------------------------------------------------------------------------

class ExperimentLogger:
    """
    Context-manager that writes AgentTrace records to a JSONL file.

    Parameters
    ----------
    run_id:
        Unique identifier for this evaluation run.
    output_path:
        Path to the JSONL file. Parent directory must exist — we do not
        silently create it (fail fast per CLAUDE.md §8.1).
    append:
        If True, open the file in append mode (safe for resumed runs).
        If False, raise if the file already exists to prevent accidental
        overwrite of a previous run's data.
    """

    def __init__(
        self,
        run_id: str,
        output_path: Path,
        *,
        append: bool = False,
    ) -> None:
        self.run_id = run_id
        self.output_path = Path(output_path)
        self._append = append
        self._hardware: dict[str, Any] = _capture_hardware()
        self._file: Optional[Any] = None
        self._count = 0

    # -- context manager --

    def __enter__(self) -> "ExperimentLogger":
        if not self.output_path.parent.exists():
            raise FileNotFoundError(
                f"Log directory does not exist: {self.output_path.parent}. "
                "Create it explicitly before starting ExperimentLogger."
            )
        mode = "a" if self._append else "x"
        try:
            self._file = self.output_path.open(mode, encoding="utf-8")
        except FileExistsError:
            raise FileExistsError(
                f"Log file already exists: {self.output_path}. "
                "Pass append=True to resume, or choose a new path."
            ) from None
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self._file is not None:
            self._file.flush()
            self._file.close()
            self._file = None

    # -- public API --

    def log_trace(self, trace: AgentTrace) -> None:
        """
        Serialise one AgentTrace to a JSONL line.

        Raises immediately on any write error or run_id mismatch (CLAUDE.md §8.1).
        """
        if self._file is None:
            raise RuntimeError(
                "ExperimentLogger is not open. Use it as a context manager."
            )
        if trace.run_id != self.run_id:
            raise RunIdMismatchError(
                f"logger run_id {self.run_id!r} does not match trace run_id {trace.run_id!r}"
            )
        record = {
            "run_id": self.run_id,
            "seq": self._count,
            "hardware": self._hardware,
            **trace.model_dump(mode="json"),
        }
        line = json.dumps(record, default=str, ensure_ascii=False) + "\n"
        self._file.write(line)
        self._file.flush()  # no buffering — each trace is immediately durable
        self._count += 1

    def log_event(self, event: str, **kwargs: Any) -> None:
        """Write an arbitrary structured event (non-trace) to the same JSONL file."""
        if self._file is None:
            raise RuntimeError(
                "ExperimentLogger is not open. Use it as a context manager."
            )
        record = {
            "run_id": self.run_id,
            "ts": datetime.datetime.utcnow().isoformat() + "Z",
            "event": event,
            **kwargs,
        }
        self._file.write(json.dumps(record, default=str, ensure_ascii=False) + "\n")
        self._file.flush()

    @property
    def hardware(self) -> dict[str, Any]:
        return self._hardware

    @property
    def traces_written(self) -> int:
        return self._count


# ---------------------------------------------------------------------------
# Hardware snapshot
# ---------------------------------------------------------------------------

def _capture_hardware() -> dict[str, Any]:
    """
    Capture a best-effort hardware/environment snapshot.

    Fields that cannot be read are set to None — never silently omitted.
    """
    snapshot: dict[str, Any] = {
        "hostname": socket.gethostname(),
        "platform": platform.platform(),
        "python_version": sys.version,
        "cpu_count": os.cpu_count(),
        "aerosafety_eval_mode": os.environ.get("AEROSAFETY_EVAL_MODE"),
    }

    # GPU info via torch (optional dep)
    try:
        import torch  # noqa: PLC0415
        snapshot["cuda_available"] = torch.cuda.is_available()
        if torch.cuda.is_available():
            snapshot["cuda_device_count"] = torch.cuda.device_count()
            snapshot["cuda_device_names"] = [
                torch.cuda.get_device_name(i)
                for i in range(torch.cuda.device_count())
            ]
    except ImportError:
        snapshot["cuda_available"] = None

    # Memory info via psutil (optional dep)
    try:
        import psutil  # noqa: PLC0415
        mem = psutil.virtual_memory()
        snapshot["ram_total_gb"] = round(mem.total / (1024 ** 3), 2)
        snapshot["ram_available_gb"] = round(mem.available / (1024 ** 3), 2)
    except ImportError:
        snapshot["ram_total_gb"] = None
        snapshot["ram_available_gb"] = None

    return snapshot
