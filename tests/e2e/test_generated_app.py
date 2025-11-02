import json
import zipfile
from pathlib import Path

import pytest


@pytest.mark.e2e
def test_workflow_package_contains_environment(cli_generation_llm: Path) -> None:
    zip_path = cli_generation_llm / "app.zip"
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as archive:
        names = set(archive.namelist())
        assert "workflow.yaml" in names
        assert "docker-compose.yml" in names
        assert ".env" in names
        assert ".env.example" in names
        assert "README.md" in names

        env_content = archive.read(".env").decode("utf-8")
        env_example = archive.read(".env.example").decode("utf-8")

    assert env_content == env_example
    assert "WORKFLOW_PROVIDER" in env_content
    assert "DIFY_API_ENDPOINT" in env_content


@pytest.mark.e2e
def test_workflow_metadata_structure(cli_generation_llm: Path) -> None:
    metadata_path = cli_generation_llm / "metadata.json"
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))

    assert metadata["analysis"]["summary"].startswith("Automated")
    assert metadata["architecture"]["pipeline_structure"]
    assert metadata["validation"]["valid"] is True
    assert metadata["workflow_yaml"].startswith("info:")
