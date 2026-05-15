from enum import Enum

from pydantic import BaseModel, Field


class SolverObjective(str, Enum):
    MINIMIZE_DISTANCE = "minimize_distance"
    MINIMIZE_TRAVEL_TIME = "minimize_travel_time"


class ORFirstSolutionStrategy(str, Enum):
    AUTOMATIC = "AUTOMATIC"
    PATH_CHEAPEST_ARC = "PATH_CHEAPEST_ARC"
    SAVINGS = "SAVINGS"
    PARALLEL_CHEAPEST_INSERTION = "PARALLEL_CHEAPEST_INSERTION"
    LOCAL_CHEAPEST_INSERTION = "LOCAL_CHEAPEST_INSERTION"
    GLOBAL_CHEAPEST_ARC = "GLOBAL_CHEAPEST_ARC"


class ORLocalSearchMetaheuristic(str, Enum):
    NONE = "NONE"
    AUTOMATIC = "AUTOMATIC"
    GREEDY_DESCENT = "GREEDY_DESCENT"
    GUIDED_LOCAL_SEARCH = "GUIDED_LOCAL_SEARCH"
    SIMULATED_ANNEALING = "SIMULATED_ANNEALING"
    TABU_SEARCH = "TABU_SEARCH"


class ClarkeWrightLocalSearch(str, Enum):
    NONE = "NONE"
    TWO_OPT = "TWO_OPT"


class SolveMethodOptions(BaseModel):
    random_seed: int | None = Field(default=None, ge=0)
    time_limit_sec: int | None = Field(default=None, gt=0)
    objective: SolverObjective = Field(default=SolverObjective.MINIMIZE_DISTANCE)
    cost_limit: int | None = Field(default=None)
    or_balance_routes: bool = Field(default=False)  # only used by OR-Tools
    or_target_time_sec: int = Field(default=10, gt=0)  # OR-Tools
    or_first_solution_strategy: ORFirstSolutionStrategy | None = Field(
        default=None
    )  # OR-Tools
    or_local_search_metaheuristic: ORLocalSearchMetaheuristic | None = Field(
        default=None
    )  # OR-Tools
    clarke_local_search: ClarkeWrightLocalSearch = Field(
        default=ClarkeWrightLocalSearch.NONE
    )  # Clarke-Wright
