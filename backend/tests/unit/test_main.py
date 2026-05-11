from pathlib import Path
from types import SimpleNamespace
from typing import Any

from fastapi.testclient import TestClient

import backend.src.main as main_module
from backend.src.settings import Settings


class DummyExecutor:
    def __init__(self, max_solvers: int, max_preparation: int) -> None:
        self.max_solvers = max_solvers
        self.max_preparation = max_preparation
        self.shutdown_called = False
        self.shutdown_cancel_futures: bool | None = None

    def shutdown(self, cancel_futures: bool = False) -> None:
        self.shutdown_called = True
        self.shutdown_cancel_futures = cancel_futures


class DummyRoutingProvider:
    def __init__(self, 
        ors_api_key: str, 
        ors_base_url: str,
        ors_profile: str,
    ) -> None:
        self.ors_api_key = ors_api_key
        self.ors_base_url = ors_base_url
        self.ors_profile = ors_profile


class DummyRoutingData:
    def __init__(self, dist_repo: Any, geom_repo: Any, routing: Any) -> None:
        self.dist_repo = dist_repo
        self.geom_repo = geom_repo
        self.routing = routing


def patch_lifespan_dependencies(monkeypatch, tmp_path: Path) -> None:
    settings = Settings(
        project_root=tmp_path,
        storage_root=tmp_path / "storage",
        ors_api_key="dummy",
        ors_base_url="https://atu.ie/ors",
    )

    repos = SimpleNamespace(scenarios=object(), jobs=object(), geometries=object(), 
        distances=object(), hospitals=object(), solutions=object(),
    )

    monkeypatch.setattr(main_module, "load_settings", lambda project_root: settings)
    monkeypatch.setattr(main_module, "create_repositories", lambda storage_root: repos)
    monkeypatch.setattr(main_module, "JobExecutor", DummyExecutor)
    monkeypatch.setattr(main_module, "ORSRoutingProvider", DummyRoutingProvider)
    monkeypatch.setattr(main_module, "RoutingData", DummyRoutingData)


def test_lifespan_creates_required_app_state(tmp_path: Path, monkeypatch) -> None:
    patch_lifespan_dependencies(monkeypatch, tmp_path)

    with TestClient(main_module.app):
        assert isinstance(main_module.app.state.settings, Settings)
        assert isinstance(main_module.app.state.executor, DummyExecutor)
        assert hasattr(main_module.app.state, "repos")
        assert isinstance(main_module.app.state.routing_data, DummyRoutingData)
        assert isinstance(main_module.app.state.jobs, dict)
        assert isinstance(main_module.app.state.job_subscribers, dict)


def test_lifespan_shuts_down_executor(tmp_path: Path, monkeypatch) -> None:
    patch_lifespan_dependencies(monkeypatch, tmp_path)

    with TestClient(main_module.app):
        executor = main_module.app.state.executor

    assert executor.shutdown_called is True
    assert executor.shutdown_cancel_futures is True


def test_health_route_is_mounted(tmp_path: Path, monkeypatch) -> None:
    patch_lifespan_dependencies(monkeypatch, tmp_path)

    with TestClient(main_module.app) as client:
        response = client.get("/api/v1/health")

    assert response.status_code < 500


def test_cors_preflight_allows_frontend_origin(tmp_path: Path, monkeypatch) -> None:
    patch_lifespan_dependencies(monkeypatch, tmp_path)

    with TestClient(main_module.app) as client:
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"