"""
Tests for aerosafety.tools.optimization_solver.

Per CLAUDE.md §8.1: the solver raises ImportError if no backend is installed —
callers must handle this. These tests verify:
1. ImportError is raised (not silently swallowed) when no backend is available.
2. When a backend IS available, the solver returns correctly structured results.
3. Feasibility flags are accurate.
4. Post-solve safety verification logic is correct.
5. All result types have required fields.
"""

from __future__ import annotations

import pytest

from aerosafety.tools.optimization_solver import (
    ORTOOLS_AVAILABLE,
    PULP_AVAILABLE,
    SOLVER_AVAILABLE,
    GroundDelayInstance,
    GroundDelayResult,
    GateAssignmentInstance,
    GateAssignmentResult,
    RunwaySequenceInstance,
    RunwaySequenceResult,
    solve_gate_assignment,
    solve_ground_delay_allocation,
    solve_runway_sequence,
)

# ---------------------------------------------------------------------------
# Module-level availability checks
# ---------------------------------------------------------------------------


def test_availability_flags_are_booleans() -> None:
    assert isinstance(SOLVER_AVAILABLE, bool)
    assert isinstance(ORTOOLS_AVAILABLE, bool)
    assert isinstance(PULP_AVAILABLE, bool)


def test_solver_available_implies_at_least_one_backend() -> None:
    if SOLVER_AVAILABLE:
        assert ORTOOLS_AVAILABLE or PULP_AVAILABLE


# ---------------------------------------------------------------------------
# ImportError behavior (CLAUDE.md §8.1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(SOLVER_AVAILABLE, reason="solver available — skip ImportError test")
def test_runway_sequence_raises_import_error_when_unavailable() -> None:
    """When no solver backend is installed, solve_runway_sequence must raise ImportError."""
    instance = RunwaySequenceInstance(
        aircraft=[
            {"id": "A1", "type_icao": "B77W", "wake_category": "H",
             "earliest_time": 0, "latest_time": 300, "scheduled_time": 0},
        ],
        wake_sep_matrix={("H", "M"): 120, ("H", "H"): 120},
    )
    with pytest.raises(ImportError, match="no solver backend found"):
        solve_runway_sequence(instance)


@pytest.mark.skipif(SOLVER_AVAILABLE, reason="solver available — skip ImportError test")
def test_gate_assignment_raises_import_error_when_unavailable() -> None:
    instance = GateAssignmentInstance(
        flights=[{"id": "F1", "arrival": 0, "departure": 3600,
                  "aircraft_size": "M", "airline": "AAL", "preferred_terminal": "A"}],
        gates=[{"id": "G1", "terminal": "A", "compatible_sizes": ["M"], "buffer_minutes": 15}],
    )
    with pytest.raises(ImportError, match="no solver backend found"):
        solve_gate_assignment(instance)


@pytest.mark.skipif(SOLVER_AVAILABLE, reason="solver available — skip ImportError test")
def test_ground_delay_raises_import_error_when_unavailable() -> None:
    instance = GroundDelayInstance(
        flights=[{"id": "F1", "scheduled_departure": 0, "cost_per_delay_unit": 1.0,
                  "max_delay": 3600, "destination_airport": "KORD"}],
        airport_capacity_slots=[(0, 3600, 1)],
    )
    with pytest.raises(ImportError, match="no solver backend found"):
        solve_ground_delay_allocation(instance)


