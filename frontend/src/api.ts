import axios from "axios";
import type {
  ConversationCreateRequest,
  ConversationCreateResponse,
  ConversationStatusResponse
} from "./types";

const baseURL =
  import.meta.env.VITE_CONVERSATION_API ??
  import.meta.env.VITE_BACKEND_URL ??
  import.meta.env.VITE_WORKFLOW_API ??
  "/api";

const client = axios.create({
  baseURL
});

export async function createConversation(payload: ConversationCreateRequest) {
  const { data } = await client.post<ConversationCreateResponse>("/generate/conversations", payload);
  return data;
}

export async function fetchConversation(sessionId: string) {
  const { data } = await client.get<ConversationStatusResponse>(`/generate/conversations/${sessionId}`);
  return data;
}

export async function fetchWorkflowYaml(sessionId: string) {
  const { data } = await client.get<string>(`/generate/conversations/${sessionId}/workflow`, {
    responseType: "text"
  });
  return data;
}

export async function downloadPackage(sessionId: string) {
  const response = await client.post(`/generate/conversations/${sessionId}/package`, undefined, {
    responseType: "blob"
  });
  return response.data as Blob;
}
