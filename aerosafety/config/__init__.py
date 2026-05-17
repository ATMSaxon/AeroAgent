"""Config loader for AeroSafetyEval.

Raises immediately on missing keys or missing env vars — no silent fallback.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:
    raise ImportError(
        "PyYAML is required for config loading. "
        "Install it via: pip install pyyaml"
    ) from exc


_DEFAULT_CONFIG_PATH = Path(__file__).parent / "base.yaml"


def load_config(path: Path | str | None = None) -> dict[str, Any]:
    """
    Load YAML config.  If `path` is None, load base.yaml.

    Raises FileNotFoundError immediately if the file does not exist.
    """
    config_path = Path(path) if path is not None else _DEFAULT_CONFIG_PATH
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path}. "
            "Do not proceed without a valid configuration."
        )
    with config_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Config file must be a YAML mapping: {config_path}")
    return data


def require_env(var: str) -> str:
    """
    Return the value of an environment variable.

    Raises immediately if the variable is not set or empty — per CLAUDE.md §8.1.
    """
    val = os.environ.get(var, "")
    if not val:
        raise EnvironmentError(
            f"Required environment variable '{var}' is not set. "
            "Check your .env file and ensure it is sourced before running."
        )
    return val