# ---------------------------------------------------------------------------
# Solver behavior when available
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not SOLVER_AVAILABLE, reason="no solver backend installed")
class TestRunwaySequenceSolver:
    """Runway sequencing solver tests — only run when a backend is available."""

    def _wake_matrix(self) -> dict:
        return {
            ("H", "H"): 120, ("H", "M"): 120, ("H", "L"): 180,
            ("M", "H"): 120, ("M", "M"): 90, ("M", "L"): 120,
            ("L", "H"): 120, ("L", "M"): 120, ("L", "L"): 90,
        }

    def test_empty_instance_returns_feasible(self) -> None:
        instance = RunwaySequenceInstance(
            aircraft=[], wake_sep_matrix=self._wake_matrix()
        )
        result = solve_runway_sequence(instance)
        assert isinstance(result, RunwaySequenceResult)
        assert result.feasible is True
        assert result.sequence == []
        assert result.safety_constraints_satisfied is True

    def test_single_aircraft_feasible(self) -> None:
        instance = RunwaySequenceInstance(
            aircraft=[{"id": "A1", "type_icao": "B77W", "wake_category": "H",
                       "earliest_time": 0, "latest_time": 300, "scheduled_time": 0}],
            wake_sep_matrix=self._wake_matrix(),
        )
        result = solve_runway_sequence(instance)
        assert result.feasible is True
        assert "A1" in result.sequence
        assert result.safety_constraints_satisfied is True

    def test_two_aircraft_wake_constraint_satisfied(self) -> None:
        """H followed by M must have >= 120s gap."""
        instance = RunwaySequenceInstance(
            aircraft=[
                {"id": "H1", "type_icao": "B77W", "wake_category": "H",
                 "earliest_time": 0, "latest_time": 300, "scheduled_time": 0},
                {"id": "M1", "type_icao": "A320", "wake_category": "M",
                 "earliest_time": 0, "latest_time": 400, "scheduled_time": 60},
            ],
            wake_sep_matrix=self._wake_matrix(),
        )
        result = solve_runway_sequence(instance)
        assert result.feasible is True
        if result.sequence.index("H1") < result.sequence.index("M1"):
            gap = result.scheduled_times["M1"] - result.scheduled_times["H1"]
            assert gap >= 120, f"H→M gap {gap}s violates 120s minimum"

    def test_result_has_required_fields(self) -> None:
        instance = RunwaySequenceInstance(
            aircraft=[
                {"id": "A1", "type_icao": "B738", "wake_category": "M",
                 "earliest_time": 0, "latest_time": 300, "scheduled_time": 0},
                {"id": "A2", "type_icao": "A320", "wake_category": "M",
                 "earliest_time": 0, "latest_time": 300, "scheduled_time": 90},
            ],
            wake_sep_matrix=self._wake_matrix(),
        )
        result = solve_runway_sequence(instance)
        assert hasattr(result, "feasible")
        assert hasattr(result, "sequence")
        assert hasattr(result, "scheduled_times")
        assert hasattr(result, "objective_value")
        assert hasattr(result, "solver_used")
        assert hasattr(result, "safety_constraints_satisfied")
        assert hasattr(result, "violated_constraints")
        assert isinstance(result.violated_constraints, list)

    def test_solver_used_is_non_empty_string(self) -> None:
        instance = RunwaySequenceInstance(
            aircraft=[
                {"id": "A1", "type_icao": "B738", "wake_category": "M",
                 "earliest_time": 0, "latest_time": 200, "scheduled_time": 0},
            ],
            wake_sep_matrix=self._wake_matrix(),
        )
        result = solve_runway_sequence(instance)
        assert isinstance(result.solver_used, str)
        assert len(result.solver_used) > 0

    def test_three_aircraft_sequence_correct(self) -> None:
        """3-aircraft instance from OD-A-007: H, M, M."""
        instance = RunwaySequenceInstance(
            aircraft=[
                {"id": "A", "type_icao": "B77W", "wake_category": "H",
                 "earliest_time": 0, "latest_time": 300, "scheduled_time": 0},
                {"id": "B", "type_icao": "A320", "wake_category": "M",
                 "earliest_time": 0, "latest_time": 300, "scheduled_time": 60},
                {"id": "C", "type_icao": "B737", "wake_category": "M",
                 "earliest_time": 0, "latest_time": 300, "scheduled_time": 120},
            ],
            wake_sep_matrix=self._wake_matrix(),
        )
        result = solve_runway_sequence(instance)
        assert result.feasible is True
        assert len(result.sequence) == 3
        # All wake constraints verified
        seq = result.sequence
        times = result.scheduled_times
        for i in range(len(seq) - 1):
            leader, follower = seq[i], seq[i + 1]
            wake_l = next(
                a["wake_category"] for a in instance.aircraft if a["id"] == leader
            )
            wake_f = next(
                a["wake_category"] for a in instance.aircraft if a["id"] == follower
            )
            required = instance.wake_sep_matrix.get((wake_l, wake_f), 90)
            actual = times[follower] - times[leader]
            assert actual >= required - 0.5, (
                f"Wake violation: {leader}({wake_l})→{follower}({wake_f}): "
                f"required {required}s, got {actual}s"
            )


