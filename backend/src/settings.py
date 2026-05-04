from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    project_root: Path = Path.cwd()
    environment: str = Field(default="development", validation_alias="ENVIRONMENT")
    storage_root: Path = Field(default=Path("storage"), validation_alias="STORAGE_ROOT")
    ors_api_key: str = Field(default="", validation_alias="ORS_API_KEY")
    ors_base_url: str = Field(
        # default="https://api.openrouteservice.org", 
        default="https://api.heigit.org/openrouteservice",
        validation_alias="ORS_BASE_URL"
    )
    ors_profile: str = Field(default="driving-car", validation_alias="ORS_PROFILE")
    port: int = Field(default=8000, validation_alias="PORT")

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