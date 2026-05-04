from fastapi import APIRouter, Depends, HTTPException

from backend.src.api.models import SolveMethod, SolverJob, SolverObjective
from backend.src.application.jobs import JobService, SolveJobRequest, get_job_service
from backend.src.solver.options import SolveMethodOptions


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/", response_model=list[SolverJob])
async def list_jobs(
    job_service: JobService = Depends(get_job_service),
) -> list[SolverJob]:
    jobs = job_service.get_jobs()
    return jobs


@router.get("/{job_id}", response_model=SolverJob)
async def get_job(
    job_id: int,
    job_service: JobService = Depends(get_job_service),
) -> SolverJob:
    job = job_service.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.post("/run/{scenario_id}", response_model=SolverJob)
async def run_job(
    scenario_id: int,
    method: SolveMethod,
    cost_limit: int | None = None,
    objective: SolverObjective = SolverObjective.MINIMIZE_TRAVEL_TIME,
    job_service: JobService = Depends(get_job_service),
) -> SolverJob:
    options = SolveMethodOptions(cost_limit=cost_limit, objective=objective)
    request = SolveJobRequest(scenario_id=scenario_id, method=method, options=options)
    try:
        job = job_service.submit(request)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    return job


@router.post("/cancel/{job_id}", status_code=204)
async def cancel_job(
    job_id: int,
    job_service: JobService = Depends(get_job_service),
) -> None:
    is_cancelled = job_service.cancel(job_id)
    if not is_cancelled:
        raise HTTPException(status_code=404, detail="Can not cancel job")

