from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.models import SolveMethod, SolverJob
from backend.src.application.dependencies import get_settings
from backend.src.application.jobs import JobService, SolveJobRequest, get_job_service
from backend.src.settings import Settings
from backend.src.solver.options import (
    ORFirstSolutionStrategy,
    ORLocalSearchMetaheuristic,
    SolveMethodOptions,
    SolverObjective,
)


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/")
async def list_jobs(
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> list[SolverJob]:
    jobs = job_service.get_jobs()
    return jobs


@router.get("/{job_id}", responses={404: {"description": "Job not found"}})
async def get_job(
    job_id: int,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> SolverJob:
    job = job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404)
    return job


@router.post("/run/{scenario_id}", responses={
    400: {"description": "Invalid request"},
    500: {"description": "Internal server error"},
})
async def run_job(
    scenario_id: int,
    method: SolveMethod,
    job_service: Annotated[JobService, Depends(get_job_service)],
    settings: Annotated[Settings, Depends(get_settings)],
    cost_limit: int | None = None,
    or_balance_routes: bool = False,
    or_first_solution: ORFirstSolutionStrategy = ORFirstSolutionStrategy.AUTOMATIC,
    or_local_search: ORLocalSearchMetaheuristic = ORLocalSearchMetaheuristic.NONE,
    objective: SolverObjective = SolverObjective.MINIMIZE_TRAVEL_TIME,
) -> SolverJob:
    time_limit_sec = settings.solver_hard_time_limit_sec
    options = SolveMethodOptions(
        cost_limit=cost_limit, 
        objective=objective, 
        time_limit_sec=time_limit_sec,
        or_balance_routes=or_balance_routes,
        or_first_solution_strategy=or_first_solution,
        or_local_search_metaheuristic=or_local_search,
    )
    request = SolveJobRequest(scenario_id=scenario_id, method=method, options=options)
    try:
        job = job_service.submit(request)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
    return job


@router.post("/cancel/{job_id}", status_code=204, responses={404: {"description": "Job cannot be cancelled"}})
async def cancel_job(
    job_id: int,
    job_service: Annotated[JobService, Depends(get_job_service)],
) -> None:
    is_cancelled = job_service.cancel(job_id)
    if not is_cancelled:
        raise HTTPException(status_code=404)

