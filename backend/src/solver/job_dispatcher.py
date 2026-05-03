import datetime
from time import perf_counter
from typing import Any

from backend.src.api.models import Hospital, LogEntry, LogLevel, RoutePath, Solution, SolveMethod, SolverObjective
from backend.src.solver.options import SolveMethodOptions
from backend.src.data.interfaces import ScenarioRepository, SolutionRepository
from backend.src.data.routing import RoutingData
from backend.src.solver.errors import CancelledError
from backend.src.solver.models import JobResult, Route, SolverInput, SolverRegistry, INF as INF_CAPACITY


class SolveDispatcher:

    def __init__(self, 
        registry: SolverRegistry,
        scenario_repo: ScenarioRepository,
        solution_repo: SolutionRepository,
        routing: RoutingData,
    ) -> None:
        self._registry = registry
        self._scenario_repo = scenario_repo
        self._solution_repo = solution_repo
        self._routing = routing

    def dispatch(self,
        scenario_id: int,
        method: SolveMethod,
        options: SolveMethodOptions | None = None,
        cancel_event: Any = None,
        objective: SolverObjective = SolverObjective.MINIMIZE_DISTANCE
    ) -> JobResult:
        # definitions
        self._log: list[LogEntry] = []
        solver_ms, preparation_ms, results_ms = 0, 0, 0
        solution_id = None
        cancelled = False
        self._cancel_event = cancel_event

        def get_result() -> JobResult:
            return JobResult(
                started_at=started_at,
                finished_at=datetime.datetime.now(datetime.timezone.utc),
                log=self._log,
                solution_id=solution_id,
                solver_ms=solver_ms,
                preparation_ms=preparation_ms,
                results_ms=results_ms,
                cancelled=cancelled
            )

        # prepare input
        started = perf_counter()
        started_at=datetime.datetime.now(datetime.timezone.utc)
        self._log_entry(LogLevel.INFO, f"Preparing solve job for scenario {scenario_id} with method {method.value}", at=started_at)
        try:
            self._check_cancelled()
            solver = self._registry.get(method)
            job_input = self._prepare_input(scenario_id, objective)
            preparation_ms = int((perf_counter() - started) * 1000)
            self._log_entry(LogLevel.INFO, f"Finished preparing input for scenario {scenario_id} in {preparation_ms} ms")
        except CancelledError:
            preparation_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.INFO,
                f"Job was cancelled during preparation for scenario {scenario_id}"
            )
            cancelled = True
            return get_result()
        except Exception as e:
            preparation_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.ERROR,
                f"Failed to prepare input for scenario {scenario_id}: {str(e)}"
            )
            return get_result()
        
        # run solver
        self._log_entry(
            LogLevel.INFO, 
            f"Starting solver for scenario {scenario_id} with method {method.value}"
        )
        started = perf_counter()
        try:
            raw_result = solver.solve(job_input, options, cancel_event)
        except CancelledError:
            solver_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.INFO,
                f"Job was cancelled during solving for scenario {scenario_id}"
            )
            cancelled = True
            return get_result()
        except Exception as e:
            solver_ms = int((perf_counter() - started) * 1000)
            self._log_entry(
                LogLevel.ERROR,
                f"Solver failed for scenario {scenario_id} with method {method.value}: {str(e)}"
            )
            return get_result()
        solver_ms = int((perf_counter() - started) * 1000)
        if raw_result is None:
            self._log_entry(LogLevel.ERROR, f"Solver failed to find a solution for scenario {scenario_id}")
            return get_result()
        self._log_entry(LogLevel.INFO, f"Solver finished for scenario {scenario_id} with method {method.value} in {solver_ms} ms")
        
        # process results
        started = perf_counter()
        new_solution: Solution = self._map_result(raw_result, method)
        persisted_solution = self._solution_repo.create(new_solution)
        if not persisted_solution:
            self._log_entry(LogLevel.ERROR, f"Failed to persist solution for scenario {scenario_id}")
            results_ms = int((perf_counter() - started) * 1000)
            return get_result()
        solution_id = persisted_solution.id
        self._log_entry(LogLevel.INFO, 
            f"Successfully solved scenario {scenario_id} with method {method.value} in {solver_ms} ms. Solution ID: {solution_id}"
        )
        return get_result()


    def _check_cancelled(self) -> None:
        if self._cancel_event and self._cancel_event.is_set():
            raise CancelledError("Job was cancelled")
        
    
    def _log_entry(self, level: LogLevel, message: str, at: datetime.datetime | None = None) -> None:
        if at is None:
            at = datetime.datetime.now(datetime.timezone.utc)
        self._log.append(LogEntry(
            timestamp=at,
            level=level,
            message=message
        ))


    def _prepare_input(self, 
        scenario_id: int, 
        objective: SolverObjective
    ) -> SolverInput:
        self._check_cancelled()
        scenario = self._scenario_repo.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")
        self._scenario = scenario
        n = len(scenario.customers)
        vehicles: dict[int, int] = {}
        for pool in scenario.vehicles:
            if pool.is_unlimited:
                vehicles[pool.capacity] = INF_CAPACITY
            vcnt = vehicles.get(pool.capacity, 0)
            if vcnt != INF_CAPACITY:
                vehicles[pool.capacity] = vcnt + pool.quantity
        depot = scenario.depots[0]
        points: list[tuple[int, int]] = [(depot.lat_e6, depot.lng_e6)]
        demand: list[int] = [0]
        for customer in scenario.customers:
            points.append((customer.lat_e6, customer.lng_e6))
            demand.append(customer.demand)
        matrix: list[list[tuple[float, float]]] = []
        for src_lat_e6, src_lng_e6 in points:
            self._check_cancelled()
            # self._log_entry(LogLevel.DEBUG, 
            #     f"Fetching routing data for source ({src_lat_e6}, {src_lng_e6} len(dst)={len(points)})",
            #     at=datetime.datetime.now(datetime.timezone.utc)
            # )
            matrix.append(self._routing.get_edges(src_lat_e6, src_lng_e6, points))
        idx = 0 if objective == SolverObjective.MINIMIZE_DISTANCE else 1
        cost = [[edge[idx] for edge in row] for row in matrix]
        self._matrix = matrix
        return SolverInput(n=n, cost=cost, demand=demand, vehicles=vehicles)
    

    def _get_edge(self, src_idx: int, dst_idx: int) -> tuple[float, float]:
        return self._matrix[src_idx][dst_idx]
    
    def _get_hospital(self, idx: int) -> Hospital:
        if idx == 0:
            return self._scenario.depots[0]
        return self._scenario.customers[idx - 1]

    def _map_result(self, 
        raw_result: list[Route], 
        method: SolveMethod
    ) -> Solution:
        route_paths: list[RoutePath] = []
        total_distance, total_duration = 0.0, 0.0
        for route in raw_result:
            sequence = []
            route_distance, route_duration = 0.0, 0.0
            for i, node in enumerate(route.nodes):
                sequence.append(self._get_hospital(node))
                if i == 0:
                    continue
                dist, time = self._get_edge(route.nodes[i - 1], node)
                route_distance += dist
                route_duration += time
            path = RoutePath(
                src=self._get_hospital(route.nodes[0]),
                dst=self._get_hospital(route.nodes[-1]),
                sequence=sequence,
                total_distance=route_distance,
                total_travel_time=route_duration,
                vehicle_capacity=route.vehicle_capacity,
                vehicle_capacity_used=route.demand,
            )
            route_paths.append(path)
            total_distance += route_distance
            total_duration += route_duration

        created_at = datetime.datetime.now(datetime.timezone.utc)
        name = f"{method.value} Solution {created_at.isoformat()}"
        solution = Solution(
            id=0, # to be set by repository
            name=name,
            scenario_id=self._scenario.id,
            method=method,
            total_distance=total_distance,
            total_travel_time=total_duration,
            routes=route_paths,
            created_at=created_at,
        )
        return solution