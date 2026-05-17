"""
Unit tests for MockLLM.

All tests use only MockLLM — no real LLM calls (CLAUDE.md §8.1 rule for tests).
"""

from __future__ import annotations

import pytest

from aerosafety.agents.mock_llm import MockLLM


class TestMockLLMBasicResponses:
    def test_returns_scripted_string(self) -> None:
        llm = MockLLM(responses=["PROCEED"])
        resp = llm.complete([{"role": "user", "content": "fly?"}])
        assert resp.content == "PROCEED"

    def test_cycles_through_responses(self) -> None:
        llm = MockLLM(responses=["A", "B"])
        assert llm.complete([]).content == "A"
        assert llm.complete([]).content == "B"
        assert llm.complete([]).content == "A"  # cycles

    def test_raises_scripted_exception(self) -> None:
        err = RuntimeError("LLM timeout")
        llm = MockLLM(responses=[err])
        with pytest.raises(RuntimeError, match="LLM timeout"):
            llm.complete([])

    def test_model_name_recorded(self) -> None:
        llm = MockLLM(responses=["ok"], model="mock/my-model")
        resp = llm.complete([])
        assert resp.model == "mock/my-model"

    def test_model_override_per_call(self) -> None:
        llm = MockLLM(responses=["ok"])
        resp = llm.complete([], model="mock/override")
        assert resp.model == "mock/override"

    def test_token_usage_in_response(self) -> None:
        llm = MockLLM(responses=["ok"], prompt_tokens_per_call=42, completion_tokens_per_call=18)
        resp = llm.complete([])
        usage = resp.token_usage_dict()
        assert usage["prompt"] == 42
        assert usage["completion"] == 18
        assert usage["total"] == 60

    def test_call_history_recorded(self) -> None:
        llm = MockLLM(responses=["a", "b"])
        llm.complete([{"role": "user", "content": "msg1"}])
        llm.complete([{"role": "user", "content": "msg2"}])
        assert llm.call_count == 2
        assert llm.call_history[0]["messages"][0]["content"] == "msg1"
        assert llm.call_history[1]["messages"][0]["content"] == "msg2"

    def test_reset_clears_history(self) -> None:
        llm = MockLLM(responses=["a", "b"])
        llm.complete([])
        llm.reset()
        assert llm.call_count == 0
        assert llm.complete([]).content == "a"  # restarts from index 0
