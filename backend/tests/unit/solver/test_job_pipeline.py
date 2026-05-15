from typing import Any

from backend.src.models import (
    Depot,
    Hospital,
    Scenario,
    Solution,
    SolveMethod,
    VehiclePool,
)
from backend.src.application.models import SolveJobRequest
from backend.src.solver.errors import CancelledError, SolverFailedError
from backend.src.solver.job_pipeline import JobPipeline
from backend.src.solver.models import Route, Solver, SolverInput, SolveMethodOptions


class CancelEvent:
    def __init__(self, is_set: bool = False) -> None:
        self._is_set = is_set

    def is_set(self) -> bool:
        return self._is_set


class FakePreparer:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def prepare(self, scenario_id: int, objective: Any, cancel_event: Any):
        if self.error is not None:
            raise self.error
        return make_solver_input(), make_scenario(), make_matrix()


class FakeExecutor:
    def __init__(
        self, result: list[Route] | None = None, error: Exception | None = None
    ) -> None:
        self.result = (
            result
            if result is not None
            else [Route([0, 1, 0], demand=2, cost=20, vehicle_capacity=10)]
        )
        self.error = error

    def run_solver(
        self,
        solver_cls: Any,
        solver_input: SolverInput,
        options: SolveMethodOptions | None,
        cancel_event: Any,
    ):
        if self.error is not None:
            raise self.error
        return self.result


class FakeJobResults:
    def __init__(self, solution: Solution | None = None) -> None:
        self.solution = solution

    def map_result(self, raw_result, scenario, cost_matrix, method, options):
        return self.solution


class DummySolver(Solver):
    pass


def dummy_hospital_data(**overrides) -> dict:
    data = {
        "id": 1,
        "name": "Hospital",
        "lat_e6": 53100000,
        "lng_e6": -8200000,
        "display_lat_e6": None,
        "display_lng_e6": None,
        "demand": 0,
    }
    data.update(overrides)
    return data


def make_hospital(**overrides) -> Hospital:
    return Hospital(**dummy_hospital_data(**overrides))


def make_depot(**overrides) -> Depot:
    return Depot(**dummy_hospital_data(**overrides))


def make_scenario() -> Scenario:
    return Scenario(
        id=42,
        name="Scenario",
        vehicles=[VehiclePool(capacity=10, quantity=1)],
        depots=[make_depot(id=100, name="Depot", demand=0)],
        customers=[make_hospital(id=1, name="A", demand=2)],
    )


def make_solver_input() -> SolverInput:
    return SolverInput(
        n=1,
        cost=[
            [0, 10],
            [10, 0],
        ],
        demand=[0, 2],
        vehicles={10: 1},
    )


def make_matrix() -> list[list[tuple[float, float]]]:
    return [
        [(0, 0), (10, 100)],
        [(10, 100), (0, 0)],
    ]


def make_solution() -> Solution:
    scenario = make_scenario()
    return Solution(
        id=7,
        name="Solution",
        scenario_id=scenario.id,
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
        total_distance=20,
        total_travel_time=200,
        routes=[],
    )


def make_request() -> SolveJobRequest:
    return SolveJobRequest(
        scenario_id=42,
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
        options=SolveMethodOptions(),
    )


def make_pipeline(
    preparer: FakePreparer | None = None,
    executor: FakeExecutor | None = None,
    job_results: FakeJobResults | None = None,
    cancel_event: CancelEvent | None = None,
) -> JobPipeline:
    return JobPipeline(
        request=make_request(),
        job_preparer=preparer or FakePreparer(),  # type: ignore[arg-type]
        job_results=job_results or FakeJobResults(make_solution()),  # type: ignore[arg-type]
        solver_cls=DummySolver,
        cancel_event=cancel_event or CancelEvent(),
        executor=executor or FakeExecutor(),  # type: ignore[arg-type]
    )


def test_success_returns_job_result_with_solution_id() -> None:
    result = make_pipeline().__call__()

    assert result is not None
    assert result.cancelled is False
    assert result.failed is False
    assert result.solution_id == 7
    assert result.preparation_ms >= 0
    assert result.solver_ms >= 0
    assert len(result.log) >= 3


def test_cancelled_before_start_returns_none() -> None:
    result = make_pipeline(cancel_event=CancelEvent(is_set=True)).__call__()

    assert result is None


def test_preparation_cancelled_returns_cancelled_result() -> None:
    result = make_pipeline(
        preparer=FakePreparer(CancelledError("cancelled"))
    ).__call__()

    assert result is not None
    assert result.cancelled is True
    assert result.failed is False


def test_preparation_error_returns_failed_result() -> None:
    result = make_pipeline(preparer=FakePreparer(ValueError("bad input"))).__call__()

    assert result is not None
    assert result.failed is True
    assert result.cancelled is False


def test_solver_failed_error_returns_failed_result() -> None:
    result = make_pipeline(
        executor=FakeExecutor(error=SolverFailedError("no solution"))
    ).__call__()

    assert result is not None
    assert result.failed is True
    assert result.cancelled is False


def test_solver_cancelled_returns_cancelled_result() -> None:
    result = make_pipeline(
        executor=FakeExecutor(error=CancelledError("cancelled"))
    ).__call__()

    assert result is not None
    assert result.cancelled is True
    assert result.failed is False


def test_result_mapper_failure_returns_failed_result() -> None:
    result = make_pipeline(job_results=FakeJobResults(solution=None)).__call__()

    assert result is not None
    assert result.failed is True
    assert result.solution_id is None
