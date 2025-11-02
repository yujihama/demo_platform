import axios from "axios";
import type { ConversationSession, ConversationStartRequest } from "./types";

const baseURL =
  import.meta.env.VITE_BACKEND_URL ??
  import.meta.env.VITE_WORKFLOW_API ??
  "/api";

const client = axios.create({
  baseURL
});

export async function startConversation(payload: ConversationStartRequest) {
  const { data } = await client.post<ConversationSession>("/generate/conversations", payload);
  return data;
}

export async function fetchConversation(sessionId: string) {
  const { data } = await client.get<ConversationSession>(`/generate/conversations/${sessionId}`);
  return data;
}

export async function fetchWorkflowYaml(sessionId: string) {
  const { data } = await client.get<string>(
    `/generate/conversations/${sessionId}/workflow`,
    { responseType: "text" }
  );
  return data;
}

export async function downloadPackage(sessionId: string) {
  const { data } = await client.get<Blob>(
    `/generate/conversations/${sessionId}/package`,
    { responseType: "blob" }
  );
  return data;
}
