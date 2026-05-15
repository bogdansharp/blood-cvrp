from dataclasses import dataclass
from pathlib import Path

from backend.src.data.interfaces import (
    DistanceRepository,
    GeometryRepository,
    HospitalRepository,
    JobRepository,
    Repositories,
    ScenarioRepository,
    SolutionRepository,
)
from backend.src.data.json_repositories.scenario import JSONScenarioRepository
from backend.src.data.json_repositories.hospital import JSONHospitalRepository
from backend.src.data.json_repositories.job import JSONJobRepository
from backend.src.data.json_repositories.geometry import JSONGeometryRepository
from backend.src.data.json_repositories.distance import JSONDistanceRepository
from backend.src.data.json_repositories.solution import JSONSolutionRepository


@dataclass
class JSONRepositories:
    scenarios: ScenarioRepository
    jobs: JobRepository
    geometries: GeometryRepository
    distances: DistanceRepository
    hospitals: HospitalRepository
    solutions: SolutionRepository


# type check assertion against the Repositories protocol
_assert_protocol: type[Repositories] = JSONRepositories


def create_repositories(storage_root: str | Path) -> Repositories:
    return JSONRepositories(
        scenarios=JSONScenarioRepository(storage_root),
        jobs=JSONJobRepository(storage_root),
        geometries=JSONGeometryRepository(storage_root),
        distances=JSONDistanceRepository(storage_root),
        solutions=JSONSolutionRepository(storage_root),
        hospitals=JSONHospitalRepository(storage_root),
    )
