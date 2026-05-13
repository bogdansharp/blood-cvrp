import json
import threading
from pathlib import Path

from backend.src.models import Scenario, ScenarioReduced
from backend.src.data.interfaces import ScenarioRepository


class JSONScenarioRepository(ScenarioRepository):
    """JSON implementation of ScenarioRepository."""

    _SUB_DIR_NAME = "scenarios"
    _FILE_PREFIX = "scenario_"


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
    

    def get(self, scenario_id: int) -> Scenario | None:
        if scenario_id <= 0:
            return None
        scenario_path = self._dir / f"{self._FILE_PREFIX}{scenario_id}.json"
        if not scenario_path.exists():
            return None
        try:
            scenario_data = json.loads(scenario_path.read_text(encoding="utf-8"))
            return Scenario.model_validate(scenario_data)
        except (OSError, ValueError):
            return None
        
        
    def get_all(self) -> list[ScenarioReduced]:
        scenarios = []
        for file in self._dir.glob(f"{self._FILE_PREFIX}*.json"):
            try:
                scenario_data = json.loads(file.read_text(encoding="utf-8"))
                scenario = Scenario.model_validate(scenario_data)
                scenarios.append(ScenarioReduced.from_scenario(scenario))
            except (OSError, ValueError):
                continue
        scenarios.sort(key=lambda s: s.id)
        return scenarios
        
        
    def create(self, scenario: Scenario) -> Scenario | None:
        if scenario.id > 0:
            return None

        scenario_id = self._get_next_id()
        scenario = scenario.model_copy(update={"id": scenario_id})
        scenario_path = self._dir / f"{self._FILE_PREFIX}{scenario.id}.json"
        try:
            with scenario_path.open("x", encoding="utf-8") as handle:
                json.dump(scenario.model_dump(mode="json"), handle, indent=2)
        except OSError:
            return None
        
        return scenario


    def update(self, scenario: Scenario) -> Scenario | None:
        if scenario.id <= 0:
            return None
        scenario_path = self._dir / f"{self._FILE_PREFIX}{scenario.id}.json"
        if not scenario_path.exists():
            return None
        try:
            scenario_path.write_text(
                json.dumps(scenario.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            return scenario
        except OSError:
            return None
    

    def delete(self, scenario_id: int) -> bool:
        if scenario_id <= 0:
            return False
        scenario_path = self._dir / f"{self._FILE_PREFIX}{scenario_id}.json"
        if not scenario_path.exists():
            return False
        try:
            scenario_path.unlink()
            return True
        except OSError:
            return False