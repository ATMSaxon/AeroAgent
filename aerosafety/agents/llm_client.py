"""
LLMClient — thin, no-retry wrapper over litellm.

Rules (CLAUDE.md §8.1):
  - NO automatic retries. Caller decides retry policy.
  - NO silent fallback to a different model.
  - All errors propagate as-is.
  - Returns raw completion text + usage dict so callers can log them.
"""

from __future__ import annotations

from typing import Any


class LLMResponse:
    """Typed container for a single LLM completion."""

    def __init__(
        self,
        content: str,
        model: str,
        usage: dict[str, int],
        raw: Any,
    ) -> None:
        self.content = content
        self.model = model
        # usage keys: "prompt_tokens", "completion_tokens", "total_tokens"
        self.usage = usage
        self.raw = raw  # the full litellm response object

    def token_usage_dict(self) -> dict[str, int]:
        """Return usage dict keyed as AgentTrace.token_usage expects."""
        return {
            "prompt": self.usage.get("prompt_tokens", 0),
            "completion": self.usage.get("completion_tokens", 0),
            "total": self.usage.get("total_tokens", 0),
        }


class LLMClient:
    """
    Thin wrapper over litellm.completion.

    Parameters
    ----------
    default_model:
        litellm model string, e.g. "openai/gpt-4o", "anthropic/claude-opus-4-7".
    default_kwargs:
        Extra kwargs forwarded to litellm.completion on every call (e.g.
        temperature=0.0 for deterministic eval).
    """

    def __init__(
        self,
        default_model: str,
        **default_kwargs: Any,
    ) -> None:
        self.default_model = default_model
        self._default_kwargs = default_kwargs

    def complete(
        self,
        messages: list[dict[str, Any]],
        model: str | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Send *messages* to the LLM and return an LLMResponse.

        Parameters
        ----------
        messages:
            OpenAI-format message list (role/content dicts).
        model:
            Override the default model. Pass None to use default.
        **kwargs:
            Override any default_kwargs for this call.

        Returns
        -------
        LLMResponse

        Raises
        ------
        Any litellm exception propagates — no retry, no fallback.
        """
        try:
            import litellm  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "litellm is required for LLMClient. Install with: pip install litellm"
            ) from exc

        resolved_model = model or self.default_model
        call_kwargs = {**self._default_kwargs, **kwargs}

        response = litellm.completion(
            model=resolved_model,
            messages=messages,
            **call_kwargs,
        )

        content = response.choices[0].message.content or ""
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

        return LLMResponse(
            content=content,
            model=resolved_model,
            usage=usage,
            raw=response,
        )
