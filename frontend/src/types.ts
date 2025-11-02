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
  metadata?: Record<string, unknown> | null;
}

export interface ErrorResponse {
  detail?: string;
  message?: string;
}

export interface FeaturesConfig {
  agents: {
    use_mock: boolean;
    allow_llm_toggle: boolean;
  };
  frontend?: {
    polling_interval_seconds?: number;
  };
}

export interface WorkflowRequirement {
  id: string;
  category: string;
  title: string;
  description: string;
  acceptance_criteria: string[];
}

export interface WorkflowAnalysisMetadata {
  summary: string;
  primary_goal: string;
  requirements: WorkflowRequirement[];
}

export interface WorkflowArchitectureMetadata {
  info_section: Record<string, unknown>;
  workflows_section: Record<string, Record<string, unknown>>;
  ui_structure: Record<string, unknown>;
  pipeline_structure: Record<string, unknown>[];
  rationale: string;
}

export interface WorkflowValidationMetadata {
  valid: boolean;
  schema_valid?: boolean;
  llm_valid?: boolean;
  schema_errors?: string[];
  llm_errors?: string[];
  all_errors?: string[];
  suggestions?: string[];
  model?: Record<string, unknown> | null;
}

export interface WorkflowGenerationMetadata {
  workflow_yaml?: string;
  analysis?: WorkflowAnalysisMetadata;
  architecture?: WorkflowArchitectureMetadata;
  validation?: WorkflowValidationMetadata;
}

