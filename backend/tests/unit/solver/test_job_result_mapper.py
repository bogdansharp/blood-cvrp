import pytest

from backend.src.models import (
    Depot,
    Hospital,
    Scenario,
    Solution,
    SolveMethod,
    VehiclePool,
)
from backend.src.solver.job_result_mapper import JobResultMapper
from backend.src.solver.models import Route, SolveMethodOptions


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


def make_scenario() -> Scenario:
    return Scenario(
        id=42,
        name="Scenario",
        vehicles=[VehiclePool(capacity=10, quantity=1)],
        depots=[make_depot(name="Depot", lat_e6=53300000, lng_e6=-8330000)],
        customers=[
            make_hospital(id=1, name="A", demand=2),
            make_hospital(id=2, name="B", demand=3),
        ],
    )


class FakeSolutionRepo:
    def __init__(self, should_create: bool = True) -> None:
        self.should_create = should_create
        self.created: Solution | None = None

    def create(self, solution: Solution) -> Solution | None:
        if not self.should_create:
            return None
        self.created = solution.model_copy(update={"id": 7})
        return self.created


def test_maps_raw_routes_to_persisted_solution() -> None:
    repo = FakeSolutionRepo()
    mapper = JobResultMapper(repo)  # type: ignore[arg-type]

    solution = mapper.map_result(
        raw_result=[Route(nodes=[0, 1, 2, 0], demand=5, cost=60, vehicle_capacity=10)],
        scenario=make_scenario(),
        cost_matrix=[
            [(0, 0), (10, 100), (20, 200)],
            [(10, 100), (0, 0), (30, 300)],
            [(20, 200), (30, 300), (0, 0)],
        ],
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
        options=SolveMethodOptions(),
    )

    assert solution is not None
    assert solution.id == 7
    assert solution.scenario_id == 42
    assert solution.total_distance == 60
    assert solution.total_travel_time == 600
    assert len(solution.routes) == 1

    route = solution.routes[0]
    assert route.total_distance == 60
    assert route.total_travel_time == 600
    assert route.vehicle_capacity == 10
    assert route.vehicle_capacity_used == 5
    assert [hospital.name for hospital in route.sequence] == [
        "Depot",
        "A",
        "B",
        "Depot",
    ]


def test_invalid_node_index_raises() -> None:
    mapper = JobResultMapper(FakeSolutionRepo())  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        mapper.map_result(
            raw_result=[
                Route(nodes=[0, 999, 0], demand=1, cost=1, vehicle_capacity=10)
            ],
            scenario=make_scenario(),
            cost_matrix=[
                [(0, 0), (1, 1), (1, 1)],
                [(1, 1), (0, 0), (1, 1)],
                [(1, 1), (1, 1), (0, 0)],
            ],
            method=SolveMethod.ORTOOLS,
        )


def test_returns_none_when_repository_create_fails() -> None:
    mapper = JobResultMapper(FakeSolutionRepo(should_create=False))  # type: ignore[arg-type]

    solution = mapper.map_result(
        raw_result=[Route(nodes=[0, 1, 0], demand=2, cost=20, vehicle_capacity=10)],
        scenario=make_scenario(),
        cost_matrix=[
            [(0, 0), (10, 100), (20, 200)],
            [(10, 100), (0, 0), (30, 300)],
            [(20, 200), (30, 300), (0, 0)],
        ],
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
    )

    assert solution is None
