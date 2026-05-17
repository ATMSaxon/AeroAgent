"""
Unit tests for System 2: RAGAgent and BM25Retriever.

All LLM calls use MockLLM. No real API calls.
"""

from __future__ import annotations

import json

import pytest

from aerosafety.agents.mock_llm import MockLLM
from aerosafety.agents.system2_rag import BM25Retriever, RAGAgent, Retriever
from aerosafety.io import AgentTrace, RetrievedDoc, TaskCard


def _valid_response(decision: str = "NO-GO") -> str:
    return json.dumps({
        "decision": decision,
        "rationale": "Based on retrieved document.",
        "safety_constraints_cited": ["runway_closure"],
        "evidence_cited": ["notam-001"],
        "escalation_recommended": False,
        "uncertainty_flags": [],
    })


# ---------------------------------------------------------------------------
# BM25Retriever tests (uses rank_bm25; skip if not installed)
# ---------------------------------------------------------------------------

bm25_available = pytest.mark.skipif(
    pytest.importorskip("rank_bm25", reason="rank_bm25 not installed") is None,
    reason="rank_bm25 not installed",
)


class TestBM25Retriever:
    def test_retrieve_empty_corpus_returns_empty(self) -> None:
        try:
            r = BM25Retriever(corpus=[])
        except ImportError:
            pytest.skip("rank_bm25 not installed")
        results = r.retrieve("runway closed", top_k=5)
        assert results == []

    def test_retrieve_returns_docs(self) -> None:
        try:
            r = BM25Retriever(corpus=[
                ("doc-1", "FAA NOTAM archive", "Runway 09/27 closed 1000Z to 1800Z 15 JAN 2024"),
                ("doc-2", "METAR archive", "METAR KLAX 150000Z 29010KT 10SM CLR 22/10 A2992"),
            ])
        except ImportError:
            pytest.skip("rank_bm25 not installed")
        results = r.retrieve("runway closed NOTAM", top_k=1)
        assert len(results) == 1
        assert results[0].doc_id == "doc-1"

    def test_retrieve_returns_retrieved_doc_schema(self) -> None:
        try:
            r = BM25Retriever(corpus=[("d1", "src", "text about aviation")])
        except ImportError:
            pytest.skip("rank_bm25 not installed")
        results = r.retrieve("aviation", top_k=1)
        assert len(results) == 1
        assert isinstance(results[0], RetrievedDoc)
        assert results[0].score is not None


# ---------------------------------------------------------------------------
# Stub retriever for tests that don't need real BM25
# ---------------------------------------------------------------------------

class _FixedRetriever(Retriever):
    """Returns a fixed list of documents regardless of query."""

    def __init__(self, docs: list[RetrievedDoc]) -> None:
        self._docs = docs

    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDoc]:
        return self._docs[:top_k]


class _FailingRetriever(Retriever):
    def retrieve(self, query: str, top_k: int = 5) -> list[RetrievedDoc]:
        raise RuntimeError("Retrieval backend unavailable")


# ---------------------------------------------------------------------------
# RAGAgent tests
# ---------------------------------------------------------------------------

class TestRAGAgentTrace:
    def test_returns_agent_trace(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_valid_response()])
        agent = RAGAgent(retriever=_FixedRetriever([]))
        trace = agent.run(synthetic_task_card, llm)
        assert isinstance(trace, AgentTrace)

    def test_system_name(self) -> None:
        assert RAGAgent.system_name == "system2_rag"

    def test_retrieved_docs_in_trace(self, synthetic_task_card: TaskCard) -> None:
        doc = RetrievedDoc(doc_id="d1", source="FAA", chunk_text="runway closed", score=0.9)
        llm = MockLLM(responses=[_valid_response()])
        agent = RAGAgent(retriever=_FixedRetriever([doc]))
        trace = agent.run(synthetic_task_card, llm)
        assert len(trace.retrieved_docs) == 1
        assert trace.retrieved_docs[0].doc_id == "d1"

    def test_no_tool_calls(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_valid_response()])
        agent = RAGAgent(retriever=_FixedRetriever([]))
        trace = agent.run(synthetic_task_card, llm)
        assert trace.tool_calls == []

    def test_decision_extracted(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_valid_response("NO-GO")])
        trace = RAGAgent(retriever=_FixedRetriever([])).run(synthetic_task_card, llm)
        assert trace.final_recommendation.decision == "NO-GO"

    def test_token_usage_recorded(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_valid_response()], prompt_tokens_per_call=50, completion_tokens_per_call=25)
        trace = RAGAgent(retriever=_FixedRetriever([])).run(synthetic_task_card, llm)
        assert trace.token_usage["total"] == 75

    def test_prompt_hash_64_hex_chars(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_valid_response()])
        trace = RAGAgent(retriever=_FixedRetriever([])).run(synthetic_task_card, llm)
        assert len(trace.prompt_hash) == 64


class TestRAGAgentRetrieverFailure:
    def test_retriever_error_flagged_not_raised(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_valid_response()])
        agent = RAGAgent(retriever=_FailingRetriever())
        trace = agent.run(synthetic_task_card, llm)
        assert trace.had_retrieval_error is True

    def test_retriever_error_empty_docs(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[_valid_response()])
        trace = RAGAgent(retriever=_FailingRetriever()).run(synthetic_task_card, llm)
        assert trace.retrieved_docs == []

    def test_llm_error_propagates(self, synthetic_task_card: TaskCard) -> None:
        llm = MockLLM(responses=[RuntimeError("API failure")])
        with pytest.raises(RuntimeError, match="API failure"):
            RAGAgent(retriever=_FixedRetriever([])).run(synthetic_task_card, llm)


class TestRAGAgentConstraintAware:
    def test_constraint_aware_mode_makes_extra_llm_call(self, synthetic_task_card: TaskCard) -> None:
        # Constraint extraction response + main response
        constraint_resp = json.dumps(["runway closure", "NOTAM time window"])
        main_resp = _valid_response()
        llm = MockLLM(responses=[constraint_resp, main_resp])
        agent = RAGAgent(retriever=_FixedRetriever([]), mode="constraint_aware")
        trace = agent.run(synthetic_task_card, llm)
        assert llm.call_count == 2
        assert isinstance(trace, AgentTrace)

    def test_constraint_parse_failure_falls_back_to_naive(self, synthetic_task_card: TaskCard) -> None:
        # First call returns invalid JSON (constraint extraction)
        # Second call returns valid recommendation
        llm = MockLLM(responses=["not json", _valid_response()])
        agent = RAGAgent(retriever=_FixedRetriever([]), mode="constraint_aware")
        trace = agent.run(synthetic_task_card, llm)
        # Should succeed despite parse failure in constraint step
        assert isinstance(trace, AgentTrace)
        assert trace.had_parse_error is True
