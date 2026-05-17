"""
mock_run.py — Deterministic end-to-end pipeline validation with MockLLM.

This module validates that the full pipeline
    TaskCard → Agent → AgentTrace → EvalAnnotation → EvalView → EvalRunner
runs without errors and produces structurally valid outputs.

It does NOT call any real LLM. All results are from MockLLM and are clearly
marked MOCK — they carry no research value.

Usage (programmatic):
    from aerosafety.smoke_test.mock_run import run_mock_pipeline
    result = run_mock_pipeline(systems=[1, 2, 3, 4], limit=5, output_dir="/tmp/smoke")

The function is also the backing implementation for the --dry-run flag in runner.py.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from aerosafety.agents.mock_llm import MockLLM
from aerosafety.agents.system1_direct import DirectLLMAgent
from aerosafety.agents.system2_rag import RAGAgent
from aerosafety.agents.system3_tool_aug import ToolAugmentedAgent
from aerosafety.agents.system4_multi_agent import MultiAgentSystem
from aerosafety.agents.system7_verifier_gated import VerifierGatedAgent
from aerosafety.determinism import lock_seeds, assert_eval_mode
from aerosafety.eval.adapters import EvalTaskCard, make_eval_view
from aerosafety.eval.protocols import AgentTraceStub, TaskCardStub
from aerosafety.io import AgentTrace, TaskCard, TaskProvenance
from aerosafety.smoke_test.annotate import rule_based_annotate


# ---------------------------------------------------------------------------
# TaskCard loader
# ---------------------------------------------------------------------------

_TASK_DIRS = [
    "aerosafety/tasks/notam_compliance/taskcards",
    "aerosafety/tasks/weather_dispatch/taskcards",
]

_FAMILY_MAP = {
    "notam": "aerosafety/tasks/notam_compliance/taskcards",
    "weather": "aerosafety/tasks/weather_dispatch/taskcards",
    "all": None,
}


def load_task_cards(
    families: list[str] | None = None,
    limit: int | None = None,
    project_root: Path | None = None,
) -> list[TaskCard]:
    """
    Load TaskCards from JSONL files under aerosafety/tasks/.

    Parameters
    ----------
    families:
        List of family names to include: "notam", "weather", or None for all.
    limit:
        Maximum number of cards to return (across all families).
    project_root:
        Root of the AeroAgent project. Defaults to two parents above this file.

    Returns
    -------
    list[TaskCard] — validated Pydantic objects.
    """
    if project_root is None:
        project_root = Path(__file__).parent.parent.parent

    dirs: list[Path] = []
    if families is None or "all" in families:
        dirs = [project_root / d for d in _TASK_DIRS]
    else:
        for fam in families:
            if fam == "notam":
                dirs.append(project_root / "aerosafety/tasks/notam_compliance/taskcards")
            elif fam == "weather":
                dirs.append(project_root / "aerosafety/tasks/weather_dispatch/taskcards")
            else:
                raise ValueError(f"Unknown family: {fam!r}. Valid: 'notam', 'weather'.")

    cards: list[TaskCard] = []
    for d in dirs:
        if not d.is_dir():
            continue
        for jsonl_file in sorted(d.glob("*.jsonl")):
            with jsonl_file.open(encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    raw = json.loads(line)
                    # Pydantic will validate; raises ValidationError on bad data
                    cards.append(TaskCard.model_validate(raw))
            if limit is not None and len(cards) >= limit:
                return cards[:limit]

    if limit is not None:
        cards = cards[:limit]
    return cards


# ---------------------------------------------------------------------------
# Mock LLM response factory
# ---------------------------------------------------------------------------

def _mock_responses_for_system(system_id: int, n_tasks: int) -> list[str]:
    """
    Build a list of mock LLM responses for a given system and task count.

    System 4 needs 5 responses per task (one per role).
    System 7 wraps System 3 + 6 verifier calls per task.
    All other systems need 1 response per task.

    Responses are structured JSON matching what each system expects.
    """
    single = json.dumps({
        "action": "final",
        "decision": "NO-GO",
        "rationale": "[MOCK] Runway closed per NOTAM. Operation not permitted.",
        "safety_constraints_cited": ["runway_closure_notam"],
        "evidence_cited": ["mock_evidence_001"],
        "escalation_recommended": False,
        "uncertainty_flags": [],
    })

    direct_response = json.dumps({
        "decision": "NO-GO",
        "rationale": "[MOCK] Runway closed per NOTAM. Operation not permitted.",
        "safety_constraints_cited": ["runway_closure_notam"],
        "evidence_cited": ["mock_evidence_001"],
        "escalation_recommended": False,
        "uncertainty_flags": [],
    })

    ops_analyst = json.dumps({
        "role": "operations_analyst",
        "operational_facts": ["[MOCK] runway closed"],
        "missing_information": [],
        "operational_risks": ["[MOCK] departure blocked"],
        "notes": "[MOCK]",
    })
    safety_officer = json.dumps({
        "role": "safety_officer",
        "applicable_safety_constraints": ["[MOCK] NOTAM compliance"],
        "potential_violations": ["[MOCK] departure on closed runway"],
        "severity_assessment": "High",
        "escalation_warranted": False,
        "notes": "[MOCK]",
    })
    reg_specialist = json.dumps({
        "role": "regulation_specialist",
        "applicable_regulations": ["[MOCK] FAR 91.137"],
        "compliance_assessment": "NON-COMPLIANT",
        "ambiguities": [],
        "notes": "[MOCK]",
    })
    tool_agent = json.dumps({
        "role": "tool_use_agent",
        "tools_invoked": [],
        "computed_values": {},
        "tool_errors": [],
        "notes": "[MOCK]",
    })
    final_agent = json.dumps({
        "role": "final_decision_agent",
        "decision": "NO-GO",
        "rationale": "[MOCK] All roles concur: operation not permitted.",
        "safety_constraints_cited": ["runway_closure_notam"],
        "evidence_cited": ["mock_evidence_001"],
        "escalation_recommended": False,
        "uncertainty_flags": [],
    })

    verifier_pass = json.dumps({
        "passed": True,
        "violated_constraints": [],
        "severity": "Low",
        "notes": "[MOCK] Verifier pass.",
    })

    if system_id == 1:
        return [direct_response] * n_tasks
    elif system_id == 2:
        return [direct_response] * n_tasks
    elif system_id == 3:
        return [single] * n_tasks
    elif system_id == 4:
        # 5 role responses per task
        per_task = [ops_analyst, safety_officer, reg_specialist, tool_agent, final_agent]
        return per_task * n_tasks
    elif system_id == 7:
        # System 3 primary (1 response) + 6 verifier responses per task
        per_task = [single] + [verifier_pass] * 6
        return per_task * n_tasks
    else:
        raise ValueError(f"Unknown system_id: {system_id}")


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------

def _make_agent(system_id: int) -> Any:
    if system_id == 1:
        return DirectLLMAgent()
    elif system_id == 2:
        return RAGAgent()
    elif system_id == 3:
        return ToolAugmentedAgent()
    elif system_id == 4:
        return MultiAgentSystem()
    elif system_id == 7:
        return VerifierGatedAgent()
    else:
        raise ValueError(f"Unknown system_id: {system_id}")


# ---------------------------------------------------------------------------
# Wrapped agent that satisfies EvalRunner.AgentProtocol
# ---------------------------------------------------------------------------

class _AnnotatingAgentWrapper:
    """
    Wraps an agent + LLM + annotator to produce EvalView objects that satisfy
    the AgentTraceProtocol required by EvalRunner.

    EvalRunner calls agent.run(eval_card) and expects an AgentTraceProtocol.
    This wrapper:
      1. Unwraps EvalTaskCard → underlying TaskCard.
      2. Calls the underlying agent with agent.run(task, llm).
      3. Produces rule-based EvalAnnotation.
      4. Calls make_eval_view() to produce the flat EvalView.
      5. Returns the EvalView (which satisfies AgentTraceProtocol).
    """

    def __init__(self, agent: Any, llm: MockLLM) -> None:
        self._agent = agent
        self._llm = llm

    def run(self, eval_card: EvalTaskCard) -> Any:
        task_card: TaskCard = eval_card.task_card
        trace: AgentTrace = self._agent.run(task_card, self._llm)
        annotation = rule_based_annotate(trace, task_card, eval_card)
        return make_eval_view(trace, annotation, eval_card)


# ---------------------------------------------------------------------------
# Main pipeline function
# ---------------------------------------------------------------------------

def run_mock_pipeline(
    systems: list[int] | None = None,
    families: list[str] | None = None,
    limit: int = 5,
    output_dir: str | Path = "smoke_test_outputs",
    n_bootstrap: int = 100,
    seed: int = 42,
) -> dict[str, Any]:
    """
    Run all requested agent systems on a sample of TaskCards using MockLLM.

    Parameters
    ----------
    systems:
        List of system IDs to run (1, 2, 3, 4, 7). Default: [1, 2, 3, 4].
    families:
        Task families to include: ["notam", "weather"] or None for all.
    limit:
        Max tasks per system. Default: 5.
    output_dir:
        Directory for per-system JSONL + summary markdown outputs.
    n_bootstrap:
        Bootstrap resamples for CIs. Default: 100 (fast for smoke tests).
    seed:
        Random seed.

    Returns
    -------
    dict with:
        system_results : dict[str, dict]  — per-system EvalRunner.run() outputs
        all_valid      : bool             — True if all traces are structurally valid
        errors         : list[str]        — any structural validation errors found
        output_dir     : Path

    Raises
    ------
    RuntimeError if AEROSAFETY_EVAL_MODE is not set.
    """
    assert_eval_mode()
    lock_seeds(seed)

    if systems is None:
        systems = [1, 2, 3, 4]
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Import EvalRunner here (it also calls assert_eval_mode internally)
    from aerosafety.eval.runner import EvalRunner  # noqa: PLC0415

    raw_tasks = load_task_cards(families=families, limit=limit)
    if not raw_tasks:
        raise RuntimeError(
            "No TaskCards loaded. Check that aerosafety/tasks/*/taskcards/*.jsonl exist."
        )

    # Wrap TaskCards in EvalTaskCard so EvalRunner gets required_tool_names
    # and ground_truth_consequence_points (both empty for Phase 1 pilot).
    eval_task_set = [
        EvalTaskCard(
            task_card=tc,
            required_tool_names=[],
            ground_truth_consequence_points=[],
        )
        for tc in raw_tasks
    ]

    system_results: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for sys_id in systems:
        system_name = f"system{sys_id}"
        responses = _mock_responses_for_system(sys_id, len(eval_task_set))
        llm = MockLLM(responses=responses, model=f"mock/system{sys_id}-test")
        agent = _make_agent(sys_id)
        wrapped = _AnnotatingAgentWrapper(agent, llm)

        sys_output_dir = output_dir / system_name
        sys_output_dir.mkdir(parents=True, exist_ok=True)

        runner = EvalRunner(
            agent=wrapped,
            task_set=eval_task_set,
            output_dir=sys_output_dir,
            n_bootstrap=n_bootstrap,
            bootstrap_seed=seed,
        )
        results = runner.run()
        system_results[system_name] = results

        # Structural validation: every trace must have required fields
        for view in results["traces"]:
            if not hasattr(view, "task_id"):
                errors.append(f"{system_name}: trace missing task_id")
            if not hasattr(view, "predicted_decision"):
                errors.append(f"{system_name}: trace missing predicted_decision")
            if not hasattr(view, "unsafe_recommendation"):
                errors.append(f"{system_name}: trace missing unsafe_recommendation")

    return {
        "system_results": system_results,
        "all_valid": len(errors) == 0,
        "errors": errors,
        "output_dir": output_dir,
    }
