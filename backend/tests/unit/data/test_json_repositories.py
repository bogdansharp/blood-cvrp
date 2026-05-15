from pathlib import Path

from backend.src.models import Depot, Hospital, Scenario, VehiclePool
from backend.src.data.json_repositories.scenario import JSONScenarioRepository


def dummy_hospital_data(**overrides) -> dict:
    data = {
        "id": 1,
        "name": "Hospital",
        "lat_e6": 53100000,
        "lng_e6": -8200000,
        "display_lat_e6": None,
        "display_lng_e6": None,
        "demand": 0,
    }
    data.update(overrides)
    return data


def make_hospital(**overrides) -> Hospital:
    return Hospital(**dummy_hospital_data(**overrides))


def make_depot(**overrides) -> Depot:
    return Depot(**dummy_hospital_data(**overrides))


def make_scenario(id: int = 0, name: str = "Scenario") -> Scenario:
    return Scenario(
        id=id,
        name=name,
        description="Test scenario",
        vehicles=[VehiclePool(capacity=10, quantity=2)],
        depots=[make_depot(id=1, name="Depot", lat_e6=53200000, lng_e6=-8300000)],
        customers=[make_hospital(id=2, name="Customer", demand=4)],
    )


def test_scenario_repository_create_assigns_id_and_persists_file(
    tmp_path: Path,
) -> None:
    repo = JSONScenarioRepository(tmp_path)

    created = repo.create(make_scenario())

    assert created is not None
    assert created.id == 1
    assert created.name == "Scenario"
    assert (tmp_path / "scenarios" / "scenario_1.json").exists()


def test_scenario_repository_rejects_create_with_existing_id(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)

    created = repo.create(make_scenario(id=10))

    assert created is None


def test_scenario_repository_get_loads_saved_model(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)
    created = repo.create(make_scenario(name="Saved Scenario"))

    assert created is not None

    loaded = repo.get(created.id)

    assert loaded is not None
    assert loaded.id == created.id
    assert loaded.name == "Saved Scenario"
    assert len(loaded.vehicles) == 1
    assert len(loaded.depots) == 1
    assert len(loaded.customers) == 1


def test_get_missing_returns_none(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)

    assert repo.get(999) is None
    assert repo.get(0) is None
    assert repo.get(-1) is None


def test_get_all_returns_sorted_and_skips_bad_files(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)

    first = repo.create(make_scenario(name="First"))
    second = repo.create(make_scenario(name="Second"))

    assert first is not None
    assert second is not None

    bad_file = tmp_path / "scenarios" / "scenario_999.json"
    bad_file.write_text("{bad json", encoding="utf-8")

    scenarios = repo.get_all()

    assert [scenario.id for scenario in scenarios] == [1, 2]
    assert [scenario.name for scenario in scenarios] == ["First", "Second"]
    assert scenarios[0].vehicles_count == 1
    assert scenarios[0].depots_count == 1
    assert scenarios[0].customers_count == 1


def test_scenario_repository_update_existing_scenario(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)
    created = repo.create(make_scenario(name="Before"))

    assert created is not None

    updated_scenario = created.model_copy(update={"name": "After"})
    updated = repo.update(updated_scenario)

    assert updated is not None
    assert updated.name == "After"

    loaded = repo.get(created.id)

    assert loaded is not None
    assert loaded.name == "After"


def test_update_missing_returns_none(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)

    assert repo.update(make_scenario(id=0)) is None
    assert repo.update(make_scenario(id=999)) is None


def test_scenario_repository_delete_removes_existing_file(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)
    created = repo.create(make_scenario())

    assert created is not None

    assert repo.delete(created.id) is True
    assert repo.get(created.id) is None
    assert not (tmp_path / "scenarios" / f"scenario_{created.id}.json").exists()


def test_delete_missing_returns_false(tmp_path: Path) -> None:
    repo = JSONScenarioRepository(tmp_path)

    assert repo.delete(999) is False
    assert repo.delete(0) is False
    assert repo.delete(-1) is False


def test_scenario_repository_initializes_next_id_from_existing_files(
    tmp_path: Path,
) -> None:
    first_repo = JSONScenarioRepository(tmp_path)
    created = first_repo.create(make_scenario())

    assert created is not None
    assert created.id == 1

    second_repo = JSONScenarioRepository(tmp_path)
    next_created = second_repo.create(make_scenario())

    assert next_created is not None
    assert next_created.id == 2
