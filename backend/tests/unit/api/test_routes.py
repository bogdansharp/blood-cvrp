from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.src.models import Hospital, SolveMethod, SolverJob, SolverJobStatus
from backend.src.api.jobs import router as jobs_router
from backend.src.api.routing import router as routing_router
from backend.src.api.scenarios import router as scenarios_router
from backend.src.application.dependencies import get_settings
from backend.src.application.jobs import get_job_service
from backend.src.application.routing import get_routing_service
from backend.src.application.scenarios import get_scenario_service
from backend.src.settings import Settings


def make_hospital(**overrides: Any) -> Hospital:
    data = {
        "id": 1,
        "name": "Hospital",
        "lat_e6": 53100000,
        "lng_e6": -8200000,
        "demand": 3,
    }
    data.update(overrides)
    return Hospital(**data)


def make_test_app() -> FastAPI:
    app = FastAPI()
    app.include_router(scenarios_router)
    app.include_router(jobs_router)
    app.include_router(routing_router)
    return app


class FakeScenarioService:
    def __init__(self, scenario: Any | None = None, deleted: bool = True) -> None:
        self.scenario = scenario
        self.deleted = deleted

    def get_scenario(self, scenario_id: int) -> Any | None:
        return self.scenario

    def list_scenarios(self) -> list[Any]:
        return [self.scenario] if self.scenario is not None else []

    def delete_scenario(self, scenario_id: int) -> bool:
        return self.deleted


class FakeJobService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.submitted_request = None

    def get_jobs(self) -> list[SolverJob]:
        return []

    def get_job(self, job_id: int) -> SolverJob | None:
        return None

    def submit(self, request: Any) -> SolverJob:
        if self.error is not None:
            raise self.error

        self.submitted_request = request

        return SolverJob(
            id=10,
            scenario_id=request.scenario_id,
            method=request.method,
            status=SolverJobStatus.QUEUED,
            options=request.options,
        )

    def cancel(self, job_id: int) -> bool:
        return False


class FakeRoutingService:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error

    def get_geometry(
        self,
        src_lat_e6: int,
        src_lng_e6: int,
        dst_lat_e6: int,
        dst_lng_e6: int,
    ) -> list[tuple[int, int]]:
        if self.error is not None:
            raise self.error

        return [
            (53100000, -8200000),
            (53200000, -8300000),
        ]

    def get_snap_location(self, lat_e6: int, lng_e6: int) -> tuple[int, int, float]:
        if self.error is not None:
            raise self.error

        return (53100001, -8200001, 12.5)


@pytest.fixture
def app() -> FastAPI:
    return make_test_app()


def test_get_scenario_returns_service_result(app: FastAPI) -> None:
    scenario = SimpleNamespace(
        id=42,
        name="Scenario",
        description=None,
        vehicles=[],
        depots=[],
        customers=[],
    )

    app.dependency_overrides[get_scenario_service] = lambda: FakeScenarioService(
        scenario
    )

    with TestClient(app) as client:
        response = client.get("/scenarios/42")

    assert response.status_code == 200
    assert response.json()["id"] == 42
    assert response.json()["name"] == "Scenario"


def test_get_scenario_returns_404_when_missing(app: FastAPI) -> None:
    app.dependency_overrides[get_scenario_service] = lambda: FakeScenarioService(None)

    with TestClient(app) as client:
        response = client.get("/scenarios/42")

    assert response.status_code == 404


def test_run_job_builds_options_and_submits_request(app: FastAPI) -> None:
    fake_job_service = FakeJobService()

    app.dependency_overrides[get_job_service] = lambda: fake_job_service
    app.dependency_overrides[get_settings] = lambda: Settings(
        solver_hard_time_limit_sec=123,
    )

    with TestClient(app) as client:
        response = client.post(
            "/jobs/run/42",
            params={
                "method": SolveMethod.ORTOOLS.value,
                "cost_limit": 999,
                "or_balance_routes": True,
                "or_first_solution": "PATH_CHEAPEST_ARC",
                "or_local_search": "GUIDED_LOCAL_SEARCH",
                "objective": "minimize_travel_time",
            },
        )

    assert response.status_code == 200
    assert response.json()["scenario_id"] == 42
    assert fake_job_service.submitted_request is not None
    assert fake_job_service.submitted_request.options.time_limit_sec == 123
    assert fake_job_service.submitted_request.options.cost_limit == 999
    assert fake_job_service.submitted_request.options.or_balance_routes is True


def test_run_job_maps_value_error_to_400(app: FastAPI) -> None:
    app.dependency_overrides[get_job_service] = lambda: FakeJobService(
        ValueError("bad request")
    )
    app.dependency_overrides[get_settings] = lambda: Settings()

    with TestClient(app) as client:
        response = client.post(
            "/jobs/run/42",
            params={"method": SolveMethod.ORTOOLS.value},
        )

    assert response.status_code == 400


def test_run_job_maps_runtime_error_to_500(app: FastAPI) -> None:
    app.dependency_overrides[get_job_service] = lambda: FakeJobService(
        RuntimeError("internal failure")
    )
    app.dependency_overrides[get_settings] = lambda: Settings()

    with TestClient(app) as client:
        response = client.post(
            "/jobs/run/42",
            params={"method": SolveMethod.ORTOOLS.value},
        )

    assert response.status_code == 500


def test_routing_geometry_converts_e6_to_decimal(app: FastAPI) -> None:
    app.dependency_overrides[get_routing_service] = lambda: FakeRoutingService()

    with TestClient(app) as client:
        response = client.get(
            "/routing/geometry",
            params={
                "src_lat_e6": 53100000,
                "src_lng_e6": -8200000,
                "dst_lat_e6": 53200000,
                "dst_lng_e6": -8300000,
            },
        )

    assert response.status_code == 200
    assert response.json() == [[53.1, -8.2], [53.2, -8.3]]


def test_routing_snap_returns_service_result(app: FastAPI) -> None:
    app.dependency_overrides[get_routing_service] = lambda: FakeRoutingService()

    with TestClient(app) as client:
        response = client.get(
            "/routing/snap",
            params={
                "lat_e6": 53100000,
                "lng_e6": -8200000,
            },
        )

    assert response.status_code == 200
    assert response.json() == [53100001, -8200001, 12.5]


def test_routing_value_error_returns_400(app: FastAPI) -> None:
    app.dependency_overrides[get_routing_service] = lambda: FakeRoutingService(
        ValueError("invalid coordinates")
    )

    with TestClient(app) as client:
        response = client.get(
            "/routing/geometry",
            params={
                "src_lat_e6": 53100000,
                "src_lng_e6": -8200000,
                "dst_lat_e6": 53200000,
                "dst_lng_e6": -8300000,
            },
        )

    assert response.status_code == 400


def test_routing_runtime_error_returns_502(app: FastAPI) -> None:
    app.dependency_overrides[get_routing_service] = lambda: FakeRoutingService(
        RuntimeError("routing provider failed")
    )

    with TestClient(app) as client:
        response = client.get(
            "/routing/geometry",
            params={
                "src_lat_e6": 53100000,
                "src_lng_e6": -8200000,
                "dst_lat_e6": 53200000,
                "dst_lng_e6": -8300000,
            },
        )

    assert response.status_code == 502
