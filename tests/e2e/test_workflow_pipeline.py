from pathlib import Path
import json
import zipfile

from backend.app.models import GenerationOptions, GenerationRequest, JobStatus
from backend.app.services.workflow_pipeline import workflow_pipeline


def build_request(prompt: str = "請求書の検証を行うワークフローを構築してください。") -> GenerationRequest:
    return GenerationRequest(
        user_id="e2e-user",
        project_id="phase3-app",
        project_name="Phase 3 Workflow",
        description="Phase 3 end-to-end test",
        mock_spec_id="invoice-verification",
        options=GenerationOptions(
            include_docker=True,
            include_logging=True,
            include_playwright=True,
        ),
        requirements_prompt=prompt,
        use_mock=False,
    )


def test_workflow_pipeline_produces_artifacts(clean_output_root) -> None:  # type: ignore[override]
    request = build_request()
    job = workflow_pipeline.run_sync(request)

    assert job.status == JobStatus.COMPLETED
    assert job.download_url
    assert job.output_path

    zip_path = Path(job.output_path)
    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as archive:
        files = set(archive.namelist())
        assert "workflow.yaml" in files
        assert "docker-compose.yml" in files
        assert ".env" in files
        assert ".env.example" in files
        assert "README.md" in files

        env_content = archive.read(".env").decode("utf-8")
        assert "WORKFLOW_PROVIDER=mock" in env_content

    metadata_path = zip_path.with_name("metadata.json")
    assert metadata_path.exists()

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["job_id"] == job.job_id
    assert metadata["request"]["project_name"] == "Phase 3 Workflow"
    assert metadata["workflow_yaml"].startswith("info:")
    assert metadata["analysis"]
    assert metadata["architecture"]
    assert metadata["validation"]


def test_workflow_pipeline_retry_cycle(clean_output_root) -> None:  # type: ignore[override]
    request = build_request("force retry Build an invoice validation assistant")
    job = workflow_pipeline.run_sync(request)

    assert job.status == JobStatus.COMPLETED
    metadata = job.metadata or {}
    validation = metadata.get("validation")
    assert validation
    assert validation.get("valid") is True
