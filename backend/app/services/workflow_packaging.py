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
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    command: npm run dev -- --host 0.0.0.0 --port ${FRONTEND_PORT:-5173}
    env_file:
      - .env
    environment:
      BACKEND_HOST: http://backend:8000
    volumes:
      - ./frontend:/app
      - node_modules:/app/node_modules
    ports:
      - "${FRONTEND_PORT:-5173}:5173"
    depends_on:
      - backend

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    command: uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT:-8000}
    env_file:
      - .env
    volumes:
      - ./backend:/app
      - ./workflow.yaml:/app/workflow.yaml:ro
    ports:
      - "${BACKEND_PORT:-8000}:8000"
    depends_on:
      - redis

  redis:
    image: redis:7-alpine
    ports:
      - "${REDIS_PORT:-6379}:6379"
    volumes:
      - redis_data:/data

volumes:
  node_modules: {}
  redis_data: {}
"""
    
    def _generate_env_example(self) -> str:
        """Generate .env.example template."""
        return """# Backend Configuration
BACKEND_PORT=8000

# Frontend Configuration
FRONTEND_PORT=5173

# Redis Configuration
REDIS_PORT=6379

# Workflow Provider Configuration
WORKFLOW_PROVIDER=mock
# For production, set to 'dify' and configure:
# WORKFLOW_PROVIDER=dify
# DIFY_API_ENDPOINT=https://api.dify.ai/v1
# DIFY_API_KEY=your-api-key-here

# Dify API Configuration (if using dify provider)
# DIFY_API_ENDPOINT=https://api.dify.ai/v1
# DIFY_API_KEY=your-api-key-here
"""
    
    def _generate_readme(self, app_name: str, description: str) -> str:
        """Generate README.md with setup instructions."""
        return f"""# {app_name}

{description}

## Setup

1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and configure:
   - Set `WORKFLOW_PROVIDER` to `dify` for production (or keep `mock` for development)
   - If using Dify, add your `DIFY_API_KEY` and `DIFY_API_ENDPOINT`

3. Start the application:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000

## Stopping the Application

```bash
docker-compose down
```

## Configuration

The application behavior is controlled by `workflow.yaml`. 
This file defines:
- Application metadata
- UI structure and components
- Processing pipeline steps
- External API endpoints (workflows)

To modify the application, edit `workflow.yaml` and restart the services.
"""
