"""Configuration loading utilities for the demo platform backend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field, validator


class FrontendSettings(BaseModel):
    base_url: str = Field(..., description="Base URL for the frontend wizard")
    polling_interval_seconds: int = Field(2, ge=1, le=10)


class BackendSettings(BaseModel):
    base_url: str = Field(..., description="Base URL for the backend API")
    log_level: str = Field("INFO")


class AgentSettings(BaseModel):
    use_mock: bool = Field(True, description="Whether to enable the mock agent pipeline")
    mock_spec_path: Path = Field(..., description="Path to the mock specification JSON")

    @validator("mock_spec_path", pre=True)
    def _expand_path(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve()


class GenerationSettings(BaseModel):
    output_root: Path = Field(default=Path("./output"))
    template_root: Path = Field(default=Path("./templates"))
    package_name_template: str = Field(default="invoice-verification")
    enable_playwright: bool = Field(default=True)

    @validator("output_root", "template_root", pre=True)
    def _expand_root(cls, value: Any) -> Path:
        return Path(value).expanduser().resolve()


class FeatureConfig(BaseModel):
    phase: str = Field("mvp")
    agents: AgentSettings
    generation: GenerationSettings
    frontend: FrontendSettings
    backend: BackendSettings


class LLMProviderConfig(BaseModel):
    enabled: bool = False
    api_key: Optional[str] = None


class AzureOpenAIProviderConfig(LLMProviderConfig):
    endpoint: Optional[str] = None
    deployment_name: Optional[str] = None
    api_version: str = "2024-02-15-preview"


class LLMDefaults(BaseModel):
    model: str
    temperature: float = 0.0


class LLMConfig(BaseModel):
    provider: str
    defaults: LLMDefaults
    mocks: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    providers: Dict[str, Any] = Field(default_factory=dict)  # Can be LLMProviderConfig or AzureOpenAIProviderConfig


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
        llm_raw = self._load_yaml(self._llm_path)
        dify = self._load_yaml(self._dify_path)

        # Convert provider configs to appropriate types
        providers: Dict[str, Any] = {}
        if "providers" in llm_raw:
            for key, value in llm_raw["providers"].items():
                if key == "azure_openai":
                    providers[key] = AzureOpenAIProviderConfig(**value)
                else:
                    providers[key] = LLMProviderConfig(**value)
        llm_raw["providers"] = providers

        bundle = ConfigBundle(
            features=FeatureConfig(**features),
            llm=LLMConfig(**llm_raw),
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


