"""
Statistical analysis utilities — proposal §19.

Implements:
- bootstrap_ci: 95% bootstrap CIs (1000 resamples by default)
- wilcoxon_paired_test: Wilcoxon signed-rank test for paired comparisons
- mixed_effects_logistic_spec: specification (not fit) for statsmodels GLMM
- calibration_data: ECE + reliability diagram data (no matplotlib)

All functions return plain Python dicts — no side effects, no plotting.
"""

from __future__ import annotations

import math
import random
from typing import Callable, Sequence


# ---------------------------------------------------------------------------
# Bootstrap CI
# ---------------------------------------------------------------------------

def bootstrap_ci(
    values: Sequence[float],
    statistic: Callable[[list[float]], float] = lambda xs: sum(xs) / len(xs),
    n_resamples: int = 1000,
    confidence_level: float = 0.95,
    seed: int | None = 42,
) -> dict:
    """
    Compute a bootstrap confidence interval for a scalar statistic.

    Parameters
    ----------
    values           : observed sample
    statistic        : function from list[float] → float. Default: mean.
    n_resamples      : number of bootstrap resamples (default 1000)
    confidence_level : e.g. 0.95 for a 95% CI
    seed             : random seed for reproducibility (default 42)

    Returns
    -------
    dict with keys:
        point_estimate : float   statistic applied to original sample
        ci_lower       : float
        ci_upper       : float
        confidence_level : float
        n_resamples    : int
        n_samples      : int
    """
    if not values:
        return {
            "point_estimate": float("nan"),
            "ci_lower": float("nan"),
            "ci_upper": float("nan"),
            "confidence_level": confidence_level,
            "n_resamples": n_resamples,
            "n_samples": 0,
        }

    rng = random.Random(seed)
    vals = list(values)
    n = len(vals)

    point_estimate = statistic(vals)

    bootstrap_stats = []
    for _ in range(n_resamples):
        resample = [rng.choice(vals) for _ in range(n)]
        bootstrap_stats.append(statistic(resample))

    bootstrap_stats.sort()
    alpha = 1.0 - confidence_level
    lower_idx = int(math.floor(alpha / 2 * n_resamples))
    upper_idx = int(math.ceil((1.0 - alpha / 2) * n_resamples)) - 1
    lower_idx = max(0, lower_idx)
    upper_idx = min(n_resamples - 1, upper_idx)

    return {
        "point_estimate": point_estimate,
        "ci_lower": bootstrap_stats[lower_idx],
        "ci_upper": bootstrap_stats[upper_idx],
        "confidence_level": confidence_level,
        "n_resamples": n_resamples,
        "n_samples": n,
    }


# ---------------------------------------------------------------------------
# Wilcoxon paired signed-rank test
# ---------------------------------------------------------------------------

def wilcoxon_paired_test(
    a: Sequence[float],
    b: Sequence[float],
) -> dict:
    """
    Wilcoxon signed-rank test for paired metric comparisons (proposal §19.4).

    Uses scipy.stats.wilcoxon. Returns p-value and test statistic.
    Falls back gracefully if scipy is not installed (raises ImportError with
    an informative message).

    Parameters
    ----------
    a, b : paired sequences of per-task metric values (same length)

    Returns
    -------
    dict with keys:
        statistic : float
        p_value   : float
        n_pairs   : int
        method    : str ("wilcoxon_signed_rank")
    """
    if len(a) != len(b):
        raise ValueError(f"a ({len(a)}) and b ({len(b)}) must have the same length.")

    try:
        from scipy import stats as scipy_stats
    except ImportError as exc:
        raise ImportError(
            "scipy is required for wilcoxon_paired_test. Install with: pip install scipy"
        ) from exc

    result = scipy_stats.wilcoxon(a, b, alternative="two-sided")
    return {
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "n_pairs": len(a),
        "method": "wilcoxon_signed_rank",
    }


# ---------------------------------------------------------------------------
# Mixed-effects logistic regression specification
# ---------------------------------------------------------------------------

