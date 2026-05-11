from typing import Any

from backend.src.api.models import Scenario
from backend.src.data.interfaces import ScenarioRepository
from backend.src.data.routing import RoutingData
from backend.src.solver.errors import CancelledError
from backend.src.solver.models import INF_VEHICLES, SolverInput
from backend.src.solver.options import SolverObjective


class JobPreparer:
  
    def __init__(self,
        scenario_repo: ScenarioRepository,
        routing: RoutingData,
    ) -> None:
        self._scenario_repo = scenario_repo
        self._routing = routing


    def _check_cancelled(self, cancel_event: Any | None) -> None:
        if cancel_event and cancel_event.is_set():
            raise CancelledError("Job was cancelled")


    def prepare(self, 
        scenario_id: int, 
        objective: SolverObjective = SolverObjective.MINIMIZE_TRAVEL_TIME,
        cancel_event: Any | None = None,
    ) -> tuple[SolverInput, Scenario, list[list[tuple[float, float]]]]:
        self._check_cancelled(cancel_event)
        scenario = self._scenario_repo.get(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario not found: {scenario_id}")
        n = len(scenario.customers)
        vehicles: dict[int, int] = {}
        for pool in scenario.vehicles:
            if pool.is_quantity_unlimited:
                vehicles[pool.capacity] = INF_VEHICLES
            vcnt = vehicles.get(pool.capacity, 0)
            if vcnt != INF_VEHICLES:
                vehicles[pool.capacity] = vcnt + pool.quantity
        depot = scenario.depots[0]
        points: list[tuple[int, int]] = [(depot.lat_e6, depot.lng_e6)]
        demand: list[int] = [0]
        for customer in scenario.customers:
            points.append((customer.lat_e6, customer.lng_e6))
            demand.append(customer.demand)
        matrix: list[list[tuple[float, float]]] = []
        for src_lat_e6, src_lng_e6 in points:
            self._check_cancelled(cancel_event)
            matrix.append(self._routing.get_edges(src_lat_e6, src_lng_e6, points))
        idx = 0 if objective == SolverObjective.MINIMIZE_DISTANCE else 1
        cost = [[edge[idx] for edge in row] for row in matrix]
        solver_input = SolverInput(n=n, cost=cost, demand=demand, vehicles=vehicles)
        return solver_input, scenario, matrix