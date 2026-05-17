"""
AgentBase — abstract base class for all AeroSafetyEval agent systems.

Every concrete agent must implement `run()` and return a complete AgentTrace.
No silent failures, no silent degradation (CLAUDE.md §8.1).
"""

from __future__ import annotations

import abc
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from aerosafety.io import AgentTrace, TaskCard

if TYPE_CHECKING:
    from aerosafety.agents.llm_client import LLMClient
    from aerosafety.tools.registry import ToolRegistry


class AgentBase(abc.ABC):
    """
    Abstract base for all agent systems.

    Subclasses must:
      - implement `run()` returning a fully populated AgentTrace
      - never silently catch and discard LLM or tool errors
      - never return a partial AgentTrace with fabricated fields
    """

    system_name: str  # must be set by each subclass

    @abc.abstractmethod
    def run(
        self,
        task: TaskCard,
        llm: "LLMClient",
        tools: "ToolRegistry | None" = None,
    ) -> AgentTrace:
        """
        Execute the agent on *task* using *llm* and optionally *tools*.

        Parameters
        ----------
        task:
            The evaluation task. Never modify this object.
        llm:
            LLM client (real or mock). Must be the sole LLM interface.
        tools:
            Optional tool registry. System 1/2 pass None.

        Returns
        -------
        AgentTrace
            Fully populated trace including model_version, prompt_hash,
            token_usage, tool_calls, retrieved_docs, final_recommendation,
            confidence, requested_escalation, and timing fields.

        Raises
        ------
        Any exception from llm or tools propagates upward — no silent swallowing.
        """

    # ------------------------------------------------------------------
    # Shared helpers available to all subclasses
    # ------------------------------------------------------------------

    @staticmethod
    def _new_run_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _ms_since(start_ns: int) -> float:
        import time
        return (time.perf_counter_ns() - start_ns) / 1_000_000

    @staticmethod
    def _compute_prompt_hash(system_prompt: str, messages: list[dict[str, Any]]) -> str:
        from aerosafety.determinism import prompt_hash
        return prompt_hash(messages, system_prompt)
