"""Simple FastAPI server that emulates the minimal Dify workflow endpoint."""

from __future__ import annotations

import random
from datetime import datetime
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class WorkflowRequest(BaseModel):
    inputs: Dict[str, Any]


class WorkflowResponse(BaseModel):
    workflow_id: str
    requested_at: datetime
    outputs: Dict[str, Any]


app = FastAPI(title="Dify Mock Server", version="0.1.0")


@app.post("/v1/workflows/{workflow_id}/run", response_model=WorkflowResponse)
async def run_workflow(workflow_id: str, payload: WorkflowRequest) -> WorkflowResponse:
    inputs = payload.inputs
    if "invoice_csv" not in inputs:
        raise HTTPException(status_code=400, detail="invoice_csv input is required")

    rows = [row for row in inputs["invoice_csv"].splitlines() if row.strip()]
    total_amount = 0.0
    line_items = []
    for row in rows:
        columns = [column.strip() for column in row.split(",")]
        if len(columns) < 3:
            continue
        name, quantity, amount = columns[0], columns[1], columns[2]
        try:
            amount_value = float(amount)
        except ValueError:
            amount_value = 0.0
        total_amount += amount_value
        line_items.append({
            "field": name,
            "value": f"数量:{quantity} 金額:{amount}",
        })

    line_items.append({"field": "行数", "value": str(len(rows))})
    line_items.append({"field": "合計金額", "value": f"{total_amount:.2f}"})

    outputs = {
        "status": "success",
        "items": line_items,
        "seed": random.randint(1, 9999),
    }

    return WorkflowResponse(
        workflow_id=workflow_id,
        requested_at=datetime.utcnow(),
        outputs=outputs,
    )


