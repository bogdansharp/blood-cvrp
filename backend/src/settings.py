from enum import Enum
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class EnvironmentType(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    STAGING = "staging"
    TEST = "test2"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    project_root: Path = Path.cwd()
    storage_root: Path = Field(default=Path("storage"), validation_alias="STORAGE_ROOT")
    environment: EnvironmentType = Field(
        default=EnvironmentType.DEVELOPMENT, validation_alias="ENVIRONMENT"
    )
    ors_api_key: str = Field(default="", validation_alias="ORS_API_KEY")
    ors_base_url: str = Field(
        default="https://api.heigit.org/openrouteservice",
        validation_alias="ORS_BASE_URL",
    )
    ors_profile: str = Field(default="driving-car", validation_alias="ORS_PROFILE")
    port: int = Field(default=8000, validation_alias="PORT")
    solver_hard_time_limit_sec: int = Field(
        default=600, validation_alias="SOLVER_HARD_TIME_LIMIT_SEC", gt=0, le=3600
    )
    or_tools_target_time_sec: int = Field(
        default=10, validation_alias="OR_TOOLS_TARGET_TIME_SEC", gt=0, le=3600
    )
    ors_max_snap_dist: int = Field(
        default=250, validation_alias="ORS_MAX_SNAP_DIST", gt=0, le=1000
    )

    @field_validator("storage_root", mode="before")
    def resolve_storage_root(cls, value: str | Path, info) -> Path:
        candidate = Path(value)
        project_root = info.data.get("project_root", Path.cwd())
        if candidate.is_absolute():
            return candidate.resolve()
        return (project_root / candidate).resolve()


def load_settings(project_root: str | Path | None = None) -> Settings:
    if project_root is not None:
        return Settings(project_root=Path(project_root))
    return Settings()
