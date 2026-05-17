"""
Evidence Faithfulness — proposal §12.4

Four sub-metrics aggregated over all traces:

1. citation_rate         = #traces_with_at_least_one_citation / N
2. unsupported_claim_rate = total_unsupported_claims / total_claims_made
3. hallucinated_evidence_rate = total_hallucinated / total_citations_made
4. contradiction_rate    = total_contradictions / total_claims_made

where total_claims_made = len(citations) + len(unsupported_claims)
(citations represent grounded claims; unsupported_claims are additional ungrounded ones)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aerosafety.eval.protocols import AgentTraceProtocol


def evidence_faithfulness(
    traces: list["AgentTraceProtocol"],
) -> dict:
    """
    Compute all four Evidence Faithfulness sub-metrics.

    Returns
    -------
    dict with keys:
        citation_rate              : float
        unsupported_claim_rate     : float
        hallucinated_evidence_rate : float
        contradiction_rate         : float
        n_total                    : int
        per_task                   : list[dict]
    """
    if not traces:
        return {
            "citation_rate": float("nan"),
            "unsupported_claim_rate": float("nan"),
            "hallucinated_evidence_rate": float("nan"),
            "contradiction_rate": float("nan"),
            "n_total": 0,
            "per_task": [],
        }

    total_cited = 0
    total_unsupported = 0
    total_hallucinated = 0
    total_contradictions = 0
    total_citations_made = 0
    total_claims_made = 0
    n_with_citation = 0
    per_task = []

    for t in traces:
        n_citations = len(t.citations)
        n_unsupported = len(t.unsupported_claims)
        n_hallucinated = len(t.hallucinated_evidence)
        n_contradictions = len(t.contradictions)

        has_citation = n_citations > 0
        if has_citation:
            n_with_citation += 1

        claims = n_citations + n_unsupported

        total_citations_made += n_citations
        total_hallucinated += n_hallucinated
        total_unsupported += n_unsupported
        total_contradictions += n_contradictions
        total_claims_made += claims

        per_task.append(
            {
                "task_id": t.task_id,
                "has_citation": has_citation,
                "n_citations": n_citations,
                "n_unsupported_claims": n_unsupported,
                "n_hallucinated_evidence": n_hallucinated,
                "n_contradictions": n_contradictions,
            }
        )

    n = len(traces)
    citation_rate = n_with_citation / n

    unsupported_claim_rate = (
        total_unsupported / total_claims_made if total_claims_made > 0 else float("nan")
    )
    hallucinated_evidence_rate = (
        total_hallucinated / total_citations_made
        if total_citations_made > 0
        else float("nan")
    )
    contradiction_rate = (
        total_contradictions / total_claims_made
        if total_claims_made > 0
        else float("nan")
    )

    return {
        "citation_rate": citation_rate,
        "unsupported_claim_rate": unsupported_claim_rate,
        "hallucinated_evidence_rate": hallucinated_evidence_rate,
        "contradiction_rate": contradiction_rate,
        "n_total": n,
        "per_task": per_task,
    }
