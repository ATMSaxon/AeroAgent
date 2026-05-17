# aerosafety/tools package
# All tools are pure functions with typed pydantic inputs/outputs.
# All tools raise explicit exceptions on bad input (CLAUDE.md §8.1).
# Tool outputs must be validated by callers (CLAUDE.md §8.3).
#
# For logged invocations use call_tool() below, which returns a ToolCall
# record compatible with aerosafety.io.ToolCall and AgentTrace.tool_calls.

from __future__ import annotations

import time
import traceback
from typing import Any, Callable

from aerosafety.io import ToolCall
from aerosafety.logging import get_logger

_log = get_logger("tools")


def call_tool(
    fn: Callable[..., Any],
    args: dict[str, Any],
    *,
    tool_name: str | None = None,
) -> ToolCall:
    """
    Invoke a tool function with logged inputs, outputs, runtime, and errors.

    Returns a ToolCall record. On exception the error field is populated and
    the exception is re-raised — CLAUDE.md §8.1: no silent failure.

    Args:
        fn:         The tool callable (e.g. parse_metar, calculate_wind_components).
        args:       Keyword arguments to pass to fn.
        tool_name:  Override name in the ToolCall record; defaults to fn.__name__.

    Example:
        tc = call_tool(parse_metar, {"raw": "METAR KLAX ..."})
        # tc is a ToolCall; append to AgentTrace.tool_calls
    """
    name = tool_name or fn.__name__
    _log.info("tool_call_start", extra={"tool": name, "tool_args": str(args)[:200]})
    t0 = time.perf_counter()
    result = None
    error: str | None = None

    try:
        result = fn(**args)
        # Serialise pydantic models to plain dicts for JSON compatibility
        if hasattr(result, "model_dump"):
            result_serialised: Any = result.model_dump(mode="json")
        else:
            result_serialised = result
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        runtime_ms = (time.perf_counter() - t0) * 1000
        _log.error(
            "tool_call_error",
            extra={"tool": name, "tool_error": str(exc), "runtime_ms": runtime_ms},
        )
        tc = ToolCall(name=name, args=args, result=None, error=error, runtime_ms=runtime_ms)
        raise  # re-raise per CLAUDE.md §8.1

    runtime_ms = (time.perf_counter() - t0) * 1000
    _log.info(
        "tool_call_done",
        extra={"tool": name, "runtime_ms": runtime_ms},
    )
    return ToolCall(
        name=name,
        args=args,
        result=result_serialised,
        error=None,
        runtime_ms=runtime_ms,
    )
