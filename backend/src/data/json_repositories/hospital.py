import json
import threading
from pathlib import Path

from backend.src.api.models import Hospital
from backend.src.data.interfaces import HospitalRepository


class JSONHospitalRepository(HospitalRepository):
    """JSON implementation of HospitalRepository."""

    _SUB_DIR_NAME = "hospitals"
    _FILE_PREFIX = "hospital_"

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

    def create(self, hospital: Hospital) -> Hospital | None:
        if hospital.id > 0:
            return None

        hospital_id = self._get_next_id()
        hospital = hospital.model_copy(update={"id": hospital_id})
        hospital_path = self._dir / f"{self._FILE_PREFIX}{hospital.id}.json"
        try:
            with hospital_path.open("x", encoding="utf-8") as handle:
                json.dump(hospital.model_dump(mode="json"), handle, indent=2)
        except OSError:
            return None

        return hospital

    def get(self, hospital_id: int) -> Hospital | None:
        if hospital_id <= 0:
            return None
        hospital_path = self._dir / f"{self._FILE_PREFIX}{hospital_id}.json"
        if not hospital_path.exists():
            return None
        try:
            hospital_data = json.loads(hospital_path.read_text(encoding="utf-8"))
            return Hospital.model_validate(hospital_data)
        except (OSError, ValueError):
            return None
        
    def get_all(self) -> list[Hospital]:
        hospitals = []
        for file in self._dir.glob(f"{self._FILE_PREFIX}*.json"):
            try:
                hospital_data = json.loads(file.read_text(encoding="utf-8"))
                hospital = Hospital.model_validate(hospital_data)
                hospitals.append(hospital)
            except (OSError, ValueError):
                continue
        hospitals.sort(key=lambda h: h.id)
        return hospitals

    def update(self, hospital: Hospital) -> Hospital | None:
        if hospital.id <= 0:
            return None
        hospital_path = self._dir / f"{self._FILE_PREFIX}{hospital.id}.json"
        if not hospital_path.exists():
            return None
        try:
            hospital_path.write_text(
                json.dumps(hospital.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            return hospital
        except OSError:
            return None

    def delete(self, hospital_id: int) -> bool:
        if hospital_id <= 0:
            return False
        hospital_path = self._dir / f"{self._FILE_PREFIX}{hospital_id}.json"
        if not hospital_path.exists():
            return False
        try:
            hospital_path.unlink()
            return True
        except OSError:
            return False
