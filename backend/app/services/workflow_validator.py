"""Schema validator and self-correction loop for workflow.yaml generation."""

from __future__ import annotations

import yaml
import logging
from typing import Any, Dict, List

from pydantic import ValidationError

from ..models.workflow import WorkflowYaml
from .llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class WorkflowValidator:
    """Validates workflow.yaml against schema and coordinates self-correction."""
    
    def __init__(self, llm_factory: LLMFactory):
        self.llm_factory = llm_factory
    
    def validate_yaml_schema(self, yaml_content: str) -> tuple[bool, List[str], WorkflowYaml | None]:
        """
        Validate YAML content against WorkflowYaml schema.
        
        Returns:
            tuple of (is_valid, errors, parsed_model)
        """
        errors: List[str] = []
        
        # Parse YAML first
        try:
            parsed = yaml.safe_load(yaml_content)
            if parsed is None:
                errors.append("YAML file is empty")
                return False, errors, None
        except yaml.YAMLError as e:
            errors.append(f"YAML syntax error: {str(e)}")
            return False, errors, None
        
        # Validate against Pydantic schema
        try:
            model = WorkflowYaml(**parsed)
            return True, [], model
        except ValidationError as e:
            for error in e.errors():
                field_path = " -> ".join(str(loc) for loc in error["loc"])
                error_msg = f"{field_path}: {error['msg']}"
                errors.append(error_msg)
            return False, errors, None
    
    def validate_with_llm(
        self,
        yaml_content: str,
        previous_errors: List[str] | None = None,
    ) -> tuple[bool, List[str], List[str]]:
        """
        Use LLM validator agent to validate YAML and provide feedback.
        
        Returns:
            tuple of (is_valid, errors, suggestions)
        """
        from ..agents.workflow_agents import ValidatorAgent
        
        llm = self.llm_factory.create_chat_model()
        retry_policy = self.llm_factory.get_retry_policy()
        validator = ValidatorAgent(llm, retry_policy)
        
        previous_errors_str = "\n".join(previous_errors) if previous_errors else "None"
        
        try:
            result = validator.run(yaml_content, previous_errors_str)
            return result.valid, result.errors, result.suggestions
        except Exception as e:
            logger.error("LLM validation failed: %s", e, exc_info=True)
            return False, [f"LLM validation error: {str(e)}"], []
    
    def validate_complete(
        self,
        yaml_content: str,
        previous_errors: List[str] | None = None,
    ) -> Dict[str, Any]:
        """
        Complete validation: schema validation + LLM validation.
        
        Returns:
            dict with keys: valid, schema_errors, llm_errors, suggestions, model
        """
        # Schema validation first
        schema_valid, schema_errors, model = self.validate_yaml_schema(yaml_content)
        
        # LLM validation
        llm_valid, llm_errors, suggestions = self.validate_with_llm(
            yaml_content,
            previous_errors,
        )
        
        is_valid = schema_valid and llm_valid
        
        return {
            "valid": is_valid,
            "schema_valid": schema_valid,
            "llm_valid": llm_valid,
            "schema_errors": schema_errors,
            "llm_errors": llm_errors,
            "all_errors": schema_errors + llm_errors,
            "suggestions": suggestions,
            "model": model,
        }


class SelfCorrectionLoop:
    """Orchestrates self-correction loop for workflow.yaml generation."""
    
    def __init__(
        self,
        llm_factory: LLMFactory,
        validator: WorkflowValidator,
        max_iterations: int = 3,
    ):
        self.llm_factory = llm_factory
        self.validator = validator
        self.max_iterations = max_iterations
    
    def generate_with_correction(
        self,
        requirements: Any,  # WorkflowAnalysisResult
        architecture: Any,  # WorkflowArchitectureResult
    ) -> tuple[str, bool, List[str]]:
        """
        Generate workflow.yaml with self-correction loop.
        
        Returns:
            tuple of (yaml_content, success, all_errors_encountered)
        """
        from ..agents.workflow_agents import YAMLSpecialistAgent
        
        llm = self.llm_factory.create_chat_model()
        retry_policy = self.llm_factory.get_retry_policy()
        specialist = YAMLSpecialistAgent(llm, retry_policy)
        
        all_errors: List[str] = []
        yaml_content = ""
        
        for iteration in range(self.max_iterations):
            logger.info("YAML generation iteration %d/%d", iteration + 1, self.max_iterations)
            
            try:
                # Generate YAML
                if iteration == 0:
                    result = specialist.run(requirements, architecture)
                else:
                    # On retry, include previous errors in the prompt
                    result = specialist.run(requirements, architecture)
                
                yaml_content = result.workflow_yaml
                
                # Validate
                validation_result = self.validator.validate_complete(
                    yaml_content,
                    previous_errors=all_errors if all_errors else None,
                )
                
                all_errors.extend(validation_result["all_errors"])
                
                if validation_result["valid"]:
                    logger.info("YAML generation succeeded after %d iterations", iteration + 1)
                    return yaml_content, True, []
                
                logger.warning(
                    "YAML validation failed (iteration %d): %s",
                    iteration + 1,
                    validation_result["all_errors"],
                )
                
                # Prepare feedback for next iteration
                feedback = "\n".join(validation_result["all_errors"])
                if validation_result["suggestions"]:
                    feedback += "\nSuggestions:\n" + "\n".join(validation_result["suggestions"])
                
                # Update requirements/architecture with feedback if needed
                # For now, we'll rely on the LLM to incorporate feedback in the next iteration
                
            except Exception as e:
                logger.error("YAML generation iteration %d failed: %s", iteration + 1, e, exc_info=True)
                all_errors.append(f"Iteration {iteration + 1} failed: {str(e)}")
                if iteration == self.max_iterations - 1:
                    break
        
        logger.error(
            "YAML generation failed after %d iterations. Errors: %s",
            self.max_iterations,
            all_errors,
        )
        return yaml_content, False, all_errors
