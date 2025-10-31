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

