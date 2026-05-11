from pydantic import BaseModel, Field

from backend.src.api.models import SolveMethod
from backend.src.solver.options import SolveMethodOptions


class SolveJobRequest(BaseModel):
    scenario_id: int
    name: str = Field(default="Solve Request")
    method: SolveMethod
    options: SolveMethodOptions