from typing import Any

from fastapi import Depends

from backend.src.api.models import Solution, SolveMethod, SolverJob, SolverJobStatus
from backend.src.application.dependencies import (
    get_cancel_manager,
    get_cancel_tokens,
    get_job_executor,
    get_job_repository,
    get_routing_data,
    get_scenario_repository,
    get_solution_repository,
)
from backend.src.application.models import SolveJobRequest
from backend.src.data.interfaces import JobRepository, ScenarioRepository, SolutionRepository
from backend.src.data.routing import RoutingData
from backend.src.solver.clarke_wright_solver import ClarkeWrightSolver
from backend.src.solver.errors import CancelledError
from backend.src.solver.job_executor import JobExecutor
from backend.src.solver.job_pipeline import JobPipeline
from backend.src.solver.models import JobResult, SolverRegistry
from backend.src.solver.ortools import OrToolsSolver
from backend.src.solver.job_preparer import JobPreparer
from backend.src.solver.job_results import JobResults

    

class JobStateMachine:

    _ALLOWED: dict[SolverJobStatus, set[SolverJobStatus]] = {
        SolverJobStatus.QUEUED: {SolverJobStatus.RUNNING, SolverJobStatus.CANCELLED},
        SolverJobStatus.RUNNING: {SolverJobStatus.FINISHED, SolverJobStatus.FAILED, SolverJobStatus.CANCELLED},
        SolverJobStatus.CANCELLED: set(),
        SolverJobStatus.FINISHED: set(),
        SolverJobStatus.FAILED: set(),
    }

    def can_transition(self, from_status: SolverJobStatus, to_status: SolverJobStatus) -> bool:
        return to_status in self._ALLOWED[from_status]

    def transition(self, from_status: SolverJobStatus, to_status: SolverJobStatus) -> SolverJobStatus:
        if self.can_transition(from_status, to_status):
            return to_status
        raise ValueError(f"Invalid state transition from {from_status} to {to_status}")



class JobService:
    def __init__(self, 
        job_repo: JobRepository,
        solution_repo: SolutionRepository,
        executor: JobExecutor,
        job_preparer: JobPreparer,
        job_results: JobResults,
        cancel_manager: Any,
        cancel_tokens: dict[int, Any],
        method_registry: SolverRegistry,
        state_machine: JobStateMachine | None = None,
    ) -> None:
        self._job_repo = job_repo
        self._solution_repo = solution_repo
        self._executor = executor
        self._sm = state_machine or JobStateMachine()
        self._cancel_manager = cancel_manager
        self._cancel_tokens = cancel_tokens
        self._job_preparer = job_preparer
        self._job_results = job_results
        self._method_registry = method_registry


    def submit(self, payload: SolveJobRequest) -> SolverJob:
        created_job = SolverJob(
            id=0,  # placeholder, will be set by repository
            scenario_id=payload.scenario_id,
            method=payload.method,
            status=SolverJobStatus.QUEUED,
            options=payload.options,
        )
        persisted_job = self._job_repo.create(created_job)
        if persisted_job is None:
            raise RuntimeError("Failed to create job in repository")

        cancel_event = self._cancel_manager.Event()
        self._cancel_tokens[persisted_job.id] = cancel_event

        task = JobPipeline(
            request=payload,
            job_preparer=self._job_preparer,
            job_results=self._job_results,
            solver_cls=self._method_registry.get(payload.method),
            cancel_event=cancel_event,
            executor=self._executor,
        )
        self._executor.submit(persisted_job.id, task)
        return persisted_job


    def get_job(self, job_id: int) -> SolverJob | None:
        job = self._job_repo.get(job_id)
        if job is None:
            return None

        if job.status.is_terminal:
            return job

        try:
            executor_status = self._executor.status(job_id)
        except KeyError:
            return job

        if executor_status == job.status:
            return job

        if executor_status == SolverJobStatus.RUNNING:
            if job.status == SolverJobStatus.QUEUED:
                job.status = self._sm.transition(job.status, SolverJobStatus.RUNNING)

        if executor_status.is_terminal:
            try:
                result = self._executor.result(job_id)
                if isinstance(result, JobResult):
                    job.started_at = result.started_at
                    job.finished_at = result.finished_at
                    job.solver_ms = result.solver_ms
                    job.preparation_ms = result.preparation_ms
                    job.results_ms = result.results_ms
                    job.log = result.log
                    job.solution_id = result.solution_id
                    if result.cancelled:
                        executor_status = SolverJobStatus.CANCELLED
            except CancelledError:
                executor_status = SolverJobStatus.CANCELLED
            if job.status == SolverJobStatus.QUEUED:
                job.status = self._sm.transition(job.status, SolverJobStatus.RUNNING)
            job.status = self._sm.transition(job.status, executor_status)

        saved_job = self._job_repo.update(job)
        return saved_job


    def get_jobs(self) -> list[SolverJob]:
        return self._job_repo.get_all()


    def cancel(self, job_id: int) -> bool:
        job = self.get_job(job_id)
        if job is None:
            return False
        if job.status.is_terminal:
            return False

        # Cancel the job before started
        try:
            if self._executor.cancel(job_id):
                job.status = self._sm.transition(job.status, SolverJobStatus.CANCELLED)
                self._job_repo.update(job)
                return True
        except KeyError:
            pass

        # Cancel the job if already started
        cancel_token = self._cancel_tokens.get(job_id)
        if cancel_token is None:
            return False
        cancel_token.set()
        return True


    def get_result(self, job_id: int) -> Solution:
        job = self.get_job(job_id)
        if job is None:
            raise KeyError(f"Job not found: {job_id}")
        if job.status != SolverJobStatus.FINISHED or not job.solution_id:
            raise RuntimeError("Solve job is not finished yet")
        solution = self._solution_repo.get(job.solution_id)
        if solution is None:
            raise KeyError(f"Solution not found for job: {job_id}")
        return solution


    def shutdown(self) -> None:
        self._executor.shutdown()


def get_job_service(
    job_repo: JobRepository = Depends(get_job_repository),
    solution_repo: SolutionRepository = Depends(get_solution_repository),
    scenario_repo: ScenarioRepository = Depends(get_scenario_repository),
    routing: RoutingData = Depends(get_routing_data),
    executor: JobExecutor = Depends(get_job_executor),
    cancel_manager: Any = Depends(get_cancel_manager),
    cancel_tokens: dict[int, Any] = Depends(get_cancel_tokens),
) -> JobService:
    job_preparer = JobPreparer(
        scenario_repo=scenario_repo,
        routing=routing,
    )
    job_results = JobResults(
        solution_repo=solution_repo,
    )
    registry = SolverRegistry()
    registry.register(SolveMethod.CLARKE_WRIGHT_SAVINIGS, ClarkeWrightSolver)
    registry.register(SolveMethod.ORTOOLS, OrToolsSolver)
    return JobService(
        job_repo=job_repo,
        solution_repo=solution_repo,
        executor=executor,
        job_preparer=job_preparer,
        job_results=job_results,
        cancel_manager=cancel_manager,
        cancel_tokens=cancel_tokens,
        method_registry=registry,
    )
