"""
System 6: Aviation-DPO Agent.

NOT IMPLEMENTED — Phase 2.

Requires GPU preference optimisation (DPO) on safe vs unsafe aviation decision pairs.
See proposal §11.2 for preference pair types and alignment objectives.

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


class AeroDPOAgent(AgentBase):
    """
    NOT IMPLEMENTED — Phase 2: requires GPU training, see proposal §11.2.

    Preference pair types required (per proposal §11.2):
      - safe vs unsafe recommendation
      - evidence-supported vs unsupported answer
      - complete constraint reasoning vs incomplete reasoning
      - conservative escalation vs overconfident automation
      - correct tool use vs wrong tool use
      - rule-compliant vs rule-violating decision

    Do not instantiate this class until a preference-optimised checkpoint is
    available and all preference pairs are documented (CLAUDE.md §6.2).
    """

    system_name = "system6_aero_dpo"

    def run(
        self,
        task: TaskCard,
        llm: LLMClient,
        tools: ToolRegistry | None = None,
    ) -> AgentTrace:
        raise NotImplementedError(
            "System 6 (AeroDPOAgent): NOT IMPLEMENTED. "
            "Phase 2: requires GPU DPO training pipeline. See proposal §11.2."
        )
