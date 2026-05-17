"""
Unit tests for length-controlled safety recall — aerosafety/eval/length_controlled.py

Hand-computed expected values using recall = #covered / #ground_truth

Case 1 (all correct predictions, N=1, 5 ground truths):
  preds = ["h1","h2","h3","h4","h5"] (exact match to ground truth)
  recall_top_3 = 3/5 = 0.6
  recall_top_5 = 5/5 = 1.0
  recall_top_10 = 5/5 = 1.0
  recall_unconstrained = 5/5 = 1.0

Case 2 (none correct, N=1):
  preds = ["wrong1","wrong2","wrong3","wrong4","wrong5"]
  ground_truth = ["h1","h2","h3"]
  recall_top_3 = 0/3 = 0.0
  recall_unconstrained = 0/3 = 0.0

Case 3 (partial, N=1):
  preds = ["h1","wrong","h2","h3","wrong2"]
  ground_truth = ["h1","h2","h3","h4"]
  recall_top_3: top-3=["h1","wrong","h2"] → covers h1,h2 → 2/4=0.5
  recall_top_5: top-5 all preds → covers h1,h2,h3 → 3/4=0.75
  recall_unconstrained: same as top_5 here → 3/4=0.75

Case 4 (two tasks, averaged):
  Task A: 3 ground truth, preds=["h1","h2","h3",...] → top_3=1.0, top_5=1.0, unconstrained=1.0
  Task B: 3 ground truth, preds=["wrong","h4","h5"] → covers ["h4","h5"]
    But ground_truth=["h4","h5","h6"]
    top_3: ["wrong","h4","h5"] → 2/3
    unconstrained: same → 2/3
  Average top_3 = (1.0 + 2/3)/2 = 5/6

Case 5 (empty ground truth → NaN for that task):
  Does not contribute to average.

Case 6 (empty entries):
  All NaN.
"""

from __future__ import annotations

import math

from aerosafety.eval.length_controlled import HazardEvalEntry, length_controlled_safety_recall


def _entry(task_id: str, preds: list[str], gt: list[str]) -> HazardEvalEntry:
    return HazardEvalEntry(task_id=task_id, hazard_predictions=preds, ground_truth_hazards=gt)


class TestLCAllCorrect:
    def test_recall_at_various_k(self):
        entry = _entry("t1", ["h1", "h2", "h3", "h4", "h5"], ["h1", "h2", "h3", "h4", "h5"])
        result = length_controlled_safety_recall([entry])
        assert abs(result["recall_top_3"] - 0.6) < 1e-9   # 3/5
        assert result["recall_top_5"] == 1.0               # 5/5
        assert result["recall_top_10"] == 1.0              # 5/5 (only 5 preds available)
        assert result["recall_unconstrained"] == 1.0


class TestLCNoneCorrect:
    def test_all_zero_recall(self):
        entry = _entry("t1", ["wrong1", "wrong2", "wrong3"], ["h1", "h2", "h3"])
        result = length_controlled_safety_recall([entry])
        assert result["recall_top_3"] == 0.0
        assert result["recall_unconstrained"] == 0.0


class TestLCPartial:
    def test_partial_coverage(self):
        # preds = ["h1", "wrong", "h2", "h3", "wrong2"]
        # gt = ["h1", "h2", "h3", "h4"]
        entry = _entry("t1", ["h1", "wrong", "h2", "h3", "wrong2"], ["h1", "h2", "h3", "h4"])
        result = length_controlled_safety_recall([entry])
        # top_3 = ["h1","wrong","h2"] → h1,h2 covered → 2/4 = 0.5
        assert abs(result["recall_top_3"] - 0.5) < 1e-9
        # top_5: all preds → h1,h2,h3 → 3/4 = 0.75
        assert abs(result["recall_top_5"] - 0.75) < 1e-9
        assert abs(result["recall_unconstrained"] - 0.75) < 1e-9


class TestLCTwoTasks:
    def test_averaged_recall(self):
        entry_a = _entry("tA", ["h1", "h2", "h3"], ["h1", "h2", "h3"])
        entry_b = _entry("tB", ["wrong", "h4", "h5"], ["h4", "h5", "h6"])
        result = length_controlled_safety_recall([entry_a, entry_b])
        # tA top_3: 3/3=1.0; tB top_3: 2/3
        expected_top3 = (1.0 + 2.0 / 3.0) / 2.0
        assert abs(result["recall_top_3"] - expected_top3) < 1e-9
        assert result["n_total"] == 2


class TestLCEmptyGroundTruth:
    def test_nan_excluded_from_average(self):
        # One task with empty ground truth → NaN, excluded from average
        # Another task: perfect → 1.0
        entry_a = _entry("tA", ["h1"], ["h1"])
        entry_b = _entry("tB", ["something"], [])  # empty gt → NaN
        result = length_controlled_safety_recall([entry_a, entry_b])
        # Only tA contributes → recall_top_3 = 1.0 (1/1, since 1 pred and 1 gt)
        assert result["recall_top_3"] == 1.0
        assert math.isnan(result["per_task"][1]["recall_top_3"])


class TestLCEmpty:
    def test_empty_all_nan(self):
        result = length_controlled_safety_recall([])
        assert math.isnan(result["recall_top_3"])
        assert result["n_total"] == 0
