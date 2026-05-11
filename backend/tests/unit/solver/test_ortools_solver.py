import pytest

from backend.src.solver.errors import CancelledError, SolverFailedError
from backend.src.solver.models import SolverInput
from backend.src.solver.options import SolveMethodOptions
from backend.src.solver.ortools import OrToolsSolver


class CancelEvent:
    def __init__(self, is_set: bool = False) -> None:
        self._is_set = is_set

    def is_set(self) -> bool:
        return self._is_set


def make_input() -> SolverInput:
    return SolverInput(
        n=2,
        cost=[
            [0, 10, 20],
            [10, 0, 5],
            [20, 5, 0],
        ],
        demand=[0, 2, 3],
        vehicles={10: 1},
    )


def test_solves_simple_case() -> None:
    routes = OrToolsSolver().solve(
        make_input(),
        SolveMethodOptions(or_target_time_sec=1),
        None,
    )

    assert routes is not None
    assert len(routes) >= 1
    assert {node for route in routes for node in route.nodes} == {0, 1, 2}
    assert all(route.nodes[0] == 0 and route.nodes[-1] == 0 for route in routes)
    assert all(route.demand <= route.vehicle_capacity for route in routes)


def test_raises_when_capacity_is_impossible() -> None:
    solver_input = SolverInput(
        n=1,
        cost=[
            [0, 10],
            [10, 0],
        ],
        demand=[0, 11],
        vehicles={10: 1},
    )

    with pytest.raises(SolverFailedError):
        OrToolsSolver().solve(solver_input, SolveMethodOptions(or_target_time_sec=1), None)


def test_raises_on_invalid_negative_cost() -> None:
    solver_input = SolverInput(
        n=1,
        cost=[
            [0, -10],
            [10, 0],
        ],
        demand=[0, 1],
        vehicles={10: 1},
    )

    with pytest.raises(SolverFailedError):
        OrToolsSolver().solve(solver_input, SolveMethodOptions(or_target_time_sec=1), None)


def test_raises_when_cancelled_before_solving() -> None:
    with pytest.raises(CancelledError):
        OrToolsSolver().solve(
            make_input(),
            SolveMethodOptions(or_target_time_sec=1),
            CancelEvent(is_set=True),
        )