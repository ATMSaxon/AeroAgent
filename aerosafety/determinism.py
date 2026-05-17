"""
Determinism utilities for reproducible evaluation runs.

Per CLAUDE.md §8.2: evaluation pipelines must support deterministic reruns.
Call `lock_seeds(seed)` once at the start of any eval script.
"""

from __future__ import annotations

import hashlib
import json
import os
import random
import sys
from typing import Any


def lock_seeds(seed: int = 42) -> None:
    """Fix Python, NumPy (if available), and Torch (if available) seeds."""
    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)

    try:
        import numpy as np  # noqa: PLC0415
        np.random.seed(seed)
    except ImportError:
        pass

    try:
        import torch  # noqa: PLC0415
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except ImportError:
        pass


def prompt_hash(messages: list[dict[str, Any]], system_prompt: str) -> str:
    """
    Return a stable SHA-256 hex digest of the full prompt.

    The digest is computed over the JSON-serialised (sorted keys) concatenation
    of the system prompt and messages list so that it is deterministic across
    Python processes and versions.
    """
    payload = json.dumps(
        {"system_prompt": system_prompt, "messages": messages},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def assert_eval_mode() -> None:
    """
    Raise if the process is not running in deterministic evaluation mode.

    Callers should invoke this at the top of eval entry-points.
    Evaluation mode is signalled by the env var AEROSAFETY_EVAL_MODE=1.
    """
    if os.environ.get("AEROSAFETY_EVAL_MODE", "0") != "1":
        raise RuntimeError(
            "AEROSAFETY_EVAL_MODE is not set to '1'. "
            "Evaluation scripts must be launched with AEROSAFETY_EVAL_MODE=1 "
            "to guarantee deterministic, reproducible runs."
        )


def python_version_string() -> str:
    v = sys.version_info
    return f"{v.major}.{v.minor}.{v.micro}"
