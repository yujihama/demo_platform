"""API router definitions for the declarative workflow backend."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from .config import config_manager
from .models import (
    PackageCreateRequest,
    PackageCreateResponse,
    WorkflowGenerationRequest,
    WorkflowGenerationResponse,
)
from .services.packaging import packaging_service, packaging_registry
from .services.workflow_generation import workflow_generation_service


router = APIRouter(prefix="/api", tags=["workflows"])


@router.post("/workflows/generate", response_model=WorkflowGenerationResponse)
async def generate_workflow(payload: WorkflowGenerationRequest) -> WorkflowGenerationResponse:
    return workflow_generation_service.generate(payload)


@router.post("/packages", response_model=PackageCreateResponse)
async def create_package(payload: PackageCreateRequest) -> PackageCreateResponse:
    return packaging_service.create_package(payload)


@router.get("/packages/{package_id}/download")
async def download_package(package_id: str) -> FileResponse:
    entry = packaging_registry.get(package_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Package not found")
    descriptor, path = entry
    return FileResponse(path=path, filename=descriptor.filename, media_type="application/zip")


@router.get("/config/features")
async def get_features_config() -> dict:
    features = config_manager.features
    return {
        "default_mock": features.agents.use_mock,
        "frontend": {
            "base_url": features.frontend.base_url,
        },
        "backend": {
            "base_url": features.backend.base_url,
        },
    }

