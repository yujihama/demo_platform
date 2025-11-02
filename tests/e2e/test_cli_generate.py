from __future__ import annotations

import json
from pathlib import Path


def test_cli_generate_produces_artifacts(cli_generation: Path) -> None:
    zip_path = cli_generation / "app.zip"
    metadata_path = cli_generation / "metadata.json"

    assert zip_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["request"]["project_name"] == "Invoice Verification Assistant"
    assert metadata["spec"]["app"]["slug"] == "invoice-verification"
    assert metadata["request"]["use_mock"] is True
    assert metadata["request"]["requirements_prompt"].startswith("Generate an invoice validation assistant")


def test_cli_generate_llm_pipeline(cli_generation_llm: Path) -> None:
    zip_path = cli_generation_llm / "app.zip"
    metadata_path = cli_generation_llm / "metadata.json"

    assert zip_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["analysis"]["summary"].startswith("Automated")
    assert metadata["validation"]["valid"] is True
    assert metadata["workflow_yaml"].startswith("info:")


def test_cli_generate_llm_validation_pipeline(cli_generation_validation_llm: Path) -> None:
    zip_path = cli_generation_validation_llm / "app.zip"
    metadata_path = cli_generation_validation_llm / "metadata.json"

    assert zip_path.exists()
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["analysis"]["summary"].startswith("Automated")
    assert metadata["validation"]["valid"] is True
    assert "pipeline" in metadata["workflow_yaml"]

