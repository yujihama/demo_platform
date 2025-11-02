"""Configuration loading utilities for the demo platform backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, validator, model_validator


class FrontendSettings(BaseModel):
    base_url: str = Field(..., description="Base URL for the frontend wizard")
    polling_interval_seconds: int = Field(2, ge=1, le=10)


class BackendSettings(BaseModel):
    base_url: str = Field(..., description="Base URL for the backend API")
    log_level: str = Field("INFO")


class AgentSettings(BaseModel):
    use_mock: bool = Field(True, description="Whether to enable the mock agent pipeline")
    allow_llm_toggle: bool = Field(
        False,
        description="Whether the UI should expose a toggle to switch between mock and LLM modes",
    )
    mock_spec_path: Path = Field(..., description="Path to the mock specification JSON")

    @validator("mock_spec_path", pre=True)
    def _expand_path(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve()


class GenerationSettings(BaseModel):
    output_root: Path = Field(default=Path("./output"))
    package_name_template: str = Field(default="invoice-verification")
    enable_playwright: bool = Field(default=True)

    @validator("output_root", pre=True)
    def _expand_root(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve()


class FeatureConfig(BaseModel):
    phase: str = Field("mvp")
    agents: AgentSettings
    generation: GenerationSettings
    frontend: FrontendSettings
    backend: BackendSettings


class LLMDefaults(BaseModel):
    model: str
    temperature: float = 0.0


class LLMConfig(BaseModel):
    provider: str
    defaults: LLMDefaults
    mocks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    providers: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_active_provider(self) -> "LLMConfig":
        provider = self.provider
        if provider == "openai":
            config = self.providers.get("openai", {})
            OpenAIProviderConfig(**config)
        elif provider == "azure_openai":
            config = self.providers.get("azure_openai", {})
            AzureOpenAIProviderConfig(**config)
        return self

    def get_openai_config(self) -> "OpenAIProviderConfig":
        return OpenAIProviderConfig(**self.providers.get("openai", {}))

    def get_azure_openai_config(self) -> "AzureOpenAIProviderConfig":
        return AzureOpenAIProviderConfig(**self.providers.get("azure_openai", {}))


class BaseProviderConfig(BaseModel):
    enabled: bool = False


class OpenAIProviderConfig(BaseProviderConfig):
    api_key: Optional[str] = None
    organization: Optional[str] = None
    base_url: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None

    @model_validator(mode="after")
    def _check_required(cls, values: "OpenAIProviderConfig") -> "OpenAIProviderConfig":
        if values.enabled and not values.api_key:
            raise ValueError("OpenAI provider requires api_key when enabled")
        return values


class AzureOpenAIProviderConfig(BaseProviderConfig):
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    deployment: Optional[str] = None
    api_version: Optional[str] = Field(default="2024-05-01-preview")
    model: Optional[str] = None
    temperature: Optional[float] = None

    @model_validator(mode="after")
    def _check_required(cls, values: "AzureOpenAIProviderConfig") -> "AzureOpenAIProviderConfig":
        if not values.enabled:
            return values
        missing = [
            name
            for name in ("api_key", "endpoint", "deployment", "api_version")
            if not getattr(values, name)
        ]
        if missing:
            missing_str = ", ".join(missing)
            raise ValueError(f"Azure OpenAI provider missing required settings: {missing_str}")
        return values


class DifyEnvironmentConfig(BaseModel):
    base_url: str
    api_key: Optional[str] = None


class DifyConfig(BaseModel):
    mode: str = Field("mock")
    enabled: bool = False
    mock: DifyEnvironmentConfig
    production: DifyEnvironmentConfig


class ConfigBundle(BaseModel):
    features: FeatureConfig
    llm: LLMConfig
    dify: DifyConfig


class ConfigManager:
    """Load YAML configuration files into strongly typed models."""

    def __init__(
        self,
        features_path: Path = Path("config/features.yaml"),
        llm_path: Path = Path("config/llm.yaml"),
        dify_path: Path = Path("config/dify.yaml"),
    ) -> None:
        self._features_path = features_path
        self._llm_path = llm_path
        self._dify_path = dify_path
        self._bundle: Optional[ConfigBundle] = None

    # ------------------------------------------------------------------
    def load(self, force: bool = False) -> ConfigBundle:
        """Load config files and cache the resulting bundle."""

        if self._bundle is not None and not force:
            return self._bundle

        features = self._load_yaml(self._features_path)
        llm = self._load_yaml(self._llm_path)
        dify = self._load_yaml(self._dify_path)

        bundle = ConfigBundle(
            features=FeatureConfig(**features),
            llm=LLMConfig(**llm),
            dify=DifyConfig(**dify),
        )
        self._bundle = bundle
        return bundle

    # ------------------------------------------------------------------
    @property
    def features(self) -> FeatureConfig:
        return self.load().features

    @property
    def llm(self) -> LLMConfig:
        return self.load().llm

    @property
    def dify(self) -> DifyConfig:
        return self.load().dify

    # ------------------------------------------------------------------
    def export_metadata(self) -> Dict[str, Any]:
        bundle = self.load()
        return json.loads(bundle.model_dump_json())

    # ------------------------------------------------------------------
    @staticmethod
    def _load_yaml(path: Path) -> Dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        if not isinstance(data, dict):
            raise ValueError(f"Configuration file must contain a mapping: {path}")
        return data


config_manager = ConfigManager()


