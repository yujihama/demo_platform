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
        """
        Package a workflow.yaml-based application.
        
        Creates a zip file containing:
        - workflow.yaml
        - docker-compose.yml (generic template)
        - .env.example (template with placeholders)
        - README.md (instructions)
        """
        target_dir = self._output_root / job.user_id / job.project_id
        target_dir.mkdir(parents=True, exist_ok=True)
        
        zip_path = target_dir / "app.zip"
        
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zip_file:
            # Add workflow.yaml
            zip_file.writestr("workflow.yaml", workflow_yaml.encode("utf-8"))
            
            # Add docker-compose.yml (generic template)
            docker_compose_content = self._generate_docker_compose()
            zip_file.writestr("docker-compose.yml", docker_compose_content.encode("utf-8"))
            
            # Add .env.example
            env_example_content = self._generate_env_example()
            zip_file.writestr(".env.example", env_example_content.encode("utf-8"))
            
            # Add README.md
            readme_content = self._generate_readme(job.project_name, job.description)
            zip_file.writestr("README.md", readme_content.encode("utf-8"))
        
        # Save metadata
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
      BACKEND_URL: http://runtime-engine:8000
    ports:
      - "${RUNTIME_UI_PORT:-5173}:5173"
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
        return """# Runtime Engine
WORKFLOW_FILE=workflow.yaml
RUNTIME_ENGINE_PORT=8000
REDIS_URL=redis://redis:6379/0

# Runtime UI
RUNTIME_UI_PORT=5173

# Redis
REDIS_PORT=6379

# Optional: configure when using Dify provider
# WORKFLOW_PROVIDER=dify
# DIFY_API_ENDPOINT=https://api.dify.ai/v1
# DIFY_API_KEY=your-api-key-here
"""
    
    def _generate_readme(self, app_name: str, description: str) -> str:
        """Generate README.md with setup instructions."""
        return f"""# {app_name}

{description}

## 必要条件

- Docker と Docker Compose が利用可能であること

## セットアップ手順

1. 環境変数ファイルを作成します。
   ```bash
   cp .env.example .env
   ```

2. `.env` を編集し、必要に応じて以下を設定します。
   - `WORKFLOW_FILE`: 配布された `workflow.yaml` のパス (既定値で問題ない場合は変更不要)
   - `REDIS_URL`: Redis への接続先
   - Dify を利用する場合は `WORKFLOW_PROVIDER`, `DIFY_API_ENDPOINT`, `DIFY_API_KEY`

3. サービスを起動します。
   ```bash
   docker-compose up -d
   ```

4. ブラウザでアプリケーションにアクセスします。
   - UI: http://localhost:${{RUNTIME_UI_PORT:-5173}}
   - 実行エンジン API: http://localhost:${{RUNTIME_ENGINE_PORT:-8000}}

## 停止方法

```bash
docker-compose down
```

## 仕組み

`workflow.yaml` に記述された宣言的な設定をもとに、汎用実行エンジンと動的UIがアプリケーションを構成します。
設定を変更した場合は、`docker-compose restart` で再起動してください。
"""
