"""
Unit tests for aerosafety/training/splits.py — test-split leakage prevention.

The load-bearing safety test is test_no_test_split_leakage which verifies that
attempting to build a dataset with a test-split card raises SplitLeakageError.
"""

from __future__ import annotations

import pytest

from aerosafety.io import TaskCard, TaskProvenance
from aerosafety.training.splits import (
    SplitLeakageError,
    assert_no_test_leakage,
    filter_train_only,
)


def _card(task_id: str, split: str | None) -> TaskCard:
    return TaskCard(
        task_id=task_id,
        family="notam_compliance",
        task_type="A",
        prompt="[SYNTHETIC] Test.",
        gold_decision="NO-GO",
        required_safety_constraints=["c1"],
        severity="High",
        escalation_required=False,
        provenance=TaskProvenance(source="SYNTHETIC", generation_rule="unit test"),
        split=split,
    )


class TestFilterTrainOnly:
    def test_excludes_test_split(self) -> None:
        cards = [_card("T1", "dev"), _card("T2", "test"), _card("T3", "dev")]
        result = filter_train_only(cards)
        ids = [c.task_id for c in result]
        assert "T2" not in ids
        assert set(ids) == {"T1", "T3"}

    def test_includes_dev(self) -> None:
        cards = [_card("T1", "dev")]
        assert len(filter_train_only(cards)) == 1

    def test_includes_none_split(self) -> None:
        # split=None means unlabelled; treated as dev (not frozen test)
        cards = [_card("T1", None)]
        assert len(filter_train_only(cards)) == 1

    def test_empty_input(self) -> None:
        assert filter_train_only([]) == []

    def test_all_test_returns_empty(self) -> None:
        cards = [_card("T1", "test"), _card("T2", "test")]
        assert filter_train_only(cards) == []


class TestAssertNoTestLeakage:
    def test_passes_for_dev_only(self) -> None:
        cards = [_card("T1", "dev"), _card("T2", "dev")]
        assert_no_test_leakage(cards)   # must not raise

    def test_passes_for_empty(self) -> None:
        assert_no_test_leakage([])   # must not raise

    def test_passes_for_none_split(self) -> None:
        cards = [_card("T1", None)]
        assert_no_test_leakage(cards)  # must not raise

    # -----------------------------------------------------------------------
    # LOAD-BEARING SAFETY TEST
    # -----------------------------------------------------------------------
    def test_no_test_split_leakage(self) -> None:
        """
        Attempting to include a test-split card in a training dataset MUST raise
        SplitLeakageError.  This is the hard-error guard per CLAUDE.md §2.3.
        """
        cards = [
            _card("DEV-001", "dev"),
            _card("TEST-001", "test"),   # intruder — must be caught
            _card("DEV-002", "dev"),
        ]
        with pytest.raises(SplitLeakageError) as exc_info:
            assert_no_test_leakage(cards)
        assert "TEST-001" in str(exc_info.value)
        assert "CLAUDE.md §2.3" in str(exc_info.value)

    def test_error_message_lists_all_leaking_ids(self) -> None:
        cards = [_card("TEST-A", "test"), _card("TEST-B", "test"), _card("DEV-1", "dev")]
        with pytest.raises(SplitLeakageError) as exc_info:
            assert_no_test_leakage(cards)
        msg = str(exc_info.value)
        assert "TEST-A" in msg
        assert "TEST-B" in msg

    def test_error_is_raised_before_any_output_written(self, tmp_path) -> None:
        """
        The dataset_builder must call assert_no_test_leakage before writing output.
        Verify that no file is created when leakage is detected.
        """
        from aerosafety.training.dataset_builder import build_sft_dataset

        out = tmp_path / "sft.jsonl"
        cards = [_card("TEST-001", "test")]  # test-only input — should raise

        with pytest.raises(SplitLeakageError):
            build_sft_dataset(task_cards=cards, output_path=out)

        assert not out.exists(), "Output file must NOT be written when leakage is detected"
