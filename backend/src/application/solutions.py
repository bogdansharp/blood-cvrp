from backend.src.models import Solution
from fastapi import Depends

from backend.src.application.dependencies import get_solution_repository
from backend.src.data.interfaces import SolutionRepository


class SolutionService:
    def __init__(self, repo: SolutionRepository) -> None:
        self._repo = repo

    def list_solutions(self, scenario_id: int | None = None) -> list[Solution]:
        return self._repo.get_all(scenario_id)

    def get_solution(self, id: int) -> Solution | None:
        return self._repo.get(id)

    def delete_solution(self, id: int) -> bool:
        return self._repo.delete(id)


def get_solution_service(
    repo: SolutionRepository = Depends(get_solution_repository),
) -> SolutionService:
    return SolutionService(repo)