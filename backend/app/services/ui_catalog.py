"""Utility for loading UI component catalog definitions."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

import yaml
from pydantic import BaseModel, Field


class UIComponentPropDefinition(BaseModel):
    type: str
    required: bool = False
    items: str | None = None


class UIComponentDefinition(BaseModel):
    id: str
    name: str
    category: str
    description: str | None = None
    applicable_app_types: list[str] = Field(default_factory=list)
    props: Dict[str, UIComponentPropDefinition] = Field(default_factory=dict)

    def supports_app_type(self, app_type: str) -> bool:
        if not self.applicable_app_types:
            return True
        return app_type in self.applicable_app_types


class UIPartsCatalog(BaseModel):
    components: Dict[str, UIComponentDefinition] = Field(default_factory=dict)

    def get(self, component_id: str) -> UIComponentDefinition:
        try:
            return self.components[component_id]
        except KeyError as exc:  # pragma: no cover - raised for invalid configs
            raise KeyError(f"Component '{component_id}' is not defined in the catalog") from exc

    def has(self, component_id: str) -> bool:
        return component_id in self.components


@lru_cache(maxsize=1)
def load_ui_catalog(path: Path | str = Path("config/ui_parts_catalog.yaml")) -> UIPartsCatalog:
    catalog_path = Path(path)
    if not catalog_path.exists():
        raise FileNotFoundError(f"UI parts catalog not found: {catalog_path}")

    with catalog_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    components_data = raw.get("components", [])
    components: Dict[str, UIComponentDefinition] = {}
    for item in components_data:
        component = UIComponentDefinition(**item)
        components[component.id] = component

    return UIPartsCatalog(components=components)

