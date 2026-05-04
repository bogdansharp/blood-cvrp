
from time import perf_counter
from typing import Any

from backend.src.solver.options import SolveMethodOptions
from backend.src.solver.errors import CancelledError
from backend.src.solver.models import Route, Solver, SolverInput


class ClarkeWrightSolver(Solver):

    def __init__(self) -> None:
        self._solution: list[Route] | None = None


    def _parse_input(self, input: SolverInput) -> None:
        self._n = input.n
        self._matrix = input.cost
        self._demand = input.demand.copy()
        self._vcap = sorted(input.vehicles.keys())
        self._vavail = dict(input.vehicles)
    

    def _get_min_vcap(self, demand: int) -> int:
        for capacity in self._vcap:
            if capacity >= demand and self._vavail[capacity] > 0:
                return capacity
        raise ValueError(f"No vehicle can handle demand {demand}")
    

    def _get_max_vcap(self) -> int:
        for i in reversed(range(len(self._vcap))):
            capacity = self._vcap[i]
            if self._vavail[capacity] > 0:
                return capacity
        raise ValueError("No vehicle available")
    

    def _periodic_check(self) -> None:
        if self._time_limit_ms is not None:
            elapsed_ms = (perf_counter() - self._started) * 1000
            if elapsed_ms > self._time_limit_ms:
                raise TimeoutError("Time limit exceeded")
        if self._cancel_event is not None and self._cancel_event.is_set():
            raise CancelledError("Job was cancelled")
    

    def solve(self, 
        input: SolverInput, 
        options: SolveMethodOptions | None,
        cancel_event: Any | None
    ) -> list[Route] | None:
        self._started = perf_counter()
        self._time_limit_ms = None
        self._cost_limit = float('inf')
        if options:
            if options.time_limit_sec is not None:
                self._time_limit_ms = options.time_limit_sec * 1000
            if options.cost_limit is not None:
                self._cost_limit = options.cost_limit
        self._cancel_event = cancel_event
        self._periodic_check()
        self._parse_input(input)
        self._solution = []

        try:
            max_cap = self._get_max_vcap()
            for node in range(1, self._n + 1):
                self._periodic_check()
                demand = self._demand[node]
                route_cost = self._matrix[0][node] + self._matrix[node][0]
                if route_cost > self._cost_limit:
                    raise ValueError(f"Single-node route cost {route_cost} exceeds cost limit {self._cost_limit}")
                while demand > max_cap:
                    demand -= max_cap
                    self._solution.append(Route([node], max_cap, route_cost, max_cap))
                    self._vavail[max_cap] -= 1
                    max_cap = self._get_max_vcap()
                self._demand[node] = demand
        except ValueError:
            return None

        self._periodic_check()
        routes = {
            i: Route([i], self._demand[i], self._matrix[0][i] + self._matrix[i][0]) 
            for i in range(1, self._n + 1) if self._demand[i] > 0
        }
        try:
            for route in routes.values():
                if route.cost > self._cost_limit:
                    raise ValueError(f"Single-node route cost {route.cost} exceeds cost limit {self._cost_limit}")
                route.vehicle_capacity = self._get_min_vcap(route.demand)
                self._vavail[route.vehicle_capacity] -= 1
        except ValueError:
            return None

        self._periodic_check()
        savings = []
        active_nodes = list(routes.keys())
        for i in active_nodes:
            for j in active_nodes:
                if i == j:
                    continue
                saving = self._matrix[i][0] + self._matrix[0][j] - self._matrix[i][j]
                if saving > 0:
                    savings.append((saving, i, j))
        savings.sort(reverse=True)

        for saving, i, j in savings:
            self._periodic_check()
            ri, rj = routes[i], routes[j]
            if ri is rj or ri.nodes[-1] != i or rj.nodes[0] != j:
                continue
            new_cost = ri.cost + rj.cost - saving
            if new_cost > self._cost_limit:
                continue
            new_demand = ri.demand + rj.demand
            self._vavail[ri.vehicle_capacity] += 1
            self._vavail[rj.vehicle_capacity] += 1
            try:
                new_vcap = self._get_min_vcap(new_demand)
            except ValueError:
                self._vavail[ri.vehicle_capacity] -= 1
                self._vavail[rj.vehicle_capacity] -= 1
                continue
            self._vavail[new_vcap] -= 1
            new_nodes = ri.nodes + rj.nodes
            new_route = Route(new_nodes, new_demand, new_cost, new_vcap)
            for node in new_nodes:
                routes[node] = new_route

        unique_routes = list({id(r): r for r in routes.values()}.values())
        self._solution.extend(list(unique_routes))
        for route in self._solution:
            route.nodes = [0] + route.nodes + [0]
        return self._solution
