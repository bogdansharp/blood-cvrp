from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest

from backend.src.api.models import (
    Hospital,
    LogEntry,
    LogLevel,
    RoutePath,
    Solution,
    SolveMethod,
    SolverJob,
    SolverJobStatus,
)
from backend.src.application.jobs import JobService
from backend.src.application.models import SolveJobRequest
from backend.src.solver.models import JobResult
from backend.src.solver.options import SolveMethodOptions


class FakeCancelEvent:
    def __init__(self) -> None:
        self._is_set = False

    def set(self) -> None:
        self._is_set = True

    def is_set(self) -> bool:
        return self._is_set


class FakeJobRepo:
    def __init__(self) -> None:
        self.jobs: dict[int, SolverJob] = {}
        self.next_id = 1

    def create(self, job: SolverJob) -> SolverJob:
        persisted = job.model_copy(update={"id": self.next_id})
        self.jobs[persisted.id] = persisted
        self.next_id += 1
        return persisted

    def get(self, job_id: int) -> SolverJob | None:
        return self.jobs.get(job_id)

    def get_all(self) -> list[SolverJob]:
        return list(self.jobs.values())

    def update(self, job: SolverJob) -> SolverJob:
        self.jobs[job.id] = job
        return job


class FakeSolutionRepo:
    def __init__(self) -> None:
        self.solutions: dict[int, Solution] = {}

    def get(self, solution_id: int) -> Solution | None:
        return self.solutions.get(solution_id)


class FakeExecutor:
    def __init__(self) -> None:
        self.submitted: dict[int, Any] = {}
        self.statuses: dict[int, SolverJobStatus] = {}
        self.results: dict[int, Any] = {}
        self.cancel_result = False
        self.cancelled_job_id: int | None = None

    def submit(self, job_id: int, task: Any) -> None:
        self.submitted[job_id] = task
        self.statuses[job_id] = SolverJobStatus.QUEUED

    def status(self, job_id: int) -> SolverJobStatus:
        if job_id not in self.statuses:
            raise KeyError(job_id)
        return self.statuses[job_id]

    def result(self, job_id: int) -> Any:
        return self.results[job_id]

    def cancel(self, job_id: int) -> bool:
        self.cancelled_job_id = job_id
        return self.cancel_result

    def shutdown(self) -> None:
        # dummy method
        pass


class DummySolver:
    pass


class FakeRegistry:
    def get(self, method: SolveMethod) -> type:
        return DummySolver


def make_request(method: SolveMethod = SolveMethod.CLARKE_WRIGHT_SAVINIGS) -> SolveJobRequest:
    return SolveJobRequest(
        scenario_id=42,
        method=method,
        options=SolveMethodOptions(),
    )


def make_job_result(solution_id: int | None = 7, cancelled: bool = False) -> JobResult:
    started_at = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    finished_at = datetime(2026, 1, 1, 12, 1, tzinfo=timezone.utc)

    return JobResult(
        started_at=started_at,
        finished_at=finished_at,
        log=[
            LogEntry(
                timestamp=started_at,
                level=LogLevel.INFO,
                message="done",
            )
        ],
        solution_id=solution_id,
        solver_ms=100,
        preparation_ms=20,
        results_ms=5,
        cancelled=cancelled,
    )


def make_solution(solution_id: int = 7) -> Solution:
    hospital = Hospital(
        id=1,
        name="Hospital",
        lat_e6=53100000,
        lng_e6=-8200000,
        demand=0,
    )

    route = RoutePath(
        src=hospital,
        dst=hospital,
        sequence=[hospital],
        total_distance=0,
        total_travel_time=0,
        vehicle_capacity=10,
        vehicle_capacity_used=0,
    )

    return Solution(
        id=solution_id,
        name="Solution",
        scenario_id=42,
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
        total_distance=0,
        total_travel_time=0,
        routes=[route],
    )


@pytest.fixture
def job_service_context():
    job_repo = FakeJobRepo()
    solution_repo = FakeSolutionRepo()
    executor = FakeExecutor()
    cancel_event = FakeCancelEvent()
    cancel_manager = Mock()
    cancel_manager.Event.return_value = cancel_event
    cancel_tokens: dict[int, Any] = {}

    service = JobService(
        job_repo=job_repo,  # type: ignore[arg-type]
        solution_repo=solution_repo,  # type: ignore[arg-type]
        executor=executor,  # type: ignore[arg-type]
        job_preparer=Mock(),  # type: ignore[arg-type]
        job_results=Mock(),  # type: ignore[arg-type]
        cancel_manager=cancel_manager,
        cancel_tokens=cancel_tokens,
        method_registry=FakeRegistry(),  # type: ignore[arg-type]
    )

    return service, job_repo, solution_repo, executor, cancel_manager, cancel_event, cancel_tokens


