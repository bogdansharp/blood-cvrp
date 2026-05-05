from pydantic import BaseModel, Field
from backend.src.api.models import SolverObjective


class SolveMethodOptions(BaseModel):
    random_seed: int | None = Field(default=None, ge=0)
    time_limit_sec: int | None = Field(default=None, gt=0)
    objective: SolverObjective = Field(default=SolverObjective.MINIMIZE_DISTANCE)
    cost_limit: int | None = Field(default=None)
