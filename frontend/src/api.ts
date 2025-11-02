import axios from "axios";
import type {
  ConversationCreateRequest,
  ConversationSession,
  SessionExecuteRequest,
  WorkflowSessionResponse,
  WorkflowYaml
} from "./types";

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

export async function startConversation(payload: ConversationCreateRequest) {
  const { data } = await client.post<ConversationSession>("/generate/conversations", payload);
  return data;
}

export async function fetchConversation(sessionId: string) {
  const { data } = await client.get<ConversationSession>(`/generate/conversations/${sessionId}`);
  return data;
}

export async function fetchConversationWorkflow(sessionId: string) {
  const response = await client.get(`/generate/conversations/${sessionId}/workflow`, {
    responseType: "text"
  });
  return response.data as string;
}

export async function downloadConversationPackage(sessionId: string) {
  const response = await client.post(`/generate/conversations/${sessionId}/package`, undefined, {
    responseType: "blob"
  });
  return response.data as Blob;
}
