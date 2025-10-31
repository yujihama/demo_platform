"""Utility for loading UI parts catalog."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


def load_ui_parts_catalog(catalog_path: Path | str | None = None) -> Dict[str, Any]:
    """Load UI parts catalog from YAML file."""
    if catalog_path is None:
        catalog_path = Path("config/ui_parts_catalog.yaml")

    if isinstance(catalog_path, str):
        catalog_path = Path(catalog_path)

    if not catalog_path.exists():
        logger.warning("UI parts catalog not found at %s, returning empty catalog", catalog_path)
        return {"components": []}

    with catalog_path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    if not isinstance(data, dict):
        raise ValueError(f"UI parts catalog must be a YAML mapping: {catalog_path}")

    logger.info("Loaded UI parts catalog from %s (%d components)", catalog_path, len(data.get("components", [])))
    return data


# Create a singleton instance
_catalog_cache: Dict[str, Any] | None = None


def get_ui_parts_catalog() -> Dict[str, Any]:
    """Get the UI parts catalog (cached)."""
    global _catalog_cache
    if _catalog_cache is None:
        _catalog_cache = load_ui_parts_catalog()
    return _catalog_cache
