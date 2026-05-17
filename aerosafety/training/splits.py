"""
Test-split leakage prevention for training dataset construction.

Per CLAUDE.md §2.3 and task spec: including a test-split TaskCard in any
training output is a HARD ERROR, not a warning. Any attempt to build SFT, DPO,
or Verifier datasets that include test-split cards raises SplitLeakageError
immediately, before any output is written.

Usage
-----
    from aerosafety.training.splits import filter_train_only, assert_no_test_leakage

    train_cards = filter_train_only(all_cards)              # returns only dev cards
    assert_no_test_leakage(train_cards)                     # idempotent safety check
"""

from __future__ import annotations

from aerosafety.io import TaskCard


class SplitLeakageError(Exception):
    """
    Raised when a test-split TaskCard is detected in a training dataset.

    Per CLAUDE.md §2.3, evaluation contamination is prohibited.  This is a
    hard error: no training output is written when this exception is raised.
    """


def filter_train_only(cards: list[TaskCard]) -> list[TaskCard]:
    """
    Return only cards whose split is NOT "test".

    Cards with split=None are treated as dev (they were not assigned a frozen
    test-set label).  Cards with split="test" are excluded.

    Parameters
    ----------
    cards:
        All TaskCards loaded from task directories.

    Returns
    -------
    Filtered list containing only non-test cards.
    """
    return [c for c in cards if c.split != "test"]


def assert_no_test_leakage(cards: list[TaskCard]) -> None:
    """
    Raise SplitLeakageError if any card in `cards` has split=="test".

    This is the second line of defence — call it immediately before writing
    any training JSONL to disk so that even if filter_train_only was skipped
    the output is never written.

    Parameters
    ----------
    cards:
        The card list that is about to be written to a training dataset.

    Raises
    ------
    SplitLeakageError
        If one or more cards have split == "test".
    """
    leaking = [c.task_id for c in cards if c.split == "test"]
    if leaking:
        raise SplitLeakageError(
            f"TEST-SPLIT LEAKAGE DETECTED — {len(leaking)} test card(s) found in "
            f"training dataset input. task_ids: {leaking}. "
            "Per CLAUDE.md §2.3 this is a hard error. No output has been written."
        )
