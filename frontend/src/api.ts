import axios from "axios";
import type { SessionExecuteRequest, WorkflowSessionResponse, WorkflowYaml } from "./types";

const baseURL =
  import.meta.env.VITE_WORKFLOW_API ??
  import.meta.env.VITE_BACKEND_URL ??
  "/api";

const client = axios.create({
  baseURL
});

export async function fetchWorkflowDefinition() {
  const { data } = await client.get<{ workflow: WorkflowYaml }>("/runtime/workflow");
  return data.workflow;
}

export async function createWorkflowSession() {
  const { data } = await client.post<WorkflowSessionResponse>("/runtime/sessions");
  return data;
}

export async function executeWorkflowSession(sessionId: string, payload: SessionExecuteRequest) {
  const { data } = await client.post<WorkflowSessionResponse>(`/runtime/sessions/${sessionId}/execute`, payload);
  return data;
}

export async function fetchWorkflowSession(sessionId: string) {
  const { data } = await client.get<WorkflowSessionResponse>(`/runtime/sessions/${sessionId}`);
  return data;
}

// Conversation API
export interface ConversationRequest {
  prompt: string;
  user_id?: string;
}

export interface ConversationResponse {
  session_id: string;
  status: string;
  message?: string | null;
}

export interface ConversationMessage {
  role: string;
  content: string;
  timestamp?: string | null;
}

export interface ConversationStatusResponse {
  session_id: string;
  status: string;
  messages: ConversationMessage[];
  workflow_ready: boolean;
}

export interface WorkflowResponse {
  session_id: string;
  workflow_yaml: string;
}

export async function createConversation(payload: ConversationRequest) {
  const { data } = await client.post<ConversationResponse>("/generate/conversations", payload);
  return data;
}

export async function getConversationStatus(sessionId: string) {
  const { data } = await client.get<ConversationStatusResponse>(
    `/generate/conversations/${sessionId}`,
  );
  return data;
}

export async function getConversationWorkflow(sessionId: string) {
  const { data } = await client.get<WorkflowResponse>(`/generate/conversations/${sessionId}/workflow`);
  return data;
}

export async function downloadWorkflowPackage(sessionId: string) {
  const { data } = await client.get(`/generate/conversations/${sessionId}/download`, {
    responseType: "blob",
  });
  return data;
}
