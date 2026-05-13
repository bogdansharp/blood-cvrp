from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.src.models import Solution
from backend.src.application.solutions import SolutionService, get_solution_service


router = APIRouter(prefix="/solutions", tags=["solutions"])


@router.get("/{solution_id}", responses={404: {"description": "Solution not found"}})
async def get_solution(
    solution_id: int,
    solution_service: Annotated[SolutionService, Depends(get_solution_service)],
) -> Solution:
    solution = solution_service.get_solution(solution_id)
    if solution is None:
        raise HTTPException(status_code=404)
    return solution


@router.get("/", response_model=list[Solution])
async def list_solutions(
    solution_service: Annotated[SolutionService, Depends(get_solution_service)]
):
    solutions = solution_service.list_solutions()
    return solutions


@router.delete("/{solution_id}", status_code=204, responses={404: {"description": "Solution not found"}})
async def delete_solution(
    solution_id: int,
    solution_service: Annotated[SolutionService, Depends(get_solution_service)],
) -> None:
    is_deleted = solution_service.delete_solution(solution_id)
    if not is_deleted:
        raise HTTPException(status_code=404)