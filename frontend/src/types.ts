export interface WorkflowInfo {
  name: string;
  description: string;
  version: string;
  author?: string | null;
}

export interface WorkflowProvider {
  provider: "mock" | "dify";
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
  description?: string | null;
  components: UIComponent[];
}

export interface UISection {
  layout: string;
  steps: UIStep[];
}

export interface PipelineStep {
  id: string;
  component: string;
  params?: Record<string, unknown>;
  condition?: string | null;
  on_error?: string | null;
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

export type WorkflowSessionStatus = "idle" | "running" | "completed" | "failed";

export interface WorkflowSessionResponse {
  session_id: string;
  status: WorkflowSessionStatus;
  current_step?: string | null;
  view: Record<string, unknown>;
  context: Record<string, unknown>;
  error?: string | null;
}

export interface SessionExecuteRequest {
  step_id?: string | null;
  inputs: Record<string, unknown>;
}

export type GenerationJobStatus =
  | "received"
  | "spec_generating"
  | "templates_rendering"
  | "packaging"
  | "completed"
  | "failed";

export interface ConversationMessage {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
}

export interface ConversationCreateRequest {
  user_id: string;
  project_id: string;
  project_name: string;
  prompt: string;
  description?: string;
}

export interface ConversationCreateResponse {
  session_id: string;
  status: GenerationJobStatus;
  messages: ConversationMessage[];
}

export interface ConversationStatusResponse {
  session_id: string;
  status: GenerationJobStatus;
  messages: ConversationMessage[];
  steps: JobStep[];
  download_url?: string | null;
}

export interface JobStep {
  id: string;
  label: string;
  status: "pending" | "running" | "completed" | "failed";
  message?: string | null;
}

export interface PackageMetadata {
  session_id: string;
  filename: string;
  size_bytes: number;
  updated_at: string;
}
