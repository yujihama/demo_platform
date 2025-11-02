"""Minimal FastAPI application that emulates a subset of Dify workflows."""

from __future__ import annotations

import base64
import binascii
import csv
import io
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="Dify Mock Server", version="1.0.0")


class WorkflowRequest(BaseModel):
    file_name: str = Field(..., description="Uploaded file name")
    file_content_b64: str = Field(..., description="Base64 encoded file contents")


class WorkflowResponse(BaseModel):
    items: List[Dict[str, Any]]
    summary: Dict[str, Any]


def _decode_csv(content_b64: str) -> List[Dict[str, str]]:
    try:
        raw = base64.b64decode(content_b64)
    except (ValueError, binascii.Error) as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 payload") from exc

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Uploaded file must be UTF-8 text") from exc

    reader = csv.DictReader(io.StringIO(text))
    rows = [row for row in reader]
    if not rows:
        raise HTTPException(status_code=400, detail="Uploaded CSV does not contain any rows")
    return rows


@app.post("/api/v1/workflows/invoice-validator/run", response_model=WorkflowResponse)
async def run_invoice_validator(request: WorkflowRequest) -> WorkflowResponse:
    rows = _decode_csv(request.file_content_b64)

    results: List[Dict[str, Any]] = []
    invalid_count = 0
    for row in rows:
        amount = row.get("amount")
        invoice_number = row.get("invoice_number") or row.get("invoice")
        vendor = row.get("vendor")
        status = "ok"
        notes: List[str] = []

        if not invoice_number:
            status = "error"
            notes.append("Missing invoice number")
        if not amount:
            status = "error"
            notes.append("Missing amount")
        else:
            try:
                value = float(amount)
                if value <= 0:
                    status = "warning"
                    notes.append("Amount must be positive")
            except ValueError:
                status = "error"
                notes.append("Amount is not numeric")

        if status != "ok":
            invalid_count += 1

        results.append(
            {
                "invoice_number": invoice_number or "UNKNOWN",
                "vendor": vendor or "",
                "amount": amount or "",
                "status": status,
                "notes": "; ".join(notes) if notes else "",
            }
        )

    summary = {
        "total": len(results),
        "invalid": invalid_count,
        "valid": len(results) - invalid_count,
    }

    return WorkflowResponse(items=results, summary=summary)


if __name__ == "__main__":  # pragma: no cover - manual execution helper
    import os
    import uvicorn

    port = int(os.environ.get("MOCK_SERVER_PORT", "8001"))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
