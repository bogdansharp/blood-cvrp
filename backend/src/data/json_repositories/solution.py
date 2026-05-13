import json
import threading
from pathlib import Path

from backend.src.models import Solution
from backend.src.data.interfaces import SolutionRepository


class JSONSolutionRepository(SolutionRepository):
    """JSON implementation of SolutionRepository."""

    _SUB_DIR_NAME = "solutions"
    _FILE_PREFIX = "solution_"

    def __init__(self, storage_root: str | Path) -> None:
        storage_root_path = Path(storage_root)
        self._dir = storage_root_path / self._SUB_DIR_NAME
        self._dir.mkdir(parents=True, exist_ok=True)
        self._next_id_lock = threading.Lock()
        self._next_id = self._initialize_next_id()

    def _initialize_next_id(self) -> int:
        max_id = 0
        for file in self._dir.glob(f"{self._FILE_PREFIX}*.json"):
            try:
                id_part = file.stem.split("_")[1]
                id_value = int(id_part)
                max_id = max(max_id, id_value)
            except (IndexError, ValueError):
                continue
        return max_id + 1

    def _get_next_id(self) -> int:
        with self._next_id_lock:
            current_id = self._next_id
            self._next_id += 1
            return current_id

    def create(self, solution: Solution) -> Solution | None:
        if solution.id > 0:
            return None

        solution_id = self._get_next_id()
        solution = solution.model_copy(update={"id": solution_id})
        solution_path = self._dir / f"{self._FILE_PREFIX}{solution.id}.json"
        try:
            with solution_path.open("x", encoding="utf-8") as handle:
                json.dump(solution.model_dump(mode="json"), handle, indent=2)
        except OSError:
            return None

        return solution

    def get(self, solution_id: int) -> Solution | None:
        if solution_id <= 0:
            return None
        solution_path = self._dir / f"{self._FILE_PREFIX}{solution_id}.json"
        if not solution_path.exists():
            return None
        try:
            solution_data = json.loads(solution_path.read_text(encoding="utf-8"))
            return Solution.model_validate(solution_data)
        except (OSError, ValueError):
            return None
        
    def get_all(self, scenario_id: int | None) -> list[Solution]:
        solutions: list[Solution] = []
        for file in self._dir.glob(f"{self._FILE_PREFIX}*.json"):
            try:
                solution_data = json.loads(file.read_text(encoding="utf-8"))
                solution = Solution.model_validate(solution_data)
                if scenario_id is None or solution.scenario_id == scenario_id:
                    solutions.append(solution)
            except (OSError, ValueError):
                continue
        return solutions

    def update(self, solution: Solution) -> Solution | None:
        if solution.id <= 0:
            return None
        solution_path = self._dir / f"{self._FILE_PREFIX}{solution.id}.json"
        if not solution_path.exists():
            return None
        try:
            solution_path.write_text(
                json.dumps(solution.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            return solution
        except OSError:
            return None

    def delete(self, solution_id: int) -> bool:
        if solution_id <= 0:
            return False
        solution_path = self._dir / f"{self._FILE_PREFIX}{solution_id}.json"
        if not solution_path.exists():
            return False
        try:
            solution_path.unlink()
            return True
        except OSError:
            return False
