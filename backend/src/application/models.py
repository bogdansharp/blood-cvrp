from pydantic import BaseModel, Field

from backend.src.models import SolveMethod
from backend.src.solver_options import SolveMethodOptions


class SolveJobRequest(BaseModel):
    scenario_id: int
    name: str = Field(default="Solve Request")
    method: SolveMethod
    options: SolveMethodOptions
