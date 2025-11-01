from __future__ import annotations

import json
from pathlib import Path


def test_cli_generate_mock_packaging(cli_generation: Path) -> None:
    zip_path = cli_generation / "app.zip"
    metadata_path = cli_generation / "metadata.json"

    assert zip_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["mode"] == "mock"
    assert metadata["request"]["project_name"] == "Invoice Verification Assistant"
    assert metadata["mock_spec_id"] == "invoice-verification"
    assert "workflow_yaml" in metadata
    assert "generated_at" in metadata


def test_cli_generate_llm_packaging(cli_generation_llm: Path) -> None:
    zip_path = cli_generation_llm / "app.zip"
    metadata_path = cli_generation_llm / "metadata.json"

    assert zip_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["mode"] == "llm"
    assert metadata["request"]["use_mock"] is False
    assert "analysis" in metadata and metadata["analysis"]["primary_goal"]
    assert "plan" in metadata and metadata["plan"]["ui_steps"]
    assert metadata["workflow_yaml"].strip().startswith("version")


def test_cli_generate_llm_validation_attempts(cli_generation_validation_llm: Path) -> None:
    metadata_path = cli_generation_validation_llm / "metadata.json"
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["mode"] == "llm"
    attempts = metadata.get("attempts", [])
    assert attempts, "LLM ????????????????????????"
    assert all("errors" in attempt for attempt in attempts)

