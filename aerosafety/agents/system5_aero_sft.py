"""
System 5: Aviation-SFT Agent.

NOT IMPLEMENTED — Phase 2.

Requires GPU fine-tuning of an open-source model on aviation instruction data.
See proposal §11.1 for training data specification and objectives.

This file exists as a placeholder so the import hierarchy is stable and
callers can check for NotImplementedError cleanly.

Per CLAUDE.md §1.2: a module that is not implemented must clearly state
NOT IMPLEMENTED. No placeholder outputs, no silent fallback.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from aerosafety.agents.base import AgentBase
from aerosafety.io import AgentTrace, TaskCard

if TYPE_CHECKING:
    from aerosafety.agents.llm_client import LLMClient
    from aerosafety.tools.registry import ToolRegistry


class AeroSFTAgent(AgentBase):
    """
    NOT IMPLEMENTED — Phase 2: requires GPU training, see proposal §11.1.

    Training data types required (per proposal §11.1):
      - ASRS reasoning examples
      - NTSB causal analysis examples
      - Weather dispatch examples
      - NOTAM compliance examples
      - Wake separation examples
      - Maintenance release examples
      - Optimization interpretation examples

    Do not instantiate this class until a fine-tuned checkpoint is available
    and its lineage is fully documented (CLAUDE.md §6.1).
    """

    system_name = "system5_aero_sft"

    def run(
        self,
        task: TaskCard,
        llm: LLMClient,
        tools: ToolRegistry | None = None,
    ) -> AgentTrace:
        raise NotImplementedError(
            "System 5 (AeroSFTAgent): NOT IMPLEMENTED. "
            "Phase 2: requires GPU training pipeline. See proposal §11.1."
        )
