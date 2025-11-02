"""Configuration for the runtime execution engine."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, validator


class RuntimeConfig(BaseModel):
    """Settings that control runtime behaviour."""

    workflow_path: Path = Field(default=Path(os.getenv("WORKFLOW_PATH", "config/workflow.yaml")))
    workflow_provider: str = Field(default=os.getenv("WORKFLOW_PROVIDER", "mock"))
    dify_endpoint: Optional[str] = Field(default=os.getenv("DIFY_API_ENDPOINT"))
    dify_api_key: Optional[str] = Field(default=os.getenv("DIFY_API_KEY"))
    redis_url: Optional[str] = Field(default=os.getenv("REDIS_URL"))
    session_ttl_seconds: int = Field(default=int(os.getenv("SESSION_TTL_SECONDS", "1800")))

    @validator("workflow_path", pre=True)
    def _expand_path(cls, value: str | Path) -> Path:  # noqa: D401 - short helper
        """Expand environment variables and resolve the path."""

        if isinstance(value, Path):
            return value
        return Path(value).expanduser().resolve()


@lru_cache(maxsize=1)
def runtime_config() -> RuntimeConfig:
    """Return cached runtime configuration."""

    return RuntimeConfig()