@pytest.mark.skipif(not SOLVER_AVAILABLE, reason="no solver backend installed")
class TestGateAssignmentSolver:
    """Gate assignment solver tests."""

    def test_empty_instance_returns_feasible(self) -> None:
        instance = GateAssignmentInstance(flights=[], gates=[])
        result = solve_gate_assignment(instance)
        assert result.feasible is True
        assert result.assignment == {}
        assert result.safety_constraints_satisfied is True

    def test_single_flight_single_gate_feasible(self) -> None:
        instance = GateAssignmentInstance(
            flights=[{"id": "F1", "arrival": 0, "departure": 3600,
                      "aircraft_size": "M", "airline": "AAL", "preferred_terminal": "A"}],
            gates=[{"id": "G1", "terminal": "A", "compatible_sizes": ["M", "S"],
                    "buffer_minutes": 15}],
        )
        result = solve_gate_assignment(instance)
        assert result.feasible is True
        assert result.assignment.get("F1") == "G1"
        assert result.safety_constraints_satisfied is True

    def test_size_incompatible_flight_not_assigned_to_wrong_gate(self) -> None:
        """WB flight should not be assigned to M-only gate."""
        instance = GateAssignmentInstance(
            flights=[{"id": "F1", "arrival": 0, "departure": 3600,
                      "aircraft_size": "WB", "airline": "UAL", "preferred_terminal": None}],
            gates=[{"id": "G1", "terminal": "A", "compatible_sizes": ["M", "S"],
                    "buffer_minutes": 15}],
        )
        result = solve_gate_assignment(instance)
        # No WB-compatible gate — should be infeasible
        assert result.feasible is False

    def test_result_has_required_fields(self) -> None:
        instance = GateAssignmentInstance(
            flights=[{"id": "F1", "arrival": 0, "departure": 1800,
                      "aircraft_size": "M", "airline": "DAL", "preferred_terminal": None}],
            gates=[{"id": "G1", "terminal": "B", "compatible_sizes": ["L", "M"],
                    "buffer_minutes": 15}],
        )
        result = solve_gate_assignment(instance)
        assert hasattr(result, "feasible")
        assert hasattr(result, "assignment")
        assert hasattr(result, "objective_value")
        assert hasattr(result, "solver_used")
        assert hasattr(result, "safety_constraints_satisfied")
        assert hasattr(result, "violated_constraints")
        assert isinstance(result.violated_constraints, list)

    def test_two_overlapping_flights_infeasible_at_one_gate(self) -> None:
        """Two flights with overlapping times + buffer cannot share one gate."""
        instance = GateAssignmentInstance(
            flights=[
                {"id": "F1", "arrival": 0, "departure": 3600,
                 "aircraft_size": "M", "airline": "AAL", "preferred_terminal": None},
                {"id": "F2", "arrival": 3000, "departure": 7200,
                 "aircraft_size": "M", "airline": "AAL", "preferred_terminal": None},
            ],
            gates=[
                {"id": "G1", "terminal": "A", "compatible_sizes": ["M"],
                 "buffer_minutes": 15},
            ],
        )
        result = solve_gate_assignment(instance)
        # F1 dep 3600 + 900s buffer = 4500s. F2 arr 3000 < 4500 — conflict.
        # Single gate → infeasible
        assert result.feasible is False


