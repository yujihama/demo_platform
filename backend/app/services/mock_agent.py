"""Mock agent that returns deterministic specifications from JSON files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class MockAgent:
    def __init__(self, spec_root: Path) -> None:
        self._spec_root = spec_root

    def generate_spec(self, spec_id: str) -> Dict[str, Any]:
        if self._spec_root.is_file():
            file_path = self._spec_root
        else:
            file_path = self._spec_root / f"{spec_id}.json"
        if not file_path.exists():
            raise FileNotFoundError(f"Mock spec not found: {file_path}")
        with file_path.open("r", encoding="utf-8") as fh:
            return json.load(fh)

