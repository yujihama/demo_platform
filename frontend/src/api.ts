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
