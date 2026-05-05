from dataclasses import dataclass
from enum import Enum
from math import inf, isfinite
from time import perf_counter
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from backend.src.solver.errors import CancelledError
from backend.src.solver.models import INF as INF_CAPACITY, Route, Solver, SolverInput
from backend.src.solver.options import SolveMethodOptions


class OrToolsPreset(Enum):
    FAST = "fast"
    BALANCED = "balanced"
    QUALITY = "quality"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True)
class OrToolsConfig:
    first_solution_strategy: int
    local_search_metaheuristic: int | None = None


ORTOOLS_CONFIGS = {
    OrToolsPreset.FAST: OrToolsConfig(
        first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        local_search_metaheuristic=None,
    ),
    OrToolsPreset.BALANCED: OrToolsConfig(
        first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
        local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT,
    ),
    OrToolsPreset.QUALITY: OrToolsConfig(
        first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
        local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    ),
    OrToolsPreset.EXPERIMENTAL: OrToolsConfig(
        first_solution_strategy=routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
        local_search_metaheuristic=routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    ),
}    

class OrToolsSolver(Solver):

    def __init__(self, preset: OrToolsPreset = OrToolsPreset.BALANCED, target_time_sec: int = 10) -> None:
        self._preset = preset
        self._target_time_sec = target_time_sec


    def _check_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise CancelledError("Job was cancelled")


    def _parse_input(self, input: SolverInput) -> None:
        self._n = input.n
        self._matrix = input.cost
        self._demand = input.demand.copy()
        self._vehicles = dict(input.vehicles)

        self._cost_matrix: list[list[int]] = []
        for row in self._matrix:
            int_row = []
            for value in row:
                if not isfinite(value) or value < 0:
                    raise ValueError(f"Invalid cost value: {value}")
                int_row.append(int(round(value)))
            self._cost_matrix.append(int_row)


    def _build_vehicle_capacities(self) -> list[int]:
        capacities: list[int] = []

        for capacity, quantity in sorted(self._vehicles.items()):
            if quantity <= 0:
                continue

            if quantity >= INF_CAPACITY:
                quantity = self._n

            capacities.extend([capacity] * quantity)

        if not capacities:
            raise ValueError("No vehicles available")

        if max(self._demand) > max(capacities):
            raise ValueError("At least one customer demand exceeds all vehicle capacities")

        if sum(capacities) < sum(self._demand):
            raise ValueError("Total vehicle capacity is not enough for total demand")

        return capacities


    def _route_cost(self, nodes: list[int]) -> float:
        cost = 0.0
        for i in range(1, len(nodes)):
            cost += self._matrix[nodes[i - 1]][nodes[i]]
        return cost


    def _route_demand(self, nodes: list[int]) -> int:
        return sum(self._demand[node] for node in nodes if node != 0)


    def solve(
        self,
        input: SolverInput,
        options: SolveMethodOptions | None,
        cancel_event: Any | None,
    ) -> list[Route] | None:
        self._started = perf_counter()
        self._cancel_event = cancel_event
        self._cost_limit = inf

        time_limit_sec = self._target_time_sec
        if options:
            if options.time_limit_sec is not None:
                time_limit_sec = min(options.time_limit_sec, time_limit_sec)
            if options.cost_limit is not None:
                self._cost_limit = options.cost_limit

        try:
            self._check_cancelled()
            self._parse_input(input)
            vehicle_capacities = self._build_vehicle_capacities()
        except (ValueError, CancelledError):
            return None

        manager = pywrapcp.RoutingIndexManager(
            self._n + 1,
            len(vehicle_capacities),
            0,
        )
        routing = pywrapcp.RoutingModel(manager)

        def cost_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return self._cost_matrix[from_node][to_node]

        cost_callback_index = routing.RegisterTransitCallback(cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(cost_callback_index)

        def demand_callback(from_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            return self._demand[from_node]

        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)
        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index,
            0,
            vehicle_capacities,
            True,
            "Capacity",
        )

        if self._cost_limit != inf:
            routing.AddDimension(
                cost_callback_index,
                0,
                int(round(self._cost_limit)),
                True,
                "CostLimit",
            )

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        cfg = ORTOOLS_CONFIGS[self._preset]
        search_parameters.first_solution_strategy = cfg.first_solution_strategy
        if cfg.local_search_metaheuristic is not None:
            search_parameters.local_search_metaheuristic = cfg.local_search_metaheuristic

        seconds = int(time_limit_sec)
        search_parameters.time_limit.seconds = seconds
        search_parameters.time_limit.nanos = int((time_limit_sec - seconds) * 1e9)

        self._check_cancelled()
        solution = routing.SolveWithParameters(search_parameters)
        self._check_cancelled()

        if solution is None:
            return None

        routes: list[Route] = []

        for vehicle_id in range(len(vehicle_capacities)):
            index = routing.Start(vehicle_id)
            next_index = solution.Value(routing.NextVar(index))

            if routing.IsEnd(next_index):
                continue

            nodes: list[int] = []

            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                nodes.append(node)
                index = solution.Value(routing.NextVar(index))

            nodes.append(0)

            route_cost = self._route_cost(nodes)
            if route_cost > self._cost_limit:
                return None

            route_demand = self._route_demand(nodes)
            routes.append(Route(
                nodes=nodes,
                demand=route_demand,
                cost=route_cost,
                vehicle_capacity=vehicle_capacities[vehicle_id],
            ))

        return routes