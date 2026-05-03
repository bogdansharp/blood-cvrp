from concurrent.futures import CancelledError as FutureCancelledError, Future, ThreadPoolExecutor
from threading import Lock
from typing import Any, Callable

from backend.src.api.models import SolverJobStatus
from backend.src.solver.errors import CancelledError
from backend.src.solver.models import JobResult


class JobExecutor:
    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers)
        self._futures: dict[int, Future[Any]] = {}
        self._lock = Lock()

    def submit(self, job_id: int, task: Callable[[], Any]) -> None:
        with self._lock:
            if job_id in self._futures:
                raise ValueError(f"Job already submitted: {job_id}")
            self._futures[job_id] = self._pool.submit(task)

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
            if isinstance(result, JobResult) and result.cancelled:
                return SolverJobStatus.CANCELLED
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
        self._pool.shutdown(wait=True, cancel_futures=cancel_futures)
