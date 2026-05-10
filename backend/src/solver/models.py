from asyncio import Protocol
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, model_validator

from backend.src.api.models import LogEntry, SolveMethod
from backend.src.solver.options import SolveMethodOptions


INF_VEHICLES = 10**9


 
class SolverInput(BaseModel):
    n: int                  # numberof customers
    cost: list[list[float]] # directed cost matrix n+1 x n+1 (including depot at index 0)
    demand: list[int]       # demand for each customer (length n + 1, with depot demand = 0)
    vehicles: dict[int, int]    # vehicle capacity to available count (INF for unlimited)

    @model_validator(mode="after")
    def _validate_shapes(self) -> "SolverInput":
        expected = self.n + 1
        if len(self.cost) != expected:
            raise ValueError(f"cost must have {expected} rows (n+1)")
        for i, row in enumerate(self.cost):
            if len(row) != expected:
                raise ValueError(f"cost row {i} must have {expected} columns (n+1)")
            if row[i] != 0:
                raise ValueError("Diagonal costs must be 0")
        if len(self.demand) != expected:
            raise ValueError(f"demand must have length {expected} (n+1)")
        if self.demand[0] != 0:
            raise ValueError("depot demand must be 0")
        return self


@dataclass
class Route:
    nodes: list[int]
    demand: int
    cost: float
    vehicle_capacity: int = 0


@dataclass
class JobResult:
    started_at: datetime
    finished_at: datetime
    log: list[LogEntry] = field(default_factory=list)
    solution_id: int | None = None
    solver_ms: int = 0
    preparation_ms: int = 0
    results_ms: int = 0
    cancelled: bool = False
    failed: bool = False


class Solver(Protocol):
    def solve(self, 
        input: SolverInput, 
        options: SolveMethodOptions | None, 
        cancel_event: Any | None
    ) -> list[Route] | None: ...


class SolverRegistry:
    def __init__(self) -> None:
        self._methods: dict[SolveMethod, Any] = {}

    def register(self, 
        method: SolveMethod, 
        solver: Any
    ) -> None:
        if method in self._methods:
            raise ValueError(f"Solver method already registered: {method}")
        self._methods[method] = solver

    def get(self, method: SolveMethod) -> Any:
        if method not in self._methods:
            raise KeyError(f"Unknown solver method: {method}")
        return self._methods[method]

    def list_names(self) -> list[SolveMethod]:
        return sorted(self._methods.keys())