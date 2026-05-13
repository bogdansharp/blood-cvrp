from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.src.models import Scenario, ScenarioReduced
from backend.src.application.scenarios import ScenarioService, get_scenario_service


router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("/{scenario_id}", responses={404: {"description": "Scenario not found"}})
async def get_scenario(
    scenario_id: int,
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> Scenario:
    scenario = scenario_service.get_scenario(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404)
    return scenario


@router.get("/", response_model=list[ScenarioReduced])
async def list_scenarios(
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)]
):
    scenarios = scenario_service.list_scenarios()
    return scenarios


@router.delete("/{scenario_id}", status_code=204, responses={404: {"description": "Scenario not found"}})
async def delete_scenario(
    scenario_id: int,
    scenario_service: Annotated[ScenarioService, Depends(get_scenario_service)],
) -> None:
    is_deleted = scenario_service.delete_scenario(scenario_id)
    if not is_deleted:
        raise HTTPException(status_code=404)