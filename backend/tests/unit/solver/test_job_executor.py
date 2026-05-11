import pytest

from backend.src.api.models import SolverJobStatus
from backend.src.solver.errors import CancelledError
from backend.src.solver.job_executor import JobExecutor, solve_in_process
from backend.src.solver.models import Route, Solver, SolverInput
from backend.src.solver.options import SolveMethodOptions


class CancelEvent:
    def __init__(self, is_set: bool = False) -> None:
        self._is_set = is_set

    def is_set(self) -> bool:
        return self._is_set


class DummySolver(Solver):
    def solve(self, solver_input: SolverInput, options: SolveMethodOptions | None, cancel_event):
        return [Route(nodes=[0, 1, 0], demand=1, cost=2, vehicle_capacity=10)]


def make_input() -> SolverInput:
    return SolverInput(
        n=1,
        cost=[
            [0, 1],
            [1, 0],
        ],
        demand=[0, 1],
        vehicles={10: 1},
    )


def test_submit_result_and_status_finished() -> None:
    executor = JobExecutor(max_solvers=1, max_preparation=1)

    try:
        executor.submit(1, lambda: "ok")

        assert executor.result(1) == "ok"
        assert executor.status(1) == SolverJobStatus.FINISHED
    finally:
        executor.shutdown(cancel_futures=True)


def test_submit_duplicate_job_id_raises() -> None:
    executor = JobExecutor(max_solvers=1, max_preparation=1)

    try:
        executor.submit(1, lambda: "ok")

        with pytest.raises(ValueError):
            executor.submit(1, lambda: "again")
    finally:
        executor.shutdown(cancel_futures=True)


def test_unknown_job_operations_raise_key_error() -> None:
    executor = JobExecutor(max_solvers=1, max_preparation=1)

    try:
        with pytest.raises(KeyError):
            executor.status(999)

        with pytest.raises(KeyError):
            executor.result(999)

        with pytest.raises(KeyError):
            executor.cancel(999)
    finally:
        executor.shutdown(cancel_futures=True)


def test_solve_in_process_instantiates_solver_and_returns_routes() -> None:
    routes = solve_in_process(
        DummySolver,
        make_input(),
        SolveMethodOptions(),
        None,
    )

    assert routes is not None
    assert routes[0].nodes == [0, 1, 0]


def test_solve_in_process_raises_when_already_cancelled() -> None:
    with pytest.raises(CancelledError):
        solve_in_process(
            DummySolver,
            make_input(),
            SolveMethodOptions(),
            CancelEvent(is_set=True),
        )