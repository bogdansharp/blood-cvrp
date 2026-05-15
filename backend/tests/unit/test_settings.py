from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.src.settings import EnvironmentType, load_settings


@pytest.fixture(autouse=True)
def isolate_env_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)


def test_load_settings_uses_defaults(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("STORAGE_ROOT", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ORS_BASE_URL", raising=False)
    monkeypatch.delenv("SOLVER_HARD_TIME_LIMIT_SEC", raising=False)
    monkeypatch.delenv("OR_TOOLS_TARGET_TIME_SEC", raising=False)

    settings = load_settings(project_root=tmp_path)

    assert settings.project_root == tmp_path
    assert settings.environment == EnvironmentType.DEVELOPMENT
    assert settings.ors_base_url == "https://api.heigit.org/openrouteservice"
    assert settings.solver_hard_time_limit_sec == 600
    assert settings.or_tools_target_time_sec == 10
    assert settings.storage_root == (tmp_path / "storage").resolve()


def test_relative_storage_root_resolves_under_project_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("STORAGE_ROOT", "storage/test")

    settings = load_settings(project_root=tmp_path)

    assert settings.storage_root == (tmp_path / "storage/test").resolve()


def test_absolute_storage_root_stays_absolute(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storage_root = tmp_path / "absolute-storage"
    monkeypatch.setenv("STORAGE_ROOT", str(storage_root))

    settings = load_settings(project_root=tmp_path)

    assert settings.storage_root == storage_root.resolve()


def test_invalid_solver_hard_time_limit_fails_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SOLVER_HARD_TIME_LIMIT_SEC", "0")

    with pytest.raises(ValidationError):
        load_settings(project_root=tmp_path)

    monkeypatch.setenv("SOLVER_HARD_TIME_LIMIT_SEC", "-10")

    with pytest.raises(ValidationError):
        load_settings(project_root=tmp_path)


def test_invalid_or_tools_target_time_fails_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OR_TOOLS_TARGET_TIME_SEC", "40000")

    with pytest.raises(ValidationError):
        load_settings(project_root=tmp_path)

    monkeypatch.setenv("OR_TOOLS_TARGET_TIME_SEC", "-1")

    with pytest.raises(ValidationError):
        load_settings(project_root=tmp_path)
