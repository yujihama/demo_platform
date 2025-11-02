"""FastAPI application that emulates a subset of the Dify workflow API."""

from __future__ import annotations

import csv
from io import StringIO
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class WorkflowInvokeRequest(BaseModel):
    """Subset of the Dify workflow invoke payload."""

    inputs: Dict[str, Any] = Field(default_factory=dict)


def create_mock_app() -> FastAPI:
    app = FastAPI(title="Dify Mock Server", version="1.0.0")

    @app.get("/health")
    async def healthcheck() -> Dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/workflows/{workflow_id}/invoke")
    async def invoke_workflow(workflow_id: str, payload: WorkflowInvokeRequest) -> Dict[str, Any]:
        if workflow_id == "invoice-processor":
            return {
                "workflow_id": workflow_id,
                "data": _handle_invoice_workflow(payload.inputs),
            }
        return {
            "workflow_id": workflow_id,
            "data": {"echo": payload.inputs},
        }

    return app


def _handle_invoice_workflow(inputs: Dict[str, Any]) -> Dict[str, Any]:
    invoice_csv = inputs.get("invoice_csv")
    if not invoice_csv:
        raise HTTPException(status_code=400, detail="invoice_csv フィールドが必要です。")

    reader = csv.DictReader(StringIO(invoice_csv))
    items: List[Dict[str, Any]] = []
    total_amount = 0.0

    for row in reader:
        name = (row.get("item") or "").strip()
        if not name:
            continue
        quantity = _safe_int(row.get("quantity"), default=1)
        unit_price = _safe_float(row.get("unit_price"), default=0.0)
        amount = quantity * unit_price
        total_amount += amount
        items.append(
            {
                "name": name,
                "quantity": quantity,
                "unit_price": unit_price,
                "amount": amount,
            }
        )

    summary = {
        "line_item_count": len(items),
        "total_amount": round(total_amount, 2),
        "currency": inputs.get("currency", "JPY"),
    }

    return {
        "items": items,
        "summary": summary,
    }


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value) if value is not None and value != "" else default
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value) if value is not None and value != "" else default
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return default


app = create_mock_app()
