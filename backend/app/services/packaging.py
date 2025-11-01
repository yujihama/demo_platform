"""Packaging utilities for declarative workflow artifacts."""

from __future__ import annotations

import json
import shutil
import uuid
import zipfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from ..models import PackageCreateRequest, PackageCreateResponse, PackageDescriptor


class PackageRegistry:
    """In-memory registry tracking packaged artifacts for download."""

    def __init__(self) -> None:
        self._storage: dict[str, tuple[PackageDescriptor, Path]] = {}

    def register(self, descriptor: PackageDescriptor, archive_path: Path) -> None:
        self._storage[descriptor.package_id] = (descriptor, archive_path)

    def get(self, package_id: str) -> tuple[PackageDescriptor, Path] | None:
        return self._storage.get(package_id)


class PackagingService:
    """Renders workflow packages containing docker-compose and runtime assets."""

    def __init__(
        self,
        output_root: Path | None = None,
        assets_dir: Path | None = None,
        registry: PackageRegistry | None = None,
    ) -> None:
        self._output_root = output_root or Path("output/packages")
        self._output_root.mkdir(parents=True, exist_ok=True)
        default_assets = Path(__file__).resolve().parent / "package_assets"
        self._assets_dir = assets_dir or default_assets
        self._registry = registry or PackageRegistry()

    @property
    def registry(self) -> PackageRegistry:
        return self._registry

    def create_package(self, request: PackageCreateRequest) -> PackageCreateResponse:
        package_id = uuid.uuid4().hex
        created_at = datetime.utcnow()
        expires_at = created_at + timedelta(days=7)

        working_dir = self._output_root / package_id
        working_dir.mkdir(parents=True, exist_ok=True)

        self._copy_assets(working_dir, include_mock=request.include_mock_server)

        workflow_path = working_dir / "workflow.yaml"
        workflow_path.write_text(request.workflow_yaml, encoding="utf-8")

        metadata_path = working_dir / "metadata.json"
        metadata_path.write_text(
            json.dumps(
                {
                    "app_name": request.app_name,
                    "created_at": created_at.isoformat(),
                    "include_mock_server": request.include_mock_server,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        self._render_env_file(working_dir, request.environment_variables)

        archive_path = self._output_root / f"{package_id}.zip"
        self._archive_directory(working_dir, archive_path)

        descriptor = PackageDescriptor(
            package_id=package_id,
            filename=f"{request.app_name.replace(' ', '_') or 'app'}-package.zip",
            download_url=f"/api/packages/{package_id}/download",
            created_at=created_at,
            expires_at=expires_at,
            size_bytes=archive_path.stat().st_size,
        )

        self._registry.register(descriptor, archive_path)

        return PackageCreateResponse(package=descriptor)

    # ------------------------------------------------------------------
    def _copy_assets(self, destination: Path, include_mock: bool) -> None:
        for item in self._assets_dir.iterdir():
            if not include_mock and item.name.startswith("mock-server"):
                continue
            target = destination / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)

    def _render_env_file(self, destination: Path, extra_variables: Dict[str, str]) -> None:
        template_path = destination / ".env.template"
        env_path = destination / ".env"

        template_content = ""
        if template_path.exists():
            template_content = template_path.read_text(encoding="utf-8")

        lines = [line for line in template_content.splitlines() if line.strip()]

        for key, value in sorted(extra_variables.items()):
            lines.append(f"{key}={value}")

        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        if template_path.exists():
            template_path.unlink()

    def _archive_directory(self, src: Path, archive_path: Path) -> None:
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in src.rglob("*"):
                if file_path.is_file():
                    arcname = file_path.relative_to(src).as_posix()
                    zip_file.write(file_path, arcname)


packaging_registry = PackageRegistry()
packaging_service = PackagingService(registry=packaging_registry)


