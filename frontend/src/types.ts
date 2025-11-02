export type ConversationRole = "user" | "assistant" | "system";

export interface ConversationMessage {
  role: ConversationRole;
  content: string;
}

export type ConversationStatus = "processing" | "completed" | "failed";

export interface ConversationCreateRequest {
  prompt: string;
  project_name?: string;
  user_id?: string;
}

export interface ConversationCreateResponse {
  session_id: string;
  status: ConversationStatus;
  messages: ConversationMessage[];
  workflow_ready: boolean;
}

export interface ConversationStatusResponse extends ConversationCreateResponse {
  created_at: string;
  updated_at: string;
  error?: string | null;
}
