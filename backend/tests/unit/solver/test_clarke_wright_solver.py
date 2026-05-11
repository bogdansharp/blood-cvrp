import pytest

from backend.src.solver.clarke_wright_solver import ClarkeWrightSolver
from backend.src.solver.errors import CancelledError, SolverFailedError
from backend.src.solver.models import SolverInput
from backend.src.solver.options import SolveMethodOptions


class CancelEvent:
    def __init__(self, is_set: bool = False) -> None:
        self._is_set = is_set

    def is_set(self) -> bool:
        return self._is_set


def make_input(
    demand: list[int] | None = None,
    vehicles: dict[int, int] | None = None,
) -> SolverInput:
    return SolverInput(
        n=2,
        cost=[
            [0, 10, 20],
            [10, 0, 5],
            [20, 5, 0],
        ],
        demand=demand or [0, 2, 3],
        vehicles=vehicles or {10: 2},
    )


def test_solves_simple_case() -> None:
    solver = ClarkeWrightSolver()

    routes = solver.solve(make_input(), SolveMethodOptions(), None)

    assert routes is not None
    assert len(routes) == 1
    assert routes[0].nodes[0] == 0
    assert routes[0].nodes[-1] == 0
    assert set(routes[0].nodes) == {0, 1, 2}
    assert routes[0].demand == 5
    assert routes[0].vehicle_capacity == 10


def test_splits_large_customer_demand_across_available_vehicles() -> None:
    solver_input = SolverInput(
        n=1,
        cost=[
            [0, 10],
            [10, 0],
        ],
        demand=[0, 15],
        vehicles={10: 2},
    )

    routes = ClarkeWrightSolver().solve(solver_input, SolveMethodOptions(), None)

    assert routes is not None
    assert len(routes) == 2
    assert sum(route.demand for route in routes) == 15
    assert all(route.vehicle_capacity == 10 for route in routes)
    assert all(route.nodes[0] == 0 and route.nodes[-1] == 0 for route in routes)


def test_raises_when_not_enough_vehicle_capacity() -> None:
    solver_input = SolverInput(
        n=1,
        cost=[
            [0, 10],
            [10, 0],
        ],
        demand=[0, 15],
        vehicles={10: 1},
    )

    with pytest.raises(SolverFailedError):
        ClarkeWrightSolver().solve(solver_input, SolveMethodOptions(), None)

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
        ClarkeWrightSolver().solve(solver_input, SolveMethodOptions(), None)


def test_raises_when_cost_limit_blocks_single_customer_route() -> None:
    options = SolveMethodOptions(cost_limit=5)

    with pytest.raises(SolverFailedError):
        ClarkeWrightSolver().solve(make_input(), options, None)


def test_raises_when_cancelled_before_solving() -> None:
    with pytest.raises(CancelledError):
        ClarkeWrightSolver().solve(make_input(), SolveMethodOptions(), CancelEvent(is_set=True))