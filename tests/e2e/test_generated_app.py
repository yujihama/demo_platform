from __future__ import annotations

import zipfile
from pathlib import Path

import yaml

from backend.app.workflow import WorkflowLoader


def test_packaged_zip_contains_workflow(cli_generation: Path) -> None:
    zip_path = cli_generation / "app.zip"
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path, "r") as zf:
        namelist = zf.namelist()
        assert "workflow.yaml" in namelist
        assert ".env.example" in namelist
        assert "docker-compose.yml" in namelist

        workflow_yaml = zf.read("workflow.yaml").decode("utf-8")
        document = WorkflowLoader.from_yaml_text(workflow_yaml)

        assert document.info.name
        assert document.pipeline
        assert document.ui.steps

        compose_text = zf.read("docker-compose.yml").decode("utf-8")
        compose = yaml.safe_load(compose_text)
        assert "engine" in compose.get("services", {})
        assert "frontend" in compose.get("services", {})

