"""Packaging utilities for generated artifacts."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict

from ..models.generation import GenerationJob


class PackagingService:
    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root
        self._output_root.mkdir(parents=True, exist_ok=True)

    def package(self, job: GenerationJob, source_dir: Path, metadata: Dict[str, Any]) -> Path:
        target_dir = self._output_root / job.user_id / job.project_id
        target_dir.mkdir(parents=True, exist_ok=True)

        zip_path = target_dir / "app.zip"

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in source_dir.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(source_dir)
                    zip_file.write(file_path, arcname.as_posix())

        metadata_path = target_dir / "metadata.json"
        metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        return zip_path

