import datetime

from backend.src.models import Hospital, RoutePath, Scenario, Solution, SolveMethod
from backend.src.data.interfaces import SolutionRepository
from backend.src.solver.models import Route
from backend.src.solver_options import SolveMethodOptions


class JobResultMapper:
  
    def __init__(self,
        solution_repo: SolutionRepository,
    ) -> None:
        self._solution_repo = solution_repo


    def _get_hospital(self, 
        idx: int, 
        scenario: Scenario
    ) -> Hospital:
        if idx == 0:
            return scenario.depots[0]
        if idx < 0 or idx > len(scenario.customers):
            raise ValueError(f"Invalid node index: {idx}")
        return scenario.customers[idx - 1]
    

    def _get_edge(self, 
        src_idx: int, 
        dst_idx: int,
        cost_matrix: list[list[tuple[float, float]]],
    ) -> tuple[float, float]:
        return cost_matrix[src_idx][dst_idx]
    

    def map_result(self, 
        raw_result: list[Route],
        scenario: Scenario,
        cost_matrix: list[list[tuple[float, float]]],
        method: SolveMethod,
        options: SolveMethodOptions | None = None,
    ) -> Solution | None:
        route_paths: list[RoutePath] = []
        total_distance, total_duration = 0.0, 0.0
        for route in raw_result:
            sequence = []
            route_distance, route_duration = 0.0, 0.0
            for i, node in enumerate(route.nodes):
                sequence.append(self._get_hospital(node, scenario))
                if i == 0:
                    continue
                dist, time = self._get_edge(route.nodes[i - 1], node, cost_matrix)
                route_distance += dist
                route_duration += time
            path = RoutePath(
                src=self._get_hospital(route.nodes[0], scenario),
                dst=self._get_hospital(route.nodes[-1], scenario),
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
        new_solution = Solution(
            id=0, # to be set by repository
            name=name,
            scenario_id=scenario.id,
            method=method,
            options=options,
            total_distance=total_distance,
            total_travel_time=total_duration,
            routes=route_paths,
            created_at=created_at,
        )

        persisted_solution = self._solution_repo.create(new_solution)
        return persisted_solution