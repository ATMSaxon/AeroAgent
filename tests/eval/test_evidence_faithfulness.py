"""
Unit tests for Evidence Faithfulness — aerosafety/eval/evidence_faithfulness.py

Hand-computed expected values:

Case 1 (perfect faithfulness, N=2):
  Both traces: 2 citations, 0 unsupported, 0 hallucinated, 0 contradictions
  citation_rate = 2/2 = 1.0
  unsupported_claim_rate = 0/(4+0) = 0.0
  hallucinated_evidence_rate = 0/4 = 0.0
  contradiction_rate = 0/(4+0) = 0.0

Case 2 (all unfaithful, N=1):
  0 citations, 3 unsupported, 2 hallucinated, 1 contradiction
  citation_rate = 0/1 = 0.0
  unsupported_claim_rate = 3/(0+3) = 1.0
  hallucinated_evidence_rate = 2/0 = NaN (no citations were made)
  contradiction_rate = 1/(0+3) = 1/3

Case 3 (mixed, N=3):
  t1: citations=["a"], unsupported=[], hallucinated=[], contradictions=[]
  t2: citations=[], unsupported=["x"], hallucinated=[], contradictions=[]
  t3: citations=["b","c"], unsupported=[], hallucinated=["c"], contradictions=["b"]
  citation_rate = 2/3
  total_claims = (1+0+0) + (0+1+0) + (2+0+0) = 1+1+2=4 (citations only, unsupported=0,0,0)
  Wait — corrected:
    total_claims_t1 = len(citations)+len(unsupported) = 1+0 = 1
    total_claims_t2 = 0+1 = 1
    total_claims_t3 = 2+0 = 2
    total_claims = 4
  total_citations_made = 1+0+2 = 3
  total_unsupported = 0+1+0 = 1
  total_hallucinated = 0+0+1 = 1
  total_contradictions = 0+0+1 = 1
  unsupported_claim_rate = 1/4 = 0.25
  hallucinated_evidence_rate = 1/3
  contradiction_rate = 1/4 = 0.25

Case 4 (empty):
  All NaN, n_total=0
"""

from __future__ import annotations

import math

from aerosafety.eval.protocols import AgentTraceStub
from aerosafety.eval.evidence_faithfulness import evidence_faithfulness


def _trace(
    task_id: str,
    citations: list[str],
    unsupported: list[str],
    hallucinated: list[str],
    contradictions: list[str],
) -> AgentTraceStub:
    return AgentTraceStub(
        task_id=task_id,
        predicted_decision="x",
        gold_decision="x",
        citations=citations,
        unsupported_claims=unsupported,
        hallucinated_evidence=hallucinated,
        contradictions=contradictions,
    )


class TestEvidenceFaithfulnessPerfect:
    def test_all_rates_best_case(self):
        traces = [
            _trace("t1", ["e1", "e2"], [], [], []),
            _trace("t2", ["e3", "e4"], [], [], []),
        ]
        result = evidence_faithfulness(traces)
        assert result["citation_rate"] == 1.0
        assert result["unsupported_claim_rate"] == 0.0
        assert result["hallucinated_evidence_rate"] == 0.0
        assert result["contradiction_rate"] == 0.0
        assert result["n_total"] == 2


class TestEvidenceFaithfulnessWorstCase:
    def test_unfaithful_trace(self):
        # 0 citations, 3 unsupported, 2 hallucinated-but-n/a (no citations), 1 contradiction
        traces = [_trace("t1", [], ["u1", "u2", "u3"], ["h1", "h2"], ["c1"])]
        result = evidence_faithfulness(traces)
        assert result["citation_rate"] == 0.0
        assert result["unsupported_claim_rate"] == 1.0  # 3/(0+3)
        assert math.isnan(result["hallucinated_evidence_rate"])  # 0 citations → NaN
        assert abs(result["contradiction_rate"] - 1.0 / 3.0) < 1e-9  # 1/(0+3)


class TestEvidenceFaithfulnessMixed:
    def test_mixed_three_traces(self):
        traces = [
            _trace("t1", ["a"], [], [], []),
            _trace("t2", [], ["x"], [], []),
            _trace("t3", ["b", "c"], [], ["c"], ["b"]),
        ]
        result = evidence_faithfulness(traces)
        # citation_rate = 2/3
        assert abs(result["citation_rate"] - 2.0 / 3.0) < 1e-9
        # unsupported_claim_rate = 1/4
        assert abs(result["unsupported_claim_rate"] - 0.25) < 1e-9
        # hallucinated_evidence_rate = 1/3
        assert abs(result["hallucinated_evidence_rate"] - 1.0 / 3.0) < 1e-9
        # contradiction_rate = 1/4
        assert abs(result["contradiction_rate"] - 0.25) < 1e-9


class TestEvidenceFaithfulnessEmpty:
    def test_empty_all_nan(self):
        result = evidence_faithfulness([])
        assert math.isnan(result["citation_rate"])
        assert result["n_total"] == 0
        assert result["per_task"] == []
