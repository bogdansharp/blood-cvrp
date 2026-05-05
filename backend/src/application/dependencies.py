from typing import Any

from fastapi import Depends, Request

from backend.src.data.interfaces import (
    HospitalRepository,
    JobRepository,
    Repositories,
    ScenarioRepository,
    SolutionRepository,
)
from backend.src.data.routing import RoutingData
from backend.src.settings import Settings


def get_repositories(request: Request) -> Repositories:
    return request.app.state.repos


def get_scenario_repository(
    repos: Repositories = Depends(get_repositories),
) -> ScenarioRepository:
    return repos.scenarios


def get_hospital_repository(
    repos: Repositories = Depends(get_repositories),
) -> HospitalRepository:
    return repos.hospitals


def get_solution_repository(
    repos: Repositories = Depends(get_repositories),
) -> SolutionRepository:
    return repos.solutions


def get_job_repository(
    repos: Repositories = Depends(get_repositories),
) -> JobRepository:
    return repos.jobs


def get_job_executor(request: Request) -> Any:
    return request.app.state.executor


def get_routing_data(request: Request) -> RoutingData:
    return request.app.state.routing_data


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
