import json
import threading
from pathlib import Path

from backend.src.models import LogEntry, SolverJob
from backend.src.data.interfaces import JobRepository


class JSONJobRepository(JobRepository):
    """JSON implementation of JobRepository."""

    _SUB_DIR_NAME = "jobs"
    _FILE_PREFIX = "job_"

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

    def create(self, job: SolverJob) -> SolverJob | None:
        if job.id > 0:
            return None

        job_id = self._get_next_id()
        job = job.model_copy(update={"id": job_id})
        job_path = self._dir / f"{self._FILE_PREFIX}{job.id}.json"
        try:
            with job_path.open("x", encoding="utf-8") as handle:
                json.dump(job.model_dump(mode="json"), handle, indent=2)
        except OSError:
            return None

        return job

    def get(self, job_id: int) -> SolverJob | None:
        if job_id <= 0:
            return None
        job_path = self._dir / f"{self._FILE_PREFIX}{job_id}.json"
        if not job_path.exists():
            return None
        try:
            job_data = json.loads(job_path.read_text(encoding="utf-8"))
            return SolverJob.model_validate(job_data)
        except (OSError, ValueError):
            return None
        
    def get_all(self) -> list[SolverJob]:
        jobs = []
        for file in self._dir.glob(f"{self._FILE_PREFIX}*.json"):
            try:
                job_data = json.loads(file.read_text(encoding="utf-8"))
                job = SolverJob.model_validate(job_data)
                jobs.append(job)
            except (OSError, ValueError):
                continue
        return jobs

    def update(self, job: SolverJob) -> SolverJob | None:
        if job.id <= 0:
            return None
        job_path = self._dir / f"{self._FILE_PREFIX}{job.id}.json"
        if not job_path.exists():
            return None
        try:
            job_path.write_text(
                json.dumps(job.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            return job
        except OSError:
            return None

    def add_log_entry(self, job_id: int, log_entry: LogEntry) -> bool:
        if job_id <= 0:
            return False
        job_path = self._dir / f"{self._FILE_PREFIX}{job_id}.json"
        if not job_path.exists():
            return False
        try:
            job_data = json.loads(job_path.read_text(encoding="utf-8"))
            job = SolverJob.model_validate(job_data)
        except (OSError, ValueError):
            return False

        job.log.append(log_entry)
        try:
            job_path.write_text(
                json.dumps(job.model_dump(mode="json"), indent=2),
                encoding="utf-8",
            )
            return True
        except OSError:
            return False

    def delete(self, job_id: int) -> bool:
        if job_id <= 0:
            return False
        job_path = self._dir / f"{self._FILE_PREFIX}{job_id}.json"
        if not job_path.exists():
            return False
        try:
            job_path.unlink()
            return True
        except OSError:
            return False
