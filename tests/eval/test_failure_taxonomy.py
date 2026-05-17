"""
Unit tests for failure taxonomy — aerosafety/eval/failure_taxonomy.py

Validates:
1. All 7 categories exist
2. Each category has exactly 5 failure modes
3. All failure modes are uniquely named
4. CATEGORY_MODES covers all categories
"""

from __future__ import annotations

from aerosafety.eval.failure_taxonomy import (
    CATEGORY_MODES,
    FailureCategory,
    FailureMode,
)


class TestFailureCategories:
    def test_seven_categories(self):
        assert len(FailureCategory) == 7

    def test_expected_categories_present(self):
        expected = {
            "Evidence", "Temporal", "Spatial",
            "Numerical", "Regulatory", "ToolUse", "Decision",
        }
        actual = {c.value for c in FailureCategory}
        assert actual == expected


class TestFailureModes:
    def test_all_modes_unique(self):
        values = [m.value for m in FailureMode]
        assert len(values) == len(set(values))

    def test_total_mode_count(self):
        # 7 categories × 5 modes = 35
        assert len(FailureMode) == 35


class TestCategoryModes:
    def test_all_categories_covered(self):
        assert set(CATEGORY_MODES.keys()) == set(FailureCategory)

    def test_each_category_has_five_modes(self):
        for category, modes in CATEGORY_MODES.items():
            assert len(modes) == 5, f"{category} should have 5 modes, got {len(modes)}"

    def test_all_modes_in_category_map(self):
        all_mapped = {m for modes in CATEGORY_MODES.values() for m in modes}
        assert all_mapped == set(FailureMode)

    def test_evidence_modes(self):
        modes = CATEGORY_MODES[FailureCategory.EVIDENCE]
        assert FailureMode.HALLUCINATED_EVIDENCE in modes
        assert FailureMode.UNSUPPORTED_CLAIM in modes
        assert FailureMode.CONTRADICTION_WITH_EVIDENCE in modes

    def test_decision_modes(self):
        modes = CATEGORY_MODES[FailureCategory.DECISION]
        assert FailureMode.UNSAFE_RECOMMENDATION in modes
        assert FailureMode.OVERCONFIDENT_WRONG_ANSWER in modes
        assert FailureMode.MISSING_ESCALATION in modes

    def test_tool_use_modes(self):
        modes = CATEGORY_MODES[FailureCategory.TOOL_USE]
        assert FailureMode.MISSING_REQUIRED_TOOL_CALL in modes
        assert FailureMode.WRONG_TOOL_SELECTED in modes
        assert FailureMode.WRONG_TOOL_INPUT in modes
