import pytest

from backend.src.api.models import Depot, Hospital, Scenario, VehiclePool
from backend.src.solver.errors import CancelledError
from backend.src.solver.job_preparer import JobPreparer
from backend.src.solver.models import INF_VEHICLES
from backend.src.solver.options import SolverObjective


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


def make_scenario(vehicles: list[VehiclePool] | None = None) -> Scenario:
    return Scenario(
        id=42,
        name="Scenario",
        vehicles=vehicles or [VehiclePool(capacity=10, quantity=2)],
        depots=[make_depot()],
        customers=[
            make_hospital(id=1, name="A", lat_e6=53100000, lng_e6=-8200000, demand=2),
            make_hospital(id=2, name="B", lat_e6=53200000, lng_e6=-8300000, demand=3),
        ],
    )


class FakeScenarioRepo:
    def __init__(self, scenario: Scenario | None) -> None:
        self.scenario = scenario

    def get(self, scenario_id: int) -> Scenario | None:
        return self.scenario


class FakeRoutingData:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, list[tuple[int, int]]]] = []
        self.rows: list[list[tuple[float, float]]] = [
            [(0, 0), (10, 100), (20, 200)],
            [(10, 100), (0, 0), (30, 300)],
            [(20, 200), (30, 300), (0, 0)],
        ]

    def get_edges(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        points: list[tuple[int, int]],
    ) -> list[tuple[float, float]]:
        self.calls.append((src_lat_e6, src_lng_e6, points))
        row_index = len(self.calls) - 1
        return self.rows[row_index]


class CancelEvent:
    def __init__(self, is_set: bool = False) -> None:
        self._is_set = is_set

    def set(self) -> None:
        self._is_set = True

    def is_set(self) -> bool:
        return self._is_set


class CancellingRoutingData(FakeRoutingData):
    def __init__(self, cancel_event: CancelEvent) -> None:
        super().__init__()
        self.cancel_event = cancel_event

    def get_edges(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        points: list[tuple[int, int]],
    ) -> list[tuple[float, float]]:
        result = super().get_edges(src_lat_e6, src_lng_e6, points)
        self.cancel_event.set()
        return result


def test_prepare_builds_solver_input_with_distance_objective() -> None:
    scenario = make_scenario()
    routing = FakeRoutingData()
    preparer = JobPreparer(FakeScenarioRepo(scenario), routing)  # type: ignore[arg-type]

    solver_input, returned_scenario, matrix = preparer.prepare(
        42,
        SolverObjective.MINIMIZE_DISTANCE,
    )

    assert returned_scenario == scenario
    assert solver_input.n == 2
    assert solver_input.demand == [0, 2, 3]
    assert solver_input.vehicles == {10: 2}
    assert solver_input.cost == [
        [0, 10, 20],
        [10, 0, 30],
        [20, 30, 0],
    ]
    assert matrix[0][1] == (10, 100)
    assert len(routing.calls) == 3


def test_prepare_builds_solver_input_with_duration_objective() -> None:
    scenario = make_scenario()
    preparer = JobPreparer(FakeScenarioRepo(scenario), FakeRoutingData())  # type: ignore[arg-type]

    solver_input, _, _ = preparer.prepare(
        42,
        SolverObjective.MINIMIZE_TRAVEL_TIME,
    )

    assert solver_input.cost == [
        [0, 100, 200],
        [100, 0, 300],
        [200, 300, 0],
    ]


def test_prepare_maps_unlimited_vehicle_quantity() -> None:
    scenario = make_scenario(vehicles=[VehiclePool(capacity=10, quantity=-1)])
    preparer = JobPreparer(FakeScenarioRepo(scenario), FakeRoutingData())  # type: ignore[arg-type]

    solver_input, _, _ = preparer.prepare(42)

    assert solver_input.vehicles == {10: INF_VEHICLES}


def test_prepare_raises_when_scenario_missing() -> None:
    preparer = JobPreparer(FakeScenarioRepo(None), FakeRoutingData())  # type: ignore[arg-type]

    with pytest.raises(ValueError):
        preparer.prepare(42)


def test_prepare_raises_when_cancelled_before_start() -> None:
    preparer = JobPreparer(FakeScenarioRepo(make_scenario()), FakeRoutingData())  # type: ignore[arg-type]

    with pytest.raises(CancelledError):
        preparer.prepare(42, cancel_event=CancelEvent(is_set=True))


def test_prepare_raises_when_cancelled_during_routing() -> None:
    cancel_event = CancelEvent()
    routing = CancellingRoutingData(cancel_event)
    preparer = JobPreparer(FakeScenarioRepo(make_scenario()), routing)  # type: ignore[arg-type]

    with pytest.raises(CancelledError):
        preparer.prepare(42, cancel_event=cancel_event)