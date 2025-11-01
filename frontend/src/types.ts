export interface WorkflowGenerationRequest {
  prompt: string;
  app_name?: string;
  session_id?: string;
  force_mock?: boolean;
}

export type AgentRole = "analyst" | "architect" | "specialist" | "validator";

export interface AgentMessage {
  role: AgentRole;
  title: string;
  content: string;
  success: boolean;
  metadata?: Record<string, unknown>;
}

export interface WorkflowInfo {
  name: string;
  description: string;
  version: string;
}

export interface WorkflowEndpoint {
  id: string;
  name: string;
  provider: "dify" | "mock";
  endpoint: string;
  method: "GET" | "POST";
}

export interface PipelineStepBase {
  id: string;
  type: string;
  [key: string]: unknown;
}

export interface WorkflowSpecification {
  info: WorkflowInfo;
  workflows: WorkflowEndpoint[];
  pipeline: {
    entrypoint: string;
    steps: Record<string, PipelineStepBase[]>;
  };
  ui?: {
    steps: Array<{
      id: string;
      title: string;
      description?: string | null;
    }>;
  };
}

export interface WorkflowGenerationResponse {
  workflow: WorkflowSpecification;
  workflow_yaml: string;
  messages: AgentMessage[];
  retries: number;
  duration_ms: number;
}

export interface PackageCreateRequest {
  workflow_yaml: string;
  app_name: string;
  include_mock_server: boolean;
  environment_variables: Record<string, string>;
}

export interface PackageDescriptor {
  package_id: string;
  filename: string;
  download_url: string;
  created_at: string;
  expires_at?: string | null;
  size_bytes?: number | null;
}

export interface PackageCreateResponse {
  package: PackageDescriptor;
}

export interface FeaturesConfig {
  default_mock: boolean;
  frontend: {
    base_url: string;
  };
  backend: {
    base_url: string;
  };
}

export interface ErrorResponse {
  message?: string;
  detail?: string;
  issues?: unknown;
}

