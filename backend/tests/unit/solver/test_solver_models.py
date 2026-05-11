import pytest
from pydantic import ValidationError

from backend.src.api.models import SolveMethod
from backend.src.solver.models import Solver, SolverInput, SolverRegistry


class DummySolver(Solver):
    pass


def test_solver_input_accepts_valid_shapes() -> None:
    solver_input = SolverInput(
        n=2,
        cost=[
            [0, 10, 20],
            [10, 0, 5],
            [20, 5, 0],
        ],
        demand=[0, 2, 3],
        vehicles={10: 1},
    )

    assert solver_input.n == 2


def test_solver_input_rejects_invalid_cost_shape() -> None:
    with pytest.raises(ValidationError):
        SolverInput(
            n=2,
            cost=[
                [0, 10],
                [10, 0],
            ],
            demand=[0, 2, 3],
            vehicles={10: 1},
        )


def test_solver_input_rejects_invalid_demand_length() -> None:
    with pytest.raises(ValidationError):
        SolverInput(
            n=2,
            cost=[
                [0, 10, 20],
                [10, 0, 5],
                [20, 5, 0],
            ],
            demand=[0, 2],
            vehicles={10: 1},
        )


def test_solver_input_rejects_non_zero_diagonal() -> None:
    with pytest.raises(ValidationError):
        SolverInput(
            n=1,
            cost=[
                [1, 10],
                [10, 0],
            ],
            demand=[0, 2],
            vehicles={10: 1},
        )


def test_solver_registry_register_get_and_list() -> None:
    registry = SolverRegistry()

    registry.register(SolveMethod.CLARKE_WRIGHT_SAVINIGS, DummySolver)

    assert registry.get(SolveMethod.CLARKE_WRIGHT_SAVINIGS) is DummySolver
    assert registry.list_names() == [SolveMethod.CLARKE_WRIGHT_SAVINIGS]


def test_solver_registry_rejects_duplicate_method() -> None:
    registry = SolverRegistry()
    registry.register(SolveMethod.ORTOOLS, DummySolver)

    with pytest.raises(ValueError):
        registry.register(SolveMethod.ORTOOLS, DummySolver)


def test_solver_registry_rejects_unknown_method() -> None:
    registry = SolverRegistry()

    with pytest.raises(KeyError):
        registry.get(SolveMethod.ORTOOLS)