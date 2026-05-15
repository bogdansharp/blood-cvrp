import datetime
from time import perf_counter
from typing import Any

from backend.src.models import LogEntry, LogLevel, Solution
from backend.src.application.jobs import SolveJobRequest
from backend.src.solver.errors import CancelledError, SolverFailedError
from backend.src.solver.job_executor import JobExecutor
from backend.src.solver.job_preparer import JobPreparer
from backend.src.solver.models import JobResult
from backend.src.solver.job_result_mapper import JobResultMapper
from backend.src.solver_options import SolverObjective


class JobPipeline:
    def __init__(
        self,
        request: SolveJobRequest,
        job_preparer: JobPreparer,
        job_results: JobResultMapper,
        solver_cls: Any,
        cancel_event: Any,
        executor: JobExecutor,
    ) -> None:
        self._request = request
        self._cancel_event = cancel_event
        self._job_preparer = job_preparer
        self._job_results = job_results
        self._solver_cls = solver_cls
        self._executor = executor
        self._log: list[LogEntry] = []

    def __call__(self) -> JobResult | None:
        if self._cancel_event and self._cancel_event.is_set():
            return None

        scenario_id = self._request.scenario_id
        method = self._request.method
        options = self._request.options
        objective = (
            options.objective
            if options and options.objective
            else SolverObjective.MINIMIZE_DISTANCE
        )
        solver_ms, preparation_ms, results_ms = 0, 0, 0
        started_at = datetime.datetime.now(datetime.timezone.utc)
        solution_id = None
        cancelled = False
        failed = False

        def get_result() -> JobResult:
            return JobResult(
                started_at=started_at,
                finished_at=datetime.datetime.now(datetime.timezone.utc),
                log=self._log,
                solution_id=solution_id,
                solver_ms=solver_ms,
                preparation_ms=preparation_ms,
                results_ms=results_ms,
                cancelled=cancelled,
                failed=failed,
            )

        # Prepare input
        started = perf_counter()
        self._log_entry(
            LogLevel.INFO,
            f"Preparing solve job for scenario {scenario_id} with method {method.value}",
            at=started_at,
        )
        try:
            solver_input, scenario, matrix = self._job_preparer.prepare(
                scenario_id, objective, self._cancel_event
            )
            preparation_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.INFO,
                f"Finished preparing input for scenario {scenario_id} in {preparation_ms} ms",
            )
        except CancelledError:
            preparation_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.INFO,
                f"Job was cancelled during preparation for scenario {scenario_id}",
            )
            cancelled = True
            return get_result()
        except Exception as e:
            preparation_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.ERROR,
                f"Failed to prepare input for scenario {scenario_id}: {str(e)}",
            )
            failed = True
            return get_result()

        # run solver
        self._log_entry(
            LogLevel.INFO,
            f"Starting solver for scenario {scenario_id} with method {method.value}",
        )
        started = perf_counter()
        try:
            raw_result = self._executor.run_solver(
                solver_cls=self._solver_cls,
                solver_input=solver_input,
                options=options,
                cancel_event=self._cancel_event,
            )
        except CancelledError:
            solver_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.INFO,
                f"Job was cancelled during solving for scenario {scenario_id}",
            )
            cancelled = True
            return get_result()
        except SolverFailedError as e:
            solver_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.ERROR,
                f"Solver failed for scenario {scenario_id} with method {method.value}: {str(e)}",
            )
            failed = True
            return get_result()
        except Exception as e:
            solver_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.ERROR,
                f"Unexpected solver error for scenario {scenario_id} with method {method.value}: {str(e)}",
            )
            failed = True
            return get_result()
        solver_ms = int((perf_counter() - started) * 1000)
        if raw_result is None:
            self._log_entry(
                LogLevel.ERROR,
                f"Solver failed to find a solution for scenario {scenario_id}",
            )
            failed = True
            return get_result()
        self._log_entry(
            LogLevel.INFO,
            f"Solver finished for scenario {scenario_id} with method {method.value} in {solver_ms} ms",
        )

        # process results
        started = perf_counter()
        solution: Solution | None = self._job_results.map_result(
            raw_result=raw_result,
            scenario=scenario,
            cost_matrix=matrix,
            method=method,
            options=options,
        )
        if not solution:
            self._log_entry(
                LogLevel.ERROR, f"Failed to persist solution for scenario {scenario_id}"
            )
            failed = True
            results_ms = int((perf_counter() - started) * 1000)
            return get_result()
        solution_id = solution.id
        self._log_entry(
            LogLevel.INFO,
            f"Successfully solved scenario {scenario_id} with method {method.value} in {solver_ms} ms. Solution ID: {solution_id}",
        )
        return get_result()

    def _log_entry(
        self, level: LogLevel, message: str, at: datetime.datetime | None = None
    ) -> None:
        if at is None:
            at = datetime.datetime.now(datetime.timezone.utc)
        self._log.append(LogEntry(timestamp=at, level=level, message=message))
