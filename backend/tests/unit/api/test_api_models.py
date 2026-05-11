from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.src.api.models import (
    Depot,
    Hospital,
    LogLevel,
    RoutePath,
    Scenario,
    ScenarioReduced,
    Solution,
    SolutionReduced,
    SolveMethod,
    SolverJob,
    SolverJobStatus,
    VehiclePool,
)

def dummy_hospital_data(**overrides) -> dict:
    data = {
        "id": 1,
        "name": "Hospital",
        "lat_e6": 53100000,
        "lng_e6": -8200000,
        "display_lat_e6": None,
        "display_lng_e6": None,
        "demand": 3,
    }
    data.update(overrides)
    return data

def make_hospital(**overrides) -> Hospital:
    return Hospital(**dummy_hospital_data(**overrides))

def make_depot(**overrides) -> Depot:
    return Depot(**dummy_hospital_data(**overrides))


def test_hospital_computed_coordinates() -> None:
    hospital = make_hospital(
        lat_e6=53123456,
        lng_e6=-8123456,
        display_lat_e6=53200000,
        display_lng_e6=-8300000,
    )

    assert abs(hospital.lat - 53.123456) < 1e-6
    assert abs(hospital.lng - (-8.123456)) < 1e-6
    assert abs(hospital.display_lat - 53.2) < 1e-6
    assert abs(hospital.display_lng - (-8.3)) < 1e-6


def test_hospital_rejects_negative_demand() -> None:
    with pytest.raises(ValidationError):
        make_hospital(demand=-1)


def test_vehicle_pool_validation_and_unlimited_quantity() -> None:
    assert VehiclePool(capacity=10, quantity=-1).is_quantity_unlimited is True

    with pytest.raises(ValueError):
        VehiclePool(capacity=0, quantity=1)

    with pytest.raises(ValueError):
        VehiclePool(capacity=10, quantity=0)


def test_reduced_models_are_created_from_full_models() -> None:
    depot = make_depot(id=100, name="Depot", demand=0)
    customer = make_hospital(id=200, name="Customer", demand=4)

    scenario = Scenario(
        id=42,
        name="Scenario",
        vehicles=[VehiclePool(capacity=10, quantity=2)],
        depots=[depot],
        customers=[customer],
    )

    reduced_scenario = ScenarioReduced.from_scenario(scenario)

    assert reduced_scenario.id == 42
    assert reduced_scenario.vehicles_count == 1
    assert reduced_scenario.depots_count == 1
    assert reduced_scenario.customers_count == 1

    route = RoutePath(
        src=depot,
        dst=depot,
        sequence=[depot, customer, depot],
        total_distance=1000,
        total_travel_time=600,
        vehicle_capacity=10,
        vehicle_capacity_used=4,
    )

    solution = Solution(
        id=7,
        name="Solution",
        scenario_id=42,
        method=SolveMethod.CLARKE_WRIGHT_SAVINIGS,
        total_distance=1000,
        total_travel_time=600,
        routes=[route],
        created_at=datetime.now(timezone.utc),
    )

    reduced_solution = SolutionReduced.from_solution(solution)

    assert reduced_solution.id == 7
    assert reduced_solution.routes_count == 1
    assert reduced_solution.total_distance == 1000


def test_solver_job_defaults_and_terminal_statuses() -> None:
    job = SolverJob(
        id=1,
        scenario_id=42,
        status=SolverJobStatus.QUEUED,
        method=SolveMethod.ORTOOLS,
    )

    assert job.name is not None
    assert job.name.startswith("ortools_")
    assert SolverJobStatus.FINISHED.is_terminal is True
    assert SolverJobStatus.FAILED.is_terminal is True
    assert SolverJobStatus.CANCELLED.is_terminal is True
    assert SolverJobStatus.RUNNING.is_terminal is False


def test_log_level_values_are_stable() -> None:
    assert LogLevel.INFO.value == "info"
    assert LogLevel.ERROR.value == "error"