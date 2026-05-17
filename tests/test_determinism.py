"""Tests for aerosafety.determinism."""

import os

import pytest

from aerosafety.determinism import assert_eval_mode, lock_seeds, prompt_hash


def test_lock_seeds_runs_without_error() -> None:
    lock_seeds(42)  # must not raise


def test_prompt_hash_is_stable() -> None:
    msgs = [{"role": "user", "content": "hello"}]
    sys = "You are a helpful assistant."
    h1 = prompt_hash(msgs, sys)
    h2 = prompt_hash(msgs, sys)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_prompt_hash_changes_with_content() -> None:
    msgs = [{"role": "user", "content": "hello"}]
    h1 = prompt_hash(msgs, "system A")
    h2 = prompt_hash(msgs, "system B")
    assert h1 != h2


def test_assert_eval_mode_raises_when_not_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AEROSAFETY_EVAL_MODE", raising=False)
    with pytest.raises(RuntimeError, match="AEROSAFETY_EVAL_MODE"):
        assert_eval_mode()


def test_assert_eval_mode_passes_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AEROSAFETY_EVAL_MODE", "1")
    assert_eval_mode()  # must not raise
