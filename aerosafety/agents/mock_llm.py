"""
MockLLM — deterministic mock for unit tests.

Rules:
  - Returns pre-scripted responses in order (cycling if exhausted).
  - Raises scripted exceptions when the response entry is an Exception.
  - Never calls any external service.
  - Tracks call history for test assertions.
"""

from __future__ import annotations

from typing import Any

from aerosafety.agents.llm_client import LLMClient, LLMResponse


class MockLLM(LLMClient):
    """
    Deterministic drop-in replacement for LLMClient.

    Parameters
    ----------
    responses:
        Ordered list of either:
          - str: returned as the completion content
          - Exception: raised when this response is consumed
        Cycles from the start when the list is exhausted.
    model:
        Model string recorded in each LLMResponse (default: "mock/test-model").
    prompt_tokens_per_call:
        Fixed prompt-token count recorded in usage (default: 100).
    completion_tokens_per_call:
        Fixed completion-token count recorded in usage (default: 50).

    Usage
    -----
    >>> llm = MockLLM(responses=["PROCEED", "NO-GO"])
    >>> r = llm.complete([{"role": "user", "content": "fly?"}])
    >>> r.content
    'PROCEED'
    """

    def __init__(
        self,
        responses: list[str | Exception],
        model: str = "mock/test-model",
        prompt_tokens_per_call: int = 100,
        completion_tokens_per_call: int = 50,
    ) -> None:
        # Do NOT call super().__init__() — we never touch litellm.
        self.default_model = model
        self._default_kwargs: dict[str, Any] = {}
        self._responses = responses
        self._call_index = 0
        self._prompt_tokens = prompt_tokens_per_call
        self._completion_tokens = completion_tokens_per_call
        # History of (messages, kwargs) tuples for test assertions
        self.call_history: list[dict[str, Any]] = []

    def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return the next scripted response or raise the next scripted exception."""
        self.call_history.append({"messages": messages, "model": model, "kwargs": kwargs})

        idx = self._call_index % len(self._responses)
        self._call_index += 1
        entry = self._responses[idx]

        if isinstance(entry, Exception):
            raise entry

        usage = {
            "prompt_tokens": self._prompt_tokens,
            "completion_tokens": self._completion_tokens,
            "total_tokens": self._prompt_tokens + self._completion_tokens,
        }
        return LLMResponse(
            content=entry,
            model=model or self.default_model,
            usage=usage,
            raw=None,
        )

    @property
    def call_count(self) -> int:
        return len(self.call_history)

    def reset(self) -> None:
        """Reset call index and history (useful between test cases)."""
        self._call_index = 0
        self.call_history.clear()
