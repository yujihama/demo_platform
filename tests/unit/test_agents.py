from __future__ import annotations

from typing import Any, List

from backend.app.agents import AnalystAgent, ArchitectAgent, WorkflowSpecialistAgent, WorkflowValidatorAgent
from backend.app.agents.models import AnalystResult, ArchitecturePlan, WorkflowDraft, ValidatorFeedback
from backend.app.services.llm_factory import RetryPolicy


class FakeLLM:
    """Simple fake LLM that returns predetermined structured outputs."""

    def __init__(self, responses: List[dict[str, Any]]) -> None:
        self._responses = responses

    def with_structured_output(self, output_model: Any) -> Any:  # noqa: ANN401
        outer = self

        class _FakeRunnable:
            def invoke(self, _: Any) -> Any:  # noqa: ANN401
                if not outer._responses:
                    raise AssertionError("No more mock responses available")
                payload = outer._responses.pop(0)
                return output_model(**payload)

        return _FakeRunnable()


def test_analyst_agent_returns_result() -> None:
    fake_llm = FakeLLM(
        [
            {
                "primary_goal": "?????????",
                "domain_context": "????????????",
                "requirements": [
                    {
                        "id": "REQ-1",
                        "title": "??????????????",
                        "detail": "PDF??????????????????",
                        "category": "input",
                        "acceptance_criteria": ["PDF????"]
                    }
                ],
                "risks": ["LLM?????"],
                "sample_inputs": ["invoice-001.pdf"],
            }
        ]
    )

    agent = AnalystAgent(fake_llm, RetryPolicy())
    result = agent.run("????????????")

    assert isinstance(result, AnalystResult)
    assert result.primary_goal == "?????????"
    assert result.requirements[0].id == "REQ-1"


def test_architect_agent_creates_plan() -> None:
    fake_llm = FakeLLM(
        [
            {
                "title": "???????",
                "summary": "????????????2????",
                "ui_steps": [
                    {
                        "id": "upload_step",
                        "title": "??????",
                        "description": "PDF???",
                        "components": ["invoice_upload"],
                        "success_transition": "result_step",
                    }
                ],
                "pipeline": [
                    {
                        "id": "call_validation",
                        "type": "call_workflow",
                        "description": "Dify???",
                        "uses_provider": "dify_invoice",
                        "inputs": ["file_url"],
                        "outputs": ["result"],
                    }
                ],
                "workflows": [
                    {
                        "id": "dify_invoice",
                        "provider_type": "dify",
                        "endpoint": "https://api.example/workflows",
                        "description": "????????",
                    }
                ],
            }
        ]
    )
    analysis = AnalystResult(
        primary_goal="?????",
        domain_context="",
        requirements=[],
        risks=[],
        sample_inputs=[],
    )

    agent = ArchitectAgent(fake_llm, RetryPolicy())
    plan = agent.run(analysis)

    assert isinstance(plan, ArchitecturePlan)
    assert plan.ui_steps[0].id == "upload_step"
    assert plan.pipeline[0].uses_provider == "dify_invoice"


def test_workflow_specialist_agent_emits_yaml() -> None:
    fake_llm = FakeLLM(
        [
            {
                "workflow_yaml": "version: '1'\ninfo:\n  name: demo\n",
                "notes": ["YAML?????????"],
            }
        ]
    )
    analysis = AnalystResult(
        primary_goal="?????",
        domain_context="",
        requirements=[],
        risks=[],
        sample_inputs=[],
    )
    plan = ArchitecturePlan(
        title="demo",
        summary="",
        ui_steps=[],
        pipeline=[],
        workflows=[],
    )

    agent = WorkflowSpecialistAgent(fake_llm, RetryPolicy())
    draft = agent.run(analysis, plan, feedback=None)

    assert isinstance(draft, WorkflowDraft)
    assert "version" in draft.workflow_yaml
    assert draft.notes == ["YAML?????????"]


def test_workflow_validator_agent_returns_feedback() -> None:
    fake_llm = FakeLLM(
        [
            {
                "is_valid": False,
                "errors": ["provider id ???"],
                "suggestions": ["workflows ?????? provider ???"]
            }
        ]
    )

    agent = WorkflowValidatorAgent(fake_llm, RetryPolicy())
    feedback = agent.run(errors="missing provider", metadata="goal: demo")

    assert isinstance(feedback, ValidatorFeedback)
    assert feedback.is_valid is False
    assert feedback.suggestions[0].startswith("workflows")
