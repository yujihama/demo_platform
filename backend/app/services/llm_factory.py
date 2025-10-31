"""Mock-friendly LLM factory for Phase 1."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from ..config import ConfigManager, config_manager
from .mock_agent import MockAgent


class LLMFactory:
    def __init__(self, cfg: ConfigManager = config_manager) -> None:
        self._cfg = cfg

    def create_mock_agent(self, spec_id: str) -> MockAgent:
        llm_cfg = self._cfg.llm
        mock_entry: Dict[str, Any] = llm_cfg.mocks.get(spec_id) or {}
        response_path = mock_entry.get("response_path") or self._cfg.features.agents.mock_spec_path
        return MockAgent(Path(response_path).parent if Path(response_path).is_file() else Path(response_path))


llm_factory = LLMFactory()

