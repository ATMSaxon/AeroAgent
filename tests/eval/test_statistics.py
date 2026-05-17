"""
Unit tests for statistics utilities — aerosafety/eval/statistics.py

Hand-computed expected values:

bootstrap_ci:
  Case 1 (constant sample [1,1,1]):
    mean=1.0, both CI bounds must equal 1.0
  Case 2 (binary sample [0,0,1,1]):
    mean=0.5, CI should be in [0, 1] and contain 0.5
  Case 3 (empty):
    point_estimate=NaN

calibration_data:
  Case 1 (perfectly calibrated, 2 bins):
    conf=[0.2,0.2], correct=[True,True] → bin [0.0,0.5]: mean_conf=0.2, acc=1.0
    → ECE = |1.0 - 0.2| * 2/2 = 0.8

  Case 2 (5 samples, 5 bins of width 0.2):
    conf=[0.1, 0.3, 0.5, 0.7, 0.9]
    corr=[True, False, True, True, True]
    bin [0.0,0.2): 1 sample, mean_conf=0.1, acc=1.0 → |1.0-0.1|*1/5 = 0.18
    bin [0.2,0.4): 1 sample, mean_conf=0.3, acc=0.0 → |0.0-0.3|*1/5 = 0.06
    bin [0.4,0.6): 1 sample, mean_conf=0.5, acc=1.0 → |1.0-0.5|*1/5 = 0.10
    bin [0.6,0.8): 1 sample, mean_conf=0.7, acc=1.0 → |1.0-0.7|*1/5 = 0.06
    bin [0.8,1.0]: 1 sample, mean_conf=0.9, acc=1.0 → |1.0-0.9|*1/5 = 0.02
    ECE = 0.18 + 0.06 + 0.10 + 0.06 + 0.02 = 0.42

  Case 3 (empty):
    ECE=NaN
"""

from __future__ import annotations

import math

import pytest

from aerosafety.eval.statistics import bootstrap_ci, calibration_data, mixed_effects_logistic_spec


class TestBootstrapCI:
    def test_constant_sample_ci_equals_mean(self):
        values = [1.0, 1.0, 1.0, 1.0]
        result = bootstrap_ci(values, seed=0)
        assert result["point_estimate"] == 1.0
        assert result["ci_lower"] == 1.0
        assert result["ci_upper"] == 1.0

    def test_binary_sample_ci_contains_mean(self):
        values = [0.0, 0.0, 1.0, 1.0]
        result = bootstrap_ci(values, seed=42)
        assert result["point_estimate"] == 0.5
        assert result["ci_lower"] <= 0.5 <= result["ci_upper"]
        assert 0.0 <= result["ci_lower"] <= result["ci_upper"] <= 1.0

    def test_empty_returns_nan(self):
        result = bootstrap_ci([])
        assert math.isnan(result["point_estimate"])
        assert result["n_samples"] == 0

    def test_single_sample(self):
        result = bootstrap_ci([0.75])
        assert result["point_estimate"] == 0.75
        assert result["ci_lower"] == 0.75
        assert result["ci_upper"] == 0.75

    def test_returns_n_resamples(self):
        result = bootstrap_ci([1.0, 0.0], n_resamples=500, seed=1)
        assert result["n_resamples"] == 500

    def test_confidence_level_stored(self):
        result = bootstrap_ci([1.0, 0.0], confidence_level=0.9)
        assert result["confidence_level"] == 0.9

    def test_reproducible_with_same_seed(self):
        r1 = bootstrap_ci([1.0, 0.0, 0.5, 0.75], seed=99)
        r2 = bootstrap_ci([1.0, 0.0, 0.5, 0.75], seed=99)
        assert r1["ci_lower"] == r2["ci_lower"]
        assert r1["ci_upper"] == r2["ci_upper"]


class TestCalibrationData:
    def test_ece_two_bins_high_overconfidence(self):
        # 2 samples both in [0.0, 0.5) bin, both correct
        # acc=1.0, mean_conf=0.2 → ECE = |1.0-0.2|*2/2 = 0.8
        result = calibration_data(
            confidences=[0.2, 0.2],
            correctness=[True, True],
            n_bins=2,
        )
        assert abs(result["ece"] - 0.8) < 1e-9
        assert result["n_total"] == 2

    def test_ece_five_bins(self):
        confs = [0.1, 0.3, 0.5, 0.7, 0.9]
        corrs = [True, False, True, True, True]
        result = calibration_data(confs, corrs, n_bins=5)
        expected_ece = 0.18 + 0.06 + 0.10 + 0.06 + 0.02
        assert abs(result["ece"] - expected_ece) < 1e-9

    def test_empty_returns_nan(self):
        result = calibration_data([], [], n_bins=10)
        assert math.isnan(result["ece"])
        assert result["n_total"] == 0
        assert result["bins"] == []

    def test_bins_have_expected_structure(self):
        result = calibration_data([0.5], [True], n_bins=5)
        for bin_entry in result["bins"]:
            assert "bin_lower" in bin_entry
            assert "bin_upper" in bin_entry
            assert "mean_confidence" in bin_entry
            assert "accuracy" in bin_entry
            assert "n_samples" in bin_entry

    def test_raises_on_length_mismatch(self):
        with pytest.raises(ValueError):
            calibration_data([0.5, 0.6], [True], n_bins=5)


class TestMixedEffectsSpec:
    def test_returns_required_fields(self):
        spec = mixed_effects_logistic_spec()
        assert "formula" in spec
        assert "random_effects" in spec
        assert "family" in spec
        assert spec["family"] == "binomial"
        assert "failure" in spec["formula"]

    def test_required_columns_listed(self):
        spec = mixed_effects_logistic_spec()
        assert "failure" in spec["required_columns"]
        assert "AgentType" in spec["required_columns"]
        assert "model_id" in spec["required_columns"]
        assert "task_id" in spec["required_columns"]
