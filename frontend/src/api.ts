import axios from "axios";
import type { FeaturesConfig, GenerationRequest, GenerationResponse, GenerationStatus } from "./types";

const client = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL ?? "/api"
});

export async function createGenerationJob(payload: GenerationRequest) {
  const { data } = await client.post<GenerationResponse>('/generate', payload);
  return data;
}

export async function fetchJob(jobId: string) {
  const { data } = await client.get<GenerationStatus>(`/generate/${jobId}`);
  return data;
}

export async function fetchPreview(specId: string) {
  const { data } = await client.get(`/preview/${specId}`, {
    responseType: 'text'
  });
  return data as string;
}

export async function fetchFeaturesConfig() {
  const { data } = await client.get<FeaturesConfig>('/config/features');
  return data;
}

