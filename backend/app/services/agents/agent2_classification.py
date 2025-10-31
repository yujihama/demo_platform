"""Agent 2: Application Type Classification (skeletal implementation).

This agent classifies the application type from structured requirements.
The current version uses a simple heuristic; LLM integration will follow.
"""

from __future__ import annotations

from .models import AppType, ClassificationResult, RequirementsSchema


class Agent2Classification:
    def run(self, requirements: RequirementsSchema) -> ClassificationResult:
        """Classify app type from requirements (stub)."""
        text = " ".join(r.description.lower() for r in requirements.items)
        if "validate" in text or "検証" in text:
            app_type = AppType.TYPE_VALIDATION
        elif "document" in text or "書類" in text:
            app_type = AppType.TYPE_DOCUMENT_PROCESSOR
        elif "chat" in text or "チャット" in text:
            app_type = AppType.TYPE_CHATBOT
        elif "analytics" in text or "分析" in text:
            app_type = AppType.TYPE_ANALYTICS
        else:
            app_type = AppType.TYPE_CRUD
        return ClassificationResult(app_type=app_type, confidence=0.5, recommended_template=str(app_type.value))


__all__ = ["Agent2Classification"]
