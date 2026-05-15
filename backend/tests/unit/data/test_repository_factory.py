from pathlib import Path

from backend.src.data.json_repositories import create_repositories
from backend.src.data.json_repositories.distance import JSONDistanceRepository
from backend.src.data.json_repositories.geometry import JSONGeometryRepository
from backend.src.data.json_repositories.hospital import JSONHospitalRepository
from backend.src.data.json_repositories.job import JSONJobRepository
from backend.src.data.json_repositories.scenario import JSONScenarioRepository
from backend.src.data.json_repositories.solution import JSONSolutionRepository


def test_create_repositories_returns_all_json_repositories(tmp_path: Path) -> None:
    repos = create_repositories(tmp_path)

    assert isinstance(repos.scenarios, JSONScenarioRepository)
    assert isinstance(repos.jobs, JSONJobRepository)
    assert isinstance(repos.geometries, JSONGeometryRepository)
    assert isinstance(repos.distances, JSONDistanceRepository)
    assert isinstance(repos.hospitals, JSONHospitalRepository)
    assert isinstance(repos.solutions, JSONSolutionRepository)


def test_create_repositories_creates_expected_directories(tmp_path: Path) -> None:
    create_repositories(tmp_path)

    assert (tmp_path / "scenarios").is_dir()
    assert (tmp_path / "jobs").is_dir()
    assert (tmp_path / "geometries").is_dir()
    assert (tmp_path / "distances").is_dir()
    assert (tmp_path / "hospitals").is_dir()
    assert (tmp_path / "solutions").is_dir()
