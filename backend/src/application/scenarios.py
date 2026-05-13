from backend.src.models import Scenario, ScenarioReduced
from fastapi import Depends

from backend.src.application.dependencies import get_scenario_repository
from backend.src.data.interfaces import ScenarioRepository


class ScenarioService:
    def __init__(self, repo: ScenarioRepository) -> None:
        self._repo = repo

    def list_scenarios(self) -> list[ScenarioReduced]:
        return self._repo.get_all()
    
    def get_scenario(self, id: int) -> Scenario | None:
        return self._repo.get(id)
    
    def create_scenario(self, scenario: Scenario) -> Scenario | None:
        return self._repo.create(scenario)

    def delete_scenario(self, id: int) -> bool:
        return self._repo.delete(id)


def get_scenario_service(
    repo: ScenarioRepository = Depends(get_scenario_repository),
) -> ScenarioService:
    return ScenarioService(repo)