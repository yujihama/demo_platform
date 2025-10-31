"""Provide mock preview assets for the frontend wizard."""

from __future__ import annotations

from pathlib import Path


class MockPreviewService:
    def __init__(self, preview_root: Path) -> None:
        self._preview_root = preview_root

    def get_preview_html(self, spec_id: str) -> str:
        file_path = self._resolve_preview_path(spec_id)
        return file_path.read_text(encoding="utf-8")

    def _resolve_preview_path(self, spec_id: str) -> Path:
        # For Phase 1 we map spec id directly to a single HTML asset
        candidate = self._preview_root / f"{spec_id}_preview.html"
        if candidate.exists():
            return candidate
        default_path = self._preview_root / "invoice_preview.html"
        if not default_path.exists():
            raise FileNotFoundError(f"Preview asset not found for {spec_id}")
        return default_path

