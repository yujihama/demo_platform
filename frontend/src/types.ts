export type StepRuntimeStatus = "pending" | "completed" | "failed";

export interface WorkflowInfo {
  name: string;
  description: string;
  version: string;
}

export interface WorkflowProvider {
  provider: "dify" | "mock";
  endpoint: string;
  api_key_env?: string | null;
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
  props?: Record<string, unknown>;
}

export interface UISection {
  layout: string;
  steps: UIStep[];
}

export interface PipelineStep {
  id: string;
  component: string;
  params: Record<string, unknown>;
}

export interface PipelineSection {
  steps: PipelineStep[];
}

export interface WorkflowYaml {
  info: WorkflowInfo;
  workflows: Record<string, WorkflowProvider>;
  ui?: UISection | null;
  pipeline: PipelineSection;
}

export interface StepState {
  status: StepRuntimeStatus;
  output?: unknown;
  error?: string | null;
}

export interface SessionState {
  session_id: string;
  inputs: Record<string, unknown>;
  data: Record<string, unknown>;
  steps: Record<string, StepState>;
}

export interface WorkflowDefinitionResponse {
  workflow: WorkflowYaml;
}

export interface SessionCreateResponse {
  session: SessionState;
}

export interface SessionStateResponse {
  session: SessionState;
}

export interface ExecuteResponse {
  session: SessionState;
}

export interface ErrorResponse {
  detail?: string;
}
