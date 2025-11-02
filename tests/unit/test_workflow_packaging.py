from pathlib import Path
import zipfile

from backend.app.models.generation import GenerationJob, JobStatus, JobStep, StepStatus
from backend.app.services.workflow_packaging import WorkflowPackagingService


def test_workflow_packaging_creates_expected_files(tmp_path: Path) -> None:
    service = WorkflowPackagingService(tmp_path)

    job = GenerationJob(
        job_id="job-123",
        user_id="demo-user",
        project_id="workflow-project",
        project_name="Workflow Demo",
        description="Declarative workflow packaging test",
        status=JobStatus.RECEIVED,
        steps=[JobStep(id="analysis", label="分析", status=StepStatus.PENDING)],
    )

    zip_path = service.package_workflow_app(job, "info:\n  name: Demo\n")

    assert zip_path.exists()

    with zipfile.ZipFile(zip_path) as archive:
        entries = set(archive.namelist())
        assert {"workflow.yaml", "docker-compose.yml", ".env.example", "README.md"}.issubset(entries)

        env_example = archive.read(".env.example").decode("utf-8")
        assert "WORKFLOW_PROVIDER=mock" in env_example
        assert "DIFY_API_ENDPOINT" in env_example

        compose = archive.read("docker-compose.yml").decode("utf-8")
        assert "redis:" in compose
        assert "env_file" in compose

        readme = archive.read("README.md").decode("utf-8")
        assert "docker-compose up" in readme
