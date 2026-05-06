from math import inf, isfinite
from time import perf_counter
from typing import Any

from ortools.constraint_solver import pywrapcp, routing_enums_pb2

from backend.src.solver.errors import CancelledError
from backend.src.solver.models import INF as INF_CAPACITY, Route, Solver, SolverInput
from backend.src.solver.options import ORFirstSolutionStrategy, ORLocalSearchMetaheuristic, SolveMethodOptions


FIRST_SOLUTION_MAP = {
    ORFirstSolutionStrategy.AUTOMATIC:
        routing_enums_pb2.FirstSolutionStrategy.AUTOMATIC,
    ORFirstSolutionStrategy.PATH_CHEAPEST_ARC:
        routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC,
    ORFirstSolutionStrategy.SAVINGS:
        routing_enums_pb2.FirstSolutionStrategy.SAVINGS,
    ORFirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION:
        routing_enums_pb2.FirstSolutionStrategy.PARALLEL_CHEAPEST_INSERTION,
    ORFirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION:
        routing_enums_pb2.FirstSolutionStrategy.LOCAL_CHEAPEST_INSERTION,
    ORFirstSolutionStrategy.GLOBAL_CHEAPEST_ARC:
        routing_enums_pb2.FirstSolutionStrategy.GLOBAL_CHEAPEST_ARC,
}

LOCAL_SEARCH_MAP = {
    ORLocalSearchMetaheuristic.AUTOMATIC:
        routing_enums_pb2.LocalSearchMetaheuristic.AUTOMATIC,
    ORLocalSearchMetaheuristic.GREEDY_DESCENT:
        routing_enums_pb2.LocalSearchMetaheuristic.GREEDY_DESCENT,
    ORLocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH:
        routing_enums_pb2.LocalSearchMetaheuristic.GUIDED_LOCAL_SEARCH,
    ORLocalSearchMetaheuristic.SIMULATED_ANNEALING:
        routing_enums_pb2.LocalSearchMetaheuristic.SIMULATED_ANNEALING,
    ORLocalSearchMetaheuristic.TABU_SEARCH:
        routing_enums_pb2.LocalSearchMetaheuristic.TABU_SEARCH,
}


class OrToolsSolver(Solver):

    BALANCE_FACTOR = 200

    def __init__(self, 
        target_time_sec: int = 10,
        balance_routes: bool = False,
        first_solution_strategy: ORFirstSolutionStrategy 
            = ORFirstSolutionStrategy.AUTOMATIC,
        local_search_metaheuristic: ORLocalSearchMetaheuristic 
            = ORLocalSearchMetaheuristic.AUTOMATIC,
    ) -> None:
        self.target_time_sec = target_time_sec
        self.balance_routes = balance_routes
        self.first_solution = first_solution_strategy
        self.local_search = local_search_metaheuristic


    def _check_cancelled(self) -> None:
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise CancelledError("Job was cancelled")


    def _parse_input(self, input: SolverInput) -> None:
        self._n = input.n
        self._matrix = input.cost
        self._demand = input.demand.copy()
        self._vehicles = dict(input.vehicles)
        for row in self._matrix:
            for value in row:
                if not isfinite(value) or value < 0:
                    raise ValueError(f"Invalid cost value: {value}")
        self._capacities: list[int] = []
        for capacity, quantity in sorted(input.vehicles.items()):
            if quantity <= 0 or capacity <= 0:
                continue
            if quantity >= INF_CAPACITY:
                quantity = self._n
            self._capacities.extend([capacity] * quantity)
        if not self._capacities:
            raise ValueError("No vehicles available")
        if max(self._demand) > max(self._capacities):
            raise ValueError("At least one customer demand exceeds all vehicle capacities")
        if sum(self._capacities) < sum(self._demand):
            raise ValueError("Total vehicle capacity is not enough for total demand")


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
        self._cost_limit_float = inf

        time_limit_sec = self.target_time_sec
        balance_routes = self.balance_routes
        first_solution = self.first_solution
        local_search = self.local_search
        if options:
            if options.time_limit_sec is not None:
                time_limit_sec = min(options.time_limit_sec, time_limit_sec)
            if options.cost_limit is not None:
                self._cost_limit_float = options.cost_limit
            balance_routes = options.or_balance_routes
            if options.or_first_solution_strategy is not None:
                first_solution = options.or_first_solution_strategy
            if options.or_local_search_metaheuristic is not None:
                local_search = options.or_local_search_metaheuristic
        need_cost_limit_dimension = self._cost_limit_float != inf or balance_routes

        try:
            self._check_cancelled()
            self._parse_input(input)
        except CancelledError:
            raise
        except ValueError:
            return None

        manager = pywrapcp.RoutingIndexManager(
            self._n + 1,
            len(self._capacities),
            0,  # single depot at index 0
        )
        routing = pywrapcp.RoutingModel(manager)

        def cost_callback(from_index: int, to_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            to_node = manager.IndexToNode(to_index)
            return int(round(self._matrix[from_node][to_node]))
        cost_callback_index = routing.RegisterTransitCallback(cost_callback)
        routing.SetArcCostEvaluatorOfAllVehicles(cost_callback_index)

        def demand_callback(from_index: int) -> int:
            from_node = manager.IndexToNode(from_index)
            return self._demand[from_node]
        demand_callback_index = routing.RegisterUnaryTransitCallback(demand_callback)

        routing.AddDimensionWithVehicleCapacity(
            demand_callback_index, 0, self._capacities, True, "Capacity",
        )

        if need_cost_limit_dimension:
            route_cost_limit = (
                int(round(self._cost_limit_float)) 
                if isfinite(self._cost_limit_float) 
                else max(int(round(v)) for row in self._matrix for v in row) * (self._n + 1)
            )
            routing.AddDimension(
                cost_callback_index, 0, route_cost_limit, True, "RouteCost",
            )
            if balance_routes:
                route_cost_dimension = routing.GetDimensionOrDie("RouteCost")
                route_cost_dimension.SetGlobalSpanCostCoefficient(self.BALANCE_FACTOR)

        search_parameters = pywrapcp.DefaultRoutingSearchParameters()
        search_parameters.first_solution_strategy = FIRST_SOLUTION_MAP[first_solution]
        if local_search != ORLocalSearchMetaheuristic.NONE:
            search_parameters.local_search_metaheuristic = LOCAL_SEARCH_MAP[local_search]
        seconds = int(time_limit_sec)
        search_parameters.time_limit.seconds = seconds
        search_parameters.time_limit.nanos = int((time_limit_sec - seconds) * 1e9)

        self._check_cancelled()
        solution = routing.SolveWithParameters(search_parameters)
        self._check_cancelled()

        if solution is None:
            return None

        routes: list[Route] = []

        for vehicle_id in range(len(self._capacities)):
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
            if route_cost > self._cost_limit_float:
                return None

            route_demand = self._route_demand(nodes)
            routes.append(Route(
                nodes=nodes,
                demand=route_demand,
                cost=route_cost,
                vehicle_capacity=self._capacities[vehicle_id],
            ))

        return routes