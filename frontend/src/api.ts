import axios from "axios";
import type { SessionActionResponse, SessionCreateResponse, WorkflowYaml } from "./types";

const baseUrl = import.meta.env.VITE_BACKEND_URL ?? "/api";

const runtimeClient = axios.create({
  baseURL: `${baseUrl}/runtime`
});

export async function fetchWorkflow(): Promise<WorkflowYaml> {
  const { data } = await runtimeClient.get<WorkflowYaml>("/workflow");
  return data;
}

export async function createRuntimeSession(): Promise<SessionCreateResponse> {
  const { data } = await runtimeClient.post<SessionCreateResponse>("/sessions");
  return data;
}

export async function fetchRuntimeSession(sessionId: string): Promise<SessionActionResponse> {
  const { data } = await runtimeClient.get<SessionActionResponse>(`/sessions/${sessionId}`);
  return data;
}

export async function advanceRuntimeSession(sessionId: string): Promise<SessionActionResponse> {
  const { data } = await runtimeClient.post<SessionActionResponse>(`/sessions/${sessionId}/advance`, { step_id: null });
  return data;
}

export async function uploadComponentFile(sessionId: string, componentId: string, file: File): Promise<SessionActionResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await runtimeClient.post<SessionActionResponse>(
    `/sessions/${sessionId}/components/${componentId}/upload`,
    formData,
    {
      headers: { "Content-Type": "multipart/form-data" }
    }
  );
  return data;
}

export async function updateComponentValue(sessionId: string, componentId: string, value: unknown): Promise<SessionActionResponse> {
  const { data } = await runtimeClient.post<SessionActionResponse>(
    `/sessions/${sessionId}/components/${componentId}`,
    { value }
  );
  return data;
}

