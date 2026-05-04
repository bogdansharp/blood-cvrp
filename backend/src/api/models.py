from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field, computed_field, model_validator


###############################################################################
#       ENUMS
###############################################################################

class SolveMethod(str, Enum):
    CLARKE_WRIGHT_SAVINIGS = "clarke_wright_savings"
    CLARKE_WRIGHT_SAVINIGS_WITH_2_OPT = "clarke_wright_savings_with_2_opt"
    ORTOOLS = "ortools"

class SolverJobStatus(str, Enum):
    QUEUED = "queued"
    CANCELLED = "cancelled"
    RUNNING = "running"
    FINISHED = "finished"
    FAILED = "failed"

    @property
    def is_terminal(self) -> bool:
        res = self in {
            SolverJobStatus.FINISHED, 
            SolverJobStatus.FAILED, 
            SolverJobStatus.CANCELLED
        }
        return res

class LogLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    DEBUG = "debug"
    ERROR = "error"

class SolverObjective(str, Enum):
    MINIMIZE_DISTANCE = "minimize_distance"
    MINIMIZE_TRAVEL_TIME = "minimize_travel_time"    


###############################################################################
#       DATA CLASSES
###############################################################################

@dataclass
class VehiclePool:
    capacity: int
    quantity: int = -1      # -1 if unlimited
    # time_limit: int = -1    # in seconds, -1 if unlimited

    def __post_init__(self) -> None:
        if self.capacity < 1:
            raise ValueError("capacity must be >= 1")
        if self.quantity != -1 and self.quantity < 1:
            raise ValueError("quantity must be >= 1 or -1 for unlimited")
        # if self.time_limit != -1 and self.time_limit < 1:
        #     raise ValueError("time_limit must be >= 1 or -1 for unlimited")

    @property
    def is_quantity_unlimited(self) -> bool:
        return self.quantity == -1
    
    # @property
    # def is_time_unlimited(self) -> bool:
    #     return self.time_limit == -1


@dataclass
class ScenarioReduced:
    id: int
    name: str
    vehicles_count: int
    depots_count: int
    customers_count: int
    description: str | None = None

    @classmethod
    def from_scenario(cls, scenario: "Scenario") -> "ScenarioReduced":
        return cls(
            id=scenario.id,
            name=scenario.name,
            vehicles_count=len(scenario.vehicles),
            depots_count=len(scenario.depots),
            customers_count=len(scenario.customers),
            description=scenario.description,
        )

@dataclass
class SolutionReduced:
    id: int
    name: str
    scenario_id: int
    method: SolveMethod
    total_distance: float
    total_travel_time: float
    created_at: datetime
    routes_count: int

    @classmethod
    def from_solution(cls, solution: "Solution") -> "SolutionReduced":
        return cls(
            id=solution.id,
            name=solution.name,
            scenario_id=solution.scenario_id,
            method=solution.method,
            total_distance=solution.total_distance,
            total_travel_time=solution.total_travel_time,
            created_at=solution.created_at,
            routes_count=len(solution.routes),
        )

@dataclass
class LogEntry:
    timestamp: datetime
    level: LogLevel
    message: str


###############################################################################
#       PYDANTIC MODELS
###############################################################################

class Hospital(BaseModel):
    id: int
    name: str
    lat_e6: int
    lng_e6: int
    display_lat_e6: int | None = None
    display_lng_e6: int | None = None
    snap_distance_m: float = 0.0
    category: str = "Hospital"
    subcategory: str = ""
    address: str = ""
    eircode: str = ""
    demand: int = Field(ge=0, default=0)

    @computed_field
    @property
    def lat(self) -> float:
        return self.lat_e6 / 1e6

    @computed_field
    @property
    def lng(self) -> float:
        return self.lng_e6 / 1e6

    @computed_field
    @property
    def display_lat(self) -> float:
        value = self.display_lat_e6 if self.display_lat_e6 is not None else self.lat_e6
        return value / 1e6

    @computed_field
    @property
    def display_lng(self) -> float:
        value = self.display_lng_e6 if self.display_lng_e6 is not None else self.lng_e6
        return value / 1e6

class Depot(Hospital):
    pass

class Scenario(BaseModel):
    id: int
    name: str
    description: str | None = None
    vehicles: list[VehiclePool]
    depots: list[Depot]
    customers: list[Hospital]

class SolverJob(BaseModel):
    id: int
    scenario_id: int
    status: SolverJobStatus
    method: SolveMethod
    name: str | None = None
    log: list[LogEntry] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    solution_id: int | None = None
    solver_ms: int = 0
    preparation_ms: int = 0
    results_ms: int = 0

    @model_validator(mode="after")
    def _set_default_name(self) -> "SolverJob":
        if not self.name:
            self.name = f"{self.method.value}_{self.created_at.isoformat()}"
        return self

class RoutePath(BaseModel):
    src: Hospital
    dst: Hospital
    sequence: list[Hospital]
    total_distance: float
    total_travel_time: float
    vehicle_capacity: int
    vehicle_capacity_used: int

class Solution(BaseModel):
    id: int
    name: str
    scenario_id: int
    method: SolveMethod
    total_distance: float
    total_travel_time: float
    routes: list[RoutePath]
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))