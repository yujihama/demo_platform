"""Input/Output utilities for workflow documents."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import WorkflowDocument


class WorkflowLoader:
    """Helper class to load workflow documents from YAML sources."""

    @staticmethod
    def from_yaml_text(text: str) -> WorkflowDocument:
        data = yaml.safe_load(text) or {}
        return WorkflowDocument.model_validate(data)

    @staticmethod
    def from_file(path: Path) -> WorkflowDocument:
        text = path.read_text(encoding="utf-8")
        return WorkflowLoader.from_yaml_text(text)


class WorkflowSerializer:
    """Serialize workflow documents into YAML string."""

    @staticmethod
    def to_yaml(document: WorkflowDocument) -> str:
        data = document.model_dump(mode="json")
        return yaml.safe_dump(data, sort_keys=False, allow_unicode=True)

    @staticmethod
    def to_file(document: WorkflowDocument, path: Path) -> None:
        yaml_text = WorkflowSerializer.to_yaml(document)
        path.write_text(yaml_text, encoding="utf-8")

