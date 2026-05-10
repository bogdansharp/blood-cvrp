from concurrent.futures import CancelledError as FutureCancelledError, Future, ProcessPoolExecutor, ThreadPoolExecutor
from threading import Lock
from typing import Any, Callable

from backend.src.api.models import SolverJobStatus
from backend.src.solver.errors import CancelledError
from backend.src.solver.models import JobResult, Route, SolverInput
from backend.src.solver.options import SolveMethodOptions


def solve_in_process(
    solver_cls: Any,
    solver_input: SolverInput,
    options: SolveMethodOptions | None,
    cancel_event: Any | None,
) -> list[Route] | None:
    if cancel_event and cancel_event.is_set():
        raise CancelledError("Job was cancelled before solver started")

    solver = solver_cls()
    return solver.solve(
        solver_input,
        options,
        cancel_event,
    )


class JobExecutor:
    def __init__(self,
        max_solvers: int = 4,
        max_preparation: int = 4
    ) -> None:
        self._prep_pool = ThreadPoolExecutor(
            max_workers=max_preparation, 
            thread_name_prefix="prep-worker"
        )
        self._solver_pool = ProcessPoolExecutor(
            max_workers=max_solvers
        )
        self._futures: dict[int, Future[Any]] = {}
        self._lock = Lock()

    def submit(self, 
        job_id: int, 
        task: Callable[[], Any]
    ) -> None:
        with self._lock:
            if job_id in self._futures:
                raise ValueError(f"Job already submitted: {job_id}")
            self._futures[job_id] = self._prep_pool.submit(task)

    def run_solver(self, 
        solver_cls: Any, 
        solver_input: SolverInput, 
        options: SolveMethodOptions | None, 
        cancel_event: Any | None
    ) -> list[Route] | None:
        future = self._solver_pool.submit(
            solve_in_process,
            solver_cls,
            solver_input,
            options,
            cancel_event
        )
        return future.result()

    def status(self, job_id: int) -> SolverJobStatus:
        future = self._futures.get(job_id)
        if future is None:
            raise KeyError(f"Unknown job: {job_id}")
        if future.running():
            return SolverJobStatus.RUNNING
        if future.done():
            if future.cancelled():
                return SolverJobStatus.CANCELLED
            exc = future.exception()
            if exc is not None:
                if isinstance(exc, CancelledError):
                    return SolverJobStatus.CANCELLED
                return SolverJobStatus.FAILED
            result = future.result()
            if result is None:
                return SolverJobStatus.CANCELLED
            if isinstance(result, JobResult):
                if result.cancelled:
                    return SolverJobStatus.CANCELLED
                if result.failed:
                    return SolverJobStatus.FAILED
            return SolverJobStatus.FINISHED
        return SolverJobStatus.QUEUED

    def cancel(self, job_id: int) -> bool:
        with self._lock:
            future = self._futures.get(job_id)
            if future is None:
                raise KeyError(f"Unknown job: {job_id}")
            return future.cancel()

    def result(self, job_id: int) -> Any:
        future = self._futures.get(job_id)
        if future is None:
            raise KeyError(f"Unknown job: {job_id}")
        try:
            return future.result()
        except FutureCancelledError as exc:
            raise CancelledError("Job was cancelled") from exc

    def shutdown(self, cancel_futures: bool = False) -> None:
        self._prep_pool.shutdown(wait=True, cancel_futures=cancel_futures)
        self._solver_pool.shutdown(wait=True, cancel_futures=cancel_futures)