def test_submit_creates_job_cancel_token_and_executor_task(job_service_context) -> None:
    service, job_repo, _, executor, cancel_manager, cancel_event, cancel_tokens = job_service_context

    job = service.submit(make_request())

    assert job.id == 1
    assert job.status == SolverJobStatus.QUEUED
    assert job_repo.get(job.id) == job
    assert cancel_tokens[job.id] is cancel_event
    assert cancel_manager.Event.called
    assert job.id in executor.submitted


def test_get_job_returns_none_when_missing(job_service_context) -> None:
    service, *_ = job_service_context

    assert service.get_job(999) is None


def test_get_job_updates_queued_job_to_running(job_service_context) -> None:
    service, _, _, executor, *_ = job_service_context

    job = service.submit(make_request())
    executor.statuses[job.id] = SolverJobStatus.RUNNING

    updated = service.get_job(job.id)

    assert updated is not None
    assert updated.status == SolverJobStatus.RUNNING


def test_get_job_copies_terminal_job_result_fields(job_service_context) -> None:
    service, _, _, executor, *_ = job_service_context

    job = service.submit(make_request())
    executor.statuses[job.id] = SolverJobStatus.FINISHED
    executor.results[job.id] = make_job_result(solution_id=7)

    updated = service.get_job(job.id)

    assert updated is not None
    assert updated.status == SolverJobStatus.FINISHED
    assert updated.solution_id == 7
    assert updated.solver_ms == 100
    assert updated.preparation_ms == 20
    assert updated.results_ms == 5
    assert len(updated.log) == 1


def test_get_job_maps_cancelled_result_to_cancelled_status(job_service_context) -> None:
    service, _, _, executor, *_ = job_service_context

    job = service.submit(make_request())
    executor.statuses[job.id] = SolverJobStatus.FINISHED
    executor.results[job.id] = make_job_result(solution_id=None, cancelled=True)

    updated = service.get_job(job.id)

    assert updated is not None
    assert updated.status == SolverJobStatus.CANCELLED


def test_cancel_queued_job_updates_status_when_executor_cancels(job_service_context) -> None:
    service, job_repo, _, executor, *_ = job_service_context

    job = service.submit(make_request())
    executor.cancel_result = True

    assert service.cancel(job.id) is True
    assert executor.cancelled_job_id == job.id
    assert job_repo.get(job.id).status == SolverJobStatus.CANCELLED


def test_cancel_running_job_sets_cancel_token(job_service_context) -> None:
    service, _, _, executor, _, _, cancel_tokens = job_service_context

    job = service.submit(make_request())
    executor.statuses[job.id] = SolverJobStatus.RUNNING
    executor.cancel_result = False

    assert service.cancel(job.id) is True
    assert cancel_tokens[job.id].is_set() is True


def test_cancel_missing_or_terminal_job_returns_false(job_service_context) -> None:
    service, job_repo, *_ = job_service_context

    assert service.cancel(999) is False

    job_repo.jobs[123] = SolverJob(
        id=123,
        scenario_id=42,
        method=SolveMethod.ORTOOLS,
        status=SolverJobStatus.FINISHED,
    )

    assert service.cancel(123) is False


def test_get_result_returns_solution_for_finished_job(job_service_context) -> None:
    service, job_repo, solution_repo, *_ = job_service_context

    job_repo.jobs[1] = SolverJob(
        id=1,
        scenario_id=42,
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
        status=SolverJobStatus.FINISHED,
        solution_id=7,
    )
    solution_repo.solutions[7] = make_solution(7)

    assert service.get_result(1).id == 7


def test_get_result_rejects_missing_or_unfinished_job(job_service_context) -> None:
    service, job_repo, *_ = job_service_context

    with pytest.raises(KeyError):
        service.get_result(999)

    job_repo.jobs[1] = SolverJob(
        id=1,
        scenario_id=42,
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
        status=SolverJobStatus.RUNNING,
    )

    with pytest.raises(RuntimeError):
        service.get_result(1)