export type JobStatus =
  | "received"
  | "spec_generating"
  | "templates_rendering"
  | "packaging"
  | "completed"
  | "failed";

export type StepStatus = "pending" | "running" | "completed" | "failed";

export interface GenerationRequest {
  user_id: string;
  project_id: string;
  project_name: string;
  description: string;
  mock_spec_id: string;
  options: {
    include_playwright: boolean;
    include_docker: boolean;
    include_logging: boolean;
  };
  requirements_prompt?: string | null;
  use_mock?: boolean | null;
}

export interface GenerationResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobStep {
  id: string;
  label: string;
  status: StepStatus;
  message?: string;
  logs?: string[];
}

export interface GenerationStatus {
  job_id: string;
  status: JobStatus;
  steps: JobStep[];
  download_url?: string | null;
  metadata?: WorkflowMetadata | null;
}

export interface WorkflowMetadata {
  job_id: string;
  generated_at: string;
  request: GenerationRequest;
  workflow_yaml: string;
  analysis: Record<string, unknown>;
  architecture: Record<string, unknown>;
  validation: Record<string, unknown>;
}

export interface ErrorResponse {
  detail?: string;
  message?: string;
}

