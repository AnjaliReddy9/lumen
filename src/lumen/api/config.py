from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_nested_delimiter="__",
    )

    anthropic_api_key: str = Field(validation_alias="ANTHROPIC_API_KEY")
    semantic_dir: Path = Field(validation_alias="LUMEN_SEMANTIC_DIR")
    warehouse_path: str = Field(validation_alias="LUMEN_WAREHOUSE_PATH")
    warehouse_type: Literal["duckdb", "postgres"] = Field(
        default="duckdb", validation_alias="LUMEN_WAREHOUSE_TYPE"
    )
    dialect: str = Field(default="sqlite", validation_alias="LUMEN_DIALECT")
    anthropic_model: str = Field(
        default="claude-sonnet-4-5", validation_alias="LUMEN_ANTHROPIC_MODEL"
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:4200", "http://localhost:3000"],
        validation_alias="LUMEN_CORS_ORIGINS",
    )
    log_level: str = Field(default="info", validation_alias="LUMEN_LOG_LEVEL")
    enable_eval_api: bool = Field(default=False, validation_alias="ENABLE_EVAL_API")
    eval_runs_dir: Path = Field(
        default=Path("benchmarks/runs"), validation_alias="LUMEN_EVAL_RUNS_DIR"
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _parse_cors_origins(cls, v: object) -> list[str]:
        if isinstance(v, str):
            parts = [s.strip() for s in v.split(",") if s.strip()]
            return parts if parts else ["http://localhost:4200", "http://localhost:3000"]
        if isinstance(v, list):
            return [str(x).strip() for x in v if str(x).strip()]
        return ["http://localhost:4200", "http://localhost:3000"]
