"""Packaging service for workflow.yaml-based applications."""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from ..models.generation import GenerationJob


@dataclass(frozen=True)
class WorkflowPackageArtifact:
    """Metadata about the packaged workflow artifacts."""

    zip_path: Path
    workflow_path: Path
    docker_compose_path: Path
    readme_path: Path
    metadata_path: Optional[Path]


class WorkflowPackagingService:
    """Packages workflow.yaml-based applications with docker-compose.yml and .env templates."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root
        self._output_root.mkdir(parents=True, exist_ok=True)

    def package_workflow_app(
        self,
        job: GenerationJob,
        workflow_yaml: str,
        metadata: Dict[str, Any] | None = None,
    ) -> WorkflowPackageArtifact:
        """Package a workflow.yaml-based application.

        Creates a directory per session containing the generated files and
        archives them into a distributable zip file.
        """
        target_dir = self._output_root / job.job_id
        if target_dir.exists():
            for child in target_dir.iterdir():
                if child.is_file():
                    child.unlink()
        target_dir.mkdir(parents=True, exist_ok=True)

        workflow_path = target_dir / "workflow.yaml"
        workflow_path.write_text(workflow_yaml, encoding="utf-8")

        docker_compose_content = self._generate_docker_compose()
        docker_compose_path = target_dir / "docker-compose.yml"
        docker_compose_path.write_text(docker_compose_content, encoding="utf-8")

        env_example_content = self._generate_env_example()
        (target_dir / ".env.example").write_text(env_example_content, encoding="utf-8")

        readme_content = self._generate_readme(job.project_name, job.description)
        readme_path = target_dir / "README.md"
        readme_path.write_text(readme_content, encoding="utf-8")

        metadata_path: Optional[Path] = None
        if metadata:
            metadata_path = target_dir / "metadata.json"
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        zip_path = target_dir / "app.zip"
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.write(workflow_path, arcname="workflow.yaml")
            zip_file.write(docker_compose_path, arcname="docker-compose.yml")
            zip_file.write(target_dir / ".env.example", arcname=".env.example")
            zip_file.write(readme_path, arcname="README.md")
            if metadata_path is not None:
                zip_file.write(metadata_path, arcname="metadata.json")

        return WorkflowPackageArtifact(
            zip_path=zip_path,
            workflow_path=workflow_path,
            docker_compose_path=docker_compose_path,
            readme_path=readme_path,
            metadata_path=metadata_path,
        )

    def _generate_docker_compose(self) -> str:
        """Generate docker-compose.yml template for runtime engine distribution."""

        return """version: "3.9"

services:
  runtime-engine:
    image: ${RUNTIME_ENGINE_IMAGE:-ghcr.io/demo-platform/runtime-engine:latest}
    environment:
      WORKFLOW_FILE: /app/workflow.yaml
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
    volumes:
      - ./workflow.yaml:/app/workflow.yaml:ro
    ports:
      - "${RUNTIME_ENGINE_PORT:-8000}:8000"
    depends_on:
      - redis

  runtime-ui:
    image: ${RUNTIME_UI_IMAGE:-ghcr.io/demo-platform/runtime-ui:latest}
    environment:
      RUNTIME_API_URL: http://runtime-engine:8000
    ports:
      - "${RUNTIME_UI_PORT:-4173}:4173"
    depends_on:
      - runtime-engine

  redis:
    image: redis:7-alpine
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data: {}
"""

    def _generate_env_example(self) -> str:
        """Generate .env.example template."""

        return """# Runtime Engine Configuration
RUNTIME_ENGINE_IMAGE=ghcr.io/demo-platform/runtime-engine:latest
RUNTIME_ENGINE_PORT=8000
REDIS_URL=redis://redis:6379/0

# Runtime UI Configuration
RUNTIME_UI_IMAGE=ghcr.io/demo-platform/runtime-ui:latest
RUNTIME_UI_PORT=4173

# Redis Configuration
REDIS_PORT=6379
"""

    def _generate_readme(self, app_name: str, description: str) -> str:
        """Generate README.md with minimal setup instructions."""

        details = description.strip() or "このアプリケーションは workflow.yaml に基づいて動作します。"
        return f"""# {app_name}

{details}

## セットアップ手順

1. `.env.example` を `.env` にコピーし、必要に応じてイメージ名やポートを調整します。

   ```bash
   cp .env.example .env
   ```

2. Docker Compose でサービスを起動します。

   ```bash
   docker-compose up -d
   ```

3. ブラウザでランタイム UI にアクセスします。

   - http://localhost:${{RUNTIME_UI_PORT:-4173}}

4. アプリの動作が完了したら、次のコマンドで停止します。

   ```bash
   docker-compose down
   ```

このパッケージに含まれる `workflow.yaml` を編集することで、アプリの挙動を変更できます。
"""
