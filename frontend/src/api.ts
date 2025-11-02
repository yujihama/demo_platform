import axios from "axios";
import type {
  ExecuteResponse,
  SessionCreateResponse,
  SessionStateResponse,
  WorkflowDefinitionResponse
} from "./types";

const baseURL = import.meta.env.VITE_BACKEND_URL ?? "/api";

const client = axios.create({
  baseURL
});

export async function fetchWorkflowDefinition() {
  const { data } = await client.get<WorkflowDefinitionResponse>("/workflow/definition");
  return data.workflow;
}

export async function createWorkflowSession() {
  const { data } = await client.post<SessionCreateResponse>("/workflow/sessions");
  return data.session;
}

export async function fetchWorkflowSession(sessionId: string) {
  const { data } = await client.get<SessionStateResponse>(`/workflow/sessions/${sessionId}`);
  return data.session;
}

export async function uploadWorkflowInput(sessionId: string, stepId: string, file: File) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await client.post<SessionStateResponse>(
    `/workflow/sessions/${sessionId}/inputs/${stepId}`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" }
    }
  );
  return data.session;
}

export async function executeWorkflow(sessionId: string) {
  const { data } = await client.post<ExecuteResponse>(`/workflow/sessions/${sessionId}/execute`);
  return data.session;
}
