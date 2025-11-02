"""Packaging service for workflow.yaml-based applications."""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any, Dict

from ..models.generation import GenerationJob


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
    ) -> Path:
        return self._package(
            user_id=job.user_id,
            project_id=job.project_id,
            project_name=job.project_name,
            description=job.description,
            workflow_yaml=workflow_yaml,
            metadata=metadata,
        )

    def package_conversation(
        self,
        *,
        session_id: str,
        user_id: str,
        project_id: str,
        project_name: str,
        description: str,
        workflow_yaml: str,
        metadata: Dict[str, Any] | None = None,
    ) -> Path:
        return self._package(
            user_id=user_id,
            project_id=project_id,
            project_name=project_name,
            description=description,
            workflow_yaml=workflow_yaml,
            metadata=metadata,
            zip_name=f"{session_id}.zip",
        )

    def _package(
        self,
        *,
        user_id: str,
        project_id: str,
        project_name: str,
        description: str,
        workflow_yaml: str,
        metadata: Dict[str, Any] | None = None,
        zip_name: str = "app.zip",
    ) -> Path:
        target_dir = self._output_root / user_id / project_id
        target_dir.mkdir(parents=True, exist_ok=True)

        zip_path = target_dir / zip_name

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr("workflow.yaml", workflow_yaml.encode("utf-8"))
            zip_file.writestr("docker-compose.yml", self._generate_docker_compose().encode("utf-8"))
            zip_file.writestr(".env.example", self._generate_env_example().encode("utf-8"))
            zip_file.writestr("README.md", self._generate_readme(project_name, description).encode("utf-8"))

        if metadata:
            metadata_path = target_dir / "metadata.json"
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        return zip_path
    
    def _generate_docker_compose(self) -> str:
        """Generate generic docker-compose.yml for workflow apps."""
        return """version: "3.9"

services:
  runtime-engine:
    image: ghcr.io/demo-platform/runtime-engine:latest
    env_file:
      - .env
    environment:
      WORKFLOW_FILE: ${WORKFLOW_FILE:-/app/workflow.yaml}
      REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
    volumes:
      - ./workflow.yaml:/app/workflow.yaml:ro
    ports:
      - "${RUNTIME_ENGINE_PORT:-8000}:8000"
    depends_on:
      - redis

  runtime-ui:
    image: ghcr.io/demo-platform/runtime-ui:latest
    env_file:
      - .env
    environment:
      VITE_RUNTIME_API_URL: ${RUNTIME_API_URL:-http://runtime-engine:8000/api/runtime}
    ports:
      - "${RUNTIME_UI_PORT:-3000}:3000"
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
WORKFLOW_FILE=workflow.yaml
REDIS_URL=redis://redis:6379/0
RUNTIME_ENGINE_PORT=8000

# Runtime UI Configuration
RUNTIME_UI_PORT=3000
RUNTIME_API_URL=http://runtime-engine:8000/api/runtime

# Redis Configuration
REDIS_PORT=6379

# Optional: configure external providers (e.g. Dify)
# WORKFLOW_PROVIDER=dify
# DIFY_API_ENDPOINT=https://api.dify.ai/v1
# DIFY_API_KEY=your-api-key-here
"""
    
    def _generate_readme(self, app_name: str, description: str) -> str:
        """Generate README.md with setup instructions."""
        return f"""# {app_name}

{description}

## 使い方

1. `.env.example` をコピーして `.env` を作成します。
   ```bash
   cp .env.example .env
   ```

2. `.env` に必要な環境変数（APIキーなど）を設定します。

3. アプリケーションを起動します。
   ```bash
   docker-compose up
   ```

4. ブラウザで http://localhost:3000 を開き、生成されたアプリケーションを操作します。

アプリの動作は `workflow.yaml` によって制御されます。内容を変更した場合は再度 `docker-compose up` を実行してください。
"""
