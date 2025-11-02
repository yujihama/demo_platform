import axios from "axios";

import type { WorkflowDefinition, WorkflowSessionState } from "./types";

const client = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL ?? "/api"
});

export async function fetchWorkflowDefinition() {
  const { data } = await client.get<WorkflowDefinition>("/runtime/workflow");
  return data;
}

export async function createRuntimeSession() {
  const { data } = await client.post<WorkflowSessionState>("/runtime/sessions");
  return data;
}

export async function fetchRuntimeSession(sessionId: string) {
  const { data } = await client.get<WorkflowSessionState>(`/runtime/sessions/${sessionId}`);
  return data;
}

export interface SubmitStepOptions {
  data?: Record<string, unknown>;
  file?: File | null;
}

export async function submitRuntimeStep(
  sessionId: string,
  stepId: string,
  options: SubmitStepOptions
) {
  const { data } = await (async () => {
    if (options.file) {
      const formData = new FormData();
      formData.append("file", options.file);
      formData.append("payload", JSON.stringify({ data: options.data ?? {} }));
      return client.post<WorkflowSessionState>(
        `/runtime/sessions/${sessionId}/steps/${stepId}`,
        formData,
        {
          headers: { "Content-Type": "multipart/form-data" }
        }
      );
    }
    return client.post<WorkflowSessionState>(
      `/runtime/sessions/${sessionId}/steps/${stepId}`,
      { data: options.data ?? {} }
    );
  })();
  return data;
}
