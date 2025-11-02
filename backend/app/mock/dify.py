"""FastAPI router providing a lightweight Dify mock server."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from uuid import uuid4

from fastapi import APIRouter, Body

router = APIRouter(prefix="/mock/dify", tags=["dify-mock"])


@router.get("/health")
def healthcheck() -> Dict[str, str]:
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


@router.post("/v1/workflows/{workflow_id}/run")
async def run_workflow(workflow_id: str, payload: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    inputs = payload.get("inputs") or {}
    metadata = payload.get("metadata") or {}

    items = []
    for key, value in inputs.items():
        detail = ""
        if isinstance(value, dict) and "name" in value:
            detail = f"ファイル {value['name']} を受信しました"
        elif isinstance(value, str):
            detail = f"入力値: {value}"[:80]
        else:
            detail = "入力を受信しました"
        items.append({"field": key, "status": "ok", "detail": detail})

    return {
        "workflow_run_id": str(uuid4()),
        "workflow_id": workflow_id,
        "status": "succeeded",
        "outputs": {
            "message": f"Mock execution completed for {workflow_id}",
            "inputs": inputs,
            "items": items,
        },
        "metadata": metadata,
        "echo": {
            key: value for key, value in inputs.items()
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
