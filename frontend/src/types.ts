export type StepStatus = "pending" | "running" | "completed" | "error";
export type SessionStatus = "awaiting_input" | "processing" | "completed" | "error";

export interface WorkflowInfo {
  name: string;
  description: string;
  version: string;
  author?: string | null;
}

export interface UIComponent {
  type: string;
  id: string;
  props: Record<string, unknown>;
}

export interface UIStep {
  id: string;
  title: string;
  description?: string | null;
  components: UIComponent[];
}

export interface UISection {
  layout: string;
  steps: UIStep[];
}

export interface PipelineStepDefinition {
  id: string;
  component: string;
  params: Record<string, any>;
}

export interface PipelineSection {
  steps: PipelineStepDefinition[];
}

export interface WorkflowDefinition {
  info: WorkflowInfo;
  ui?: UISection;
  pipeline: PipelineSection;
}

export interface WorkflowSessionState {
  session_id: string;
  workflow_id: string;
  status: SessionStatus;
  active_ui_step?: string | null;
  completed_ui_steps: string[];
  step_status: Record<string, StepStatus>;
  context: Record<string, any>;
  last_error?: string | null;
  updated_at: string;
}
