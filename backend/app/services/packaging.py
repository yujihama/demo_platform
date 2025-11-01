"""Packaging utilities for workflow-based artifacts."""

from __future__ import annotations

import json
import textwrap
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable

from ..models.generation import GenerationJob


class PackagingService:
    """Create distributable zip archives containing workflow.yaml and runtime assets."""

    def __init__(self, output_root: Path, asset_root: Path | None = None) -> None:
        self._output_root = output_root
        self._output_root.mkdir(parents=True, exist_ok=True)
        if asset_root is None:
            asset_root = Path(__file__).resolve().parents[1] / "assets" / "package"
        self._asset_root = asset_root

    def package(
        self,
        job: GenerationJob,
        workflow_yaml: str,
        metadata: Dict[str, Any],
        notes: Iterable[str] | None = None,
    ) -> Path:
        target_dir = self._output_root / job.user_id / job.project_id
        target_dir.mkdir(parents=True, exist_ok=True)

        zip_path = target_dir / "app.zip"
        notes_text = self._format_notes(notes)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            # Generated artifacts
            zip_file.writestr("workflow.yaml", workflow_yaml)
            zip_file.writestr("NOTES.md", notes_text)

            # Static runtime assets (docker-compose, env template, etc.)
            if self._asset_root.exists():
                for file_path in self._asset_root.rglob("*"):
                    if file_path.is_file():
                        arcname = file_path.relative_to(self._asset_root)
                        zip_file.write(file_path, arcname.as_posix())

            # Embed metadata for convenience
            metadata_text = json.dumps(metadata, ensure_ascii=False, indent=2)
            zip_file.writestr("metadata.json", metadata_text)

        # Also store metadata.json alongside the archive for API consumption
        metadata_path = target_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        return zip_path

    @staticmethod
    def _format_notes(notes: Iterable[str] | None) -> str:
        lines = ["# Workflow Generation Notes", ""]
        if not notes:
            lines.append("- ??????????????")
        else:
            for item in notes:
                cleaned = textwrap.dedent(str(item)).strip()
                lines.append(f"- {cleaned}")
        lines.append("")
        lines.append("????????? workflow.yaml ? docker-compose.yml/.env.example ?????????")
        return "\n".join(lines)

