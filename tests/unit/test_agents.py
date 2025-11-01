from backend.app.agents.workflow import AnalystAgent, ArchitectAgent, SpecialistAgent, ValidatorAgent
from backend.app.models import WorkflowGenerationRequest
from backend.app.models.workflow import WorkflowSpecification
from backend.app.services.workflow_generation import WorkflowGenerationService


def test_analyst_agent_infers_invoice_context() -> None:
    agent = AnalystAgent()
    insight = agent.run("?????????")

    assert insight.app_name == "Invoice Validation Assistant"
    assert "???" in insight.summary or "invoice" in insight.summary.lower()
    assert "invoice" in " ".join(insight.data_entities)


def test_architect_agent_creates_invoice_blueprint() -> None:
    analyst = AnalystAgent()
    architect = ArchitectAgent()

    insight = analyst.run("Upload invoice and validate")
    blueprint = architect.run(insight)

    assert blueprint.workflows[0].identifier == "invoice_validation"
    assert any(step.identifier == "invoke-invoice-validation" for step in blueprint.pipeline)
    assert any(step.identifier == "upload" for step in blueprint.ui)


def test_specialist_agent_creates_valid_workflow_specification() -> None:
    analyst = AnalystAgent()
    architect = ArchitectAgent()
    specialist = SpecialistAgent()

    insight = analyst.run("?????????????")
    blueprint = architect.run(insight)
    spec = specialist.run(insight, blueprint)

    assert isinstance(spec, WorkflowSpecification)
    assert spec.pipeline.entrypoint == "main"
    assert spec.workflows[0].provider.value == "mock"


def test_workflow_generation_service_returns_yaml() -> None:
    service = WorkflowGenerationService()
    request = WorkflowGenerationRequest(
        prompt="????PDF????????????????????????",
        app_name="Invoice QA",
    )
    response = service.generate(request)

    assert response.workflow.info.name == "Invoice QA"
    assert "workflow.yaml" not in response.workflow_yaml  # raw yaml string
    assert "invoice_validation" in response.workflow_yaml
    assert any(message.role.value == "validator" for message in response.messages)