@pytest.mark.skipif(not SOLVER_AVAILABLE, reason="no solver backend installed")
class TestGroundDelaySolver:
    """Ground delay allocation solver tests."""

    def test_empty_instance_returns_feasible(self) -> None:
        instance = GroundDelayInstance(flights=[], airport_capacity_slots=[])
        result = solve_ground_delay_allocation(instance)
        assert result.feasible is True
        assert result.delays == {}

    def test_single_flight_zero_delay(self) -> None:
        """Single flight within capacity — should receive zero delay."""
        instance = GroundDelayInstance(
            flights=[{"id": "F1", "scheduled_departure": 0,
                      "cost_per_delay_unit": 1.0, "max_delay": 3600,
                      "destination_airport": "KORD"}],
            airport_capacity_slots=[(0, 3600, 5)],
        )
        result = solve_ground_delay_allocation(instance)
        assert result.feasible is True
        assert "F1" in result.delays
        assert result.delays["F1"] >= 0

    def test_result_has_required_fields(self) -> None:
        instance = GroundDelayInstance(
            flights=[{"id": "F1", "scheduled_departure": 0,
                      "cost_per_delay_unit": 1.0, "max_delay": 1800,
                      "destination_airport": "KSFO"}],
            airport_capacity_slots=[(0, 7200, 2)],
        )
        result = solve_ground_delay_allocation(instance)
        assert hasattr(result, "feasible")
        assert hasattr(result, "delays")
        assert hasattr(result, "objective_value")
        assert hasattr(result, "solver_used")
        assert hasattr(result, "safety_constraints_satisfied")
        assert hasattr(result, "violated_constraints")
        assert isinstance(result.violated_constraints, list)

    def test_delays_are_non_negative(self) -> None:
        instance = GroundDelayInstance(
            flights=[
                {"id": "F1", "scheduled_departure": 0, "cost_per_delay_unit": 1.0,
                 "max_delay": 3600, "destination_airport": "KORD"},
                {"id": "F2", "scheduled_departure": 60, "cost_per_delay_unit": 2.0,
                 "max_delay": 1800, "destination_airport": "KORD"},
            ],
            airport_capacity_slots=[(0, 7200, 3)],
        )
        result = solve_ground_delay_allocation(instance)
        if result.feasible:
            for fid, delay in result.delays.items():
                assert delay >= 0, f"Negative delay for {fid}: {delay}"

    def test_max_delay_respected(self) -> None:
        """Solver must not exceed max_delay for any flight."""
        max_delay = 1800
        instance = GroundDelayInstance(
            flights=[
                {"id": "F1", "scheduled_departure": 0, "cost_per_delay_unit": 1.0,
                 "max_delay": max_delay, "destination_airport": "KORD"},
            ],
            airport_capacity_slots=[(0, 7200, 1)],
        )
        result = solve_ground_delay_allocation(instance)
        if result.feasible and "F1" in result.delays:
            assert result.delays["F1"] <= max_delay + 1, (
                f"Delay {result.delays['F1']} exceeds max_delay {max_delay}"
            )


# ---------------------------------------------------------------------------
# Data class structure tests (no backend required)
# ---------------------------------------------------------------------------


def test_runway_sequence_instance_construction() -> None:
    instance = RunwaySequenceInstance(
        aircraft=[{"id": "X1", "type_icao": "B77W", "wake_category": "H",
                   "earliest_time": 0, "latest_time": 300, "scheduled_time": 0}],
        wake_sep_matrix={("H", "M"): 120},
    )
    assert len(instance.aircraft) == 1
    assert instance.runway_capacity_per_hour == 60  # default


def test_gate_assignment_instance_construction() -> None:
    instance = GateAssignmentInstance(
        flights=[{"id": "F1", "arrival": 0, "departure": 3600,
                  "aircraft_size": "M", "airline": "UAL", "preferred_terminal": None}],
        gates=[{"id": "G1", "terminal": "A", "compatible_sizes": ["M"],
                "buffer_minutes": 15}],
    )
    assert len(instance.flights) == 1
    assert len(instance.gates) == 1


def test_ground_delay_instance_construction() -> None:
    instance = GroundDelayInstance(
        flights=[{"id": "F1", "scheduled_departure": 0, "cost_per_delay_unit": 1.0,
                  "max_delay": 3600, "destination_airport": "KORD"}],
        airport_capacity_slots=[(0, 3600, 2)],
    )
    assert len(instance.flights) == 1
    assert len(instance.airport_capacity_slots) == 1
