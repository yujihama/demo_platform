import axios from "axios";
import type {
  FeaturesConfig,
  PackageCreateRequest,
  PackageCreateResponse,
  WorkflowGenerationRequest,
  WorkflowGenerationResponse
} from "./types";

const client = axios.create({
  baseURL: import.meta.env.VITE_BACKEND_URL ?? "/api"
});

export async function generateWorkflow(payload: WorkflowGenerationRequest) {
  const { data } = await client.post<WorkflowGenerationResponse>("/workflows/generate", payload);
  return data;
}

export async function createPackage(payload: PackageCreateRequest) {
  const { data } = await client.post<PackageCreateResponse>("/packages", payload);
  return data;
}

export async function fetchFeaturesConfig() {
  const { data } = await client.get<FeaturesConfig>("/config/features");
  return data;
}

