export type JobStatus =
  | "received"
  | "spec_generating"
  | "templates_rendering"
  | "packaging"
  | "completed"
  | "failed";

export type MessageRole = "user" | "assistant" | "system";

export interface ConversationMessage {
  role: MessageRole;
  content: string;
  timestamp: string;
}

export interface ConversationStartRequest {
  user_id: string;
  project_id: string;
  project_name: string;
  prompt: string;
  description?: string;
}

export interface ConversationSession {
  session_id: string;
  job_id: string;
  status: JobStatus;
  messages: ConversationMessage[];
  workflow_ready: boolean;
  download_url?: string | null;
}

export interface WorkflowPreview {
  workflow: string;
}