def mixed_effects_logistic_spec() -> dict:
    """
    Return the statsmodels formula and random-effects specification for
    the mixed-effects logistic regression in proposal §19.2:

      logit(P(failure)) = beta_0
                        + beta_1 * AgentType
                        + beta_2 * TaskFamily
                        + beta_3 * RiskLevel
                        + beta_4 * ToolUse
                        + beta_5 * VerifierUse
                        + u_model + u_task

    Returns a dict describing how to fit this with statsmodels BinomialBayesMixedGLM
    or MixedLM with logit link.

    NOTE: This returns the specification only. Actual fitting requires a
    pandas DataFrame with the described columns.
    """
    return {
        "formula": (
            "failure ~ AgentType + TaskFamily + RiskLevel + ToolUse + VerifierUse"
        ),
        "random_effects": ["model_id", "task_id"],
        "family": "binomial",
        "link": "logit",
        "required_columns": [
            "failure",       # bool: 1 if predicted != gold
            "AgentType",     # categorical: e.g. "DirectLLM", "RAG", "ToolAugmented"
            "TaskFamily",    # categorical: e.g. "Weather", "NOTAM", "WakeVortex"
            "RiskLevel",     # ordinal: "Low"|"Medium"|"High"|"Critical"
            "ToolUse",       # bool: 1 if agent used any tools
            "VerifierUse",   # bool: 1 if agent used verifier
            "model_id",      # random effect grouping
            "task_id",       # random effect grouping
        ],
        "data_library": "polars",
        "statsmodels_class": "statsmodels.formula.api.mixedlm or BinomialBayesMixedGLM",
        "note": (
            "PARTIAL IMPLEMENTATION: formula and spec are defined. "
            "Build the polars DataFrame from EvalView records, convert to numpy/pandas "
            "only at the statsmodels boundary. Fit with statsmodels when data is available."
        ),
    }


# ---------------------------------------------------------------------------
# Calibration analysis
# ---------------------------------------------------------------------------

def calibration_data(
    confidences: Sequence[float],
    correctness: Sequence[bool],
    n_bins: int = 10,
) -> dict:
    """
    Compute Expected Calibration Error (ECE) and reliability diagram data.

    Does NOT produce matplotlib output — returns raw bin data for external plotting.

    Parameters
    ----------
    confidences : per-task predicted confidence values in [0, 1]
    correctness : per-task bool indicating whether prediction was correct
    n_bins      : number of equal-width bins (default 10)

    Returns
    -------
    dict with keys:
        ece      : float  Expected Calibration Error
        bins     : list[dict]  per-bin data for reliability diagram
            bin_lower, bin_upper, mean_confidence, accuracy, n_samples
        n_total  : int
    """
    if len(confidences) != len(correctness):
        raise ValueError("confidences and correctness must have the same length.")

    if not confidences:
        return {"ece": float("nan"), "bins": [], "n_total": 0}

    bin_edges = [i / n_bins for i in range(n_bins + 1)]
    bins_data = []

    ece = 0.0
    n_total = len(confidences)

    for i in range(n_bins):
        lower = bin_edges[i]
        upper = bin_edges[i + 1]
        in_bin = [
            (c, int(corr))
            for c, corr in zip(confidences, correctness)
            if lower <= c < upper or (i == n_bins - 1 and c == 1.0)
        ]
        if not in_bin:
            bins_data.append(
                {
                    "bin_lower": lower,
                    "bin_upper": upper,
                    "mean_confidence": (lower + upper) / 2,
                    "accuracy": float("nan"),
                    "n_samples": 0,
                }
            )
            continue

        mean_conf = sum(c for c, _ in in_bin) / len(in_bin)
        acc = sum(corr for _, corr in in_bin) / len(in_bin)
        n_bin = len(in_bin)

        ece += (n_bin / n_total) * abs(acc - mean_conf)

        bins_data.append(
            {
                "bin_lower": lower,
                "bin_upper": upper,
                "mean_confidence": mean_conf,
                "accuracy": acc,
                "n_samples": n_bin,
            }
        )

    return {
        "ece": ece,
        "bins": bins_data,
        "n_total": n_total,
    }
