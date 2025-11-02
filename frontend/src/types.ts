export interface WorkflowInfo {
  name: string;
  description: string;
  version?: string;
  author?: string | null;
}

export interface WorkflowProvider {
  provider: "dify" | "mock" | string;
  endpoint: string;
  api_key_env?: string | null;
}

export interface UIComponent {
  type: string;
  id: string;
  props?: Record<string, unknown>;
}

export interface UIStep {
  id: string;
  title: string;
  description?: string;
  components: UIComponent[];
}

export interface UISection {
  layout: string;
  steps: UIStep[];
}

export interface PipelineStepDefinition {
  id: string;
  component: string;
  params?: Record<string, unknown>;
}

export interface WorkflowYaml {
  info: WorkflowInfo;
  workflows: Record<string, WorkflowProvider>;
  ui?: UISection | null;
  pipeline: {
    steps: PipelineStepDefinition[];
  };
}

export interface ComponentState {
  value: unknown;
  status: string;
  updated_at: string;
}

export interface RuntimeSession {
  session_id: string;
  status: "idle" | "running" | "waiting" | "completed" | "failed";
  active_step_id?: string | null;
  waiting_for: string[];
  context: Record<string, unknown>;
  component_state: Record<string, ComponentState>;
  next_step_index: number;
  last_error?: string | null;
}

export interface SessionCreateResponse {
  session: RuntimeSession;
  workflow: WorkflowYaml;
}

export interface SessionActionResponse {
  session: RuntimeSession;
}

