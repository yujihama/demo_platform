from __future__ import annotations

from io import BytesIO
from pathlib import Path

import httpx
import pytest
from starlette.datastructures import UploadFile

from backend.app.runtime.engine import WorkflowEngine, load_workflow
from backend.app.runtime.state import InMemoryStateStore


@pytest.mark.asyncio
async def test_workflow_engine_executes_invoice_pipeline() -> None:
    workflow = load_workflow(Path("config/workflow.yaml"))

    async def handler(request: httpx.Request) -> httpx.Response:
        payload_bytes = request.content or b"{}"
        payload_dict = httpx.Response(200, content=payload_bytes).json()
        invoice_csv = payload_dict.get("inputs", {}).get("invoice_csv", "")
        lines = [line for line in invoice_csv.splitlines() if line.strip()]
        items = []
        total = 0.0
        for line in lines[1:]:
            name, quantity, unit_price = line.split(",")
            quantity_value = int(quantity)
            unit_price_value = float(unit_price)
            amount = quantity_value * unit_price_value
            total += amount
            items.append(
                {
                    "name": name,
                    "quantity": quantity_value,
                    "unit_price": unit_price_value,
                    "amount": amount,
                }
            )
        return httpx.Response(
            200,
            json={
                "workflow_id": "invoice-processor",
                "data": {
                    "items": items,
                    "summary": {
                        "total_amount": total,
                        "line_item_count": len(items),
                        "currency": "JPY",
                    },
                },
            },
        )

    engine = WorkflowEngine(
        workflow=workflow,
        state_store=InMemoryStateStore(),
        session_ttl=3600,
        call_workflow_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler)),
    )

    initial = await engine.create_session()
    assert initial.status == "awaiting_input"
    assert initial.active_ui_step == "upload"

    csv_content = "item,quantity,unit_price\nA,2,100\nB,1,50\n"
    upload_file = UploadFile(filename="invoice.csv", file=BytesIO(csv_content.encode("utf-8")))

    result = await engine.submit_step(initial.session_id, "upload_invoice", {}, upload_file)
    assert result.status == "completed"
    assert result.active_ui_step == "results"
    items = result.context.get("invoice_items")
    assert isinstance(items, list)
    assert len(items) == 2
    assert result.context["raw_response"]["summary"]["total_amount"] == pytest.approx(250)

    await engine.shutdown()
