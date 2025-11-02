export interface RequirementMetadata {
  id: string;
  category: string;
  title: string;
  description: string;
  acceptanceCriteria: string[];
}

export interface WorkflowAnalysisMetadata {
  summary?: string;
  primaryGoal?: string;
  requirements: RequirementMetadata[];
}

export interface WorkflowArchitectureMetadata {
  infoSection: Record<string, unknown>;
  workflowsSection: Record<string, Record<string, unknown>>;
  uiStructure?: Record<string, unknown>;
  pipelineStructure?: Record<string, unknown>[];
  rationale?: string;
}

export interface WorkflowValidationMetadata {
  valid?: boolean;
  schemaValid?: boolean;
  llmValid?: boolean;
  schemaErrors: string[];
  llmErrors: string[];
  suggestions: string[];
  allErrors: string[];
}

export interface WorkflowMetadata {
  workflowYaml?: string;
  analysis?: WorkflowAnalysisMetadata;
  architecture?: WorkflowArchitectureMetadata;
  validation?: WorkflowValidationMetadata;
}

type UnknownRecord = Record<string, unknown>;

const isRecord = (value: unknown): value is UnknownRecord =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const asString = (value: unknown): string | undefined =>
  (typeof value === "string" ? value : undefined);

const asBoolean = (value: unknown): boolean | undefined =>
  (typeof value === "boolean" ? value : undefined);

const asStringArray = (value: unknown): string[] | undefined => {
  if (!Array.isArray(value)) return undefined;
  const items = value.filter((item): item is string => typeof item === "string");
  return items.length ? items : [];
};

const parseRequirements = (value: unknown): RequirementMetadata[] => {
  if (!Array.isArray(value)) return [];
  const requirements: RequirementMetadata[] = [];
  for (const item of value) {
    if (!isRecord(item)) continue;
    const id = asString(item.id);
    const category = asString(item.category);
    const title = asString(item.title);
    const description = asString(item.description);
    if (!id || !category || !title || !description) continue;
    const acceptanceCriteria = asStringArray(item.acceptance_criteria) ?? [];
    requirements.push({ id, category, title, description, acceptanceCriteria });
  }
  return requirements;
};

const parseAnalysis = (value: unknown): WorkflowAnalysisMetadata | undefined => {
  if (!isRecord(value)) return undefined;
  const summary = asString(value.summary);
  const primaryGoal = asString(value.primary_goal);
  const requirements = parseRequirements(value.requirements);
  if (!summary && !primaryGoal && requirements.length === 0) {
    return undefined;
  }
  return {
    summary,
    primaryGoal,
    requirements,
  };
};

const parseWorkflowsSection = (value: unknown): Record<string, Record<string, unknown>> | undefined => {
  if (!isRecord(value)) return undefined;
  const result: Record<string, Record<string, unknown>> = {};
  for (const [key, entry] of Object.entries(value)) {
    if (isRecord(entry)) {
      result[key] = entry;
    }
  }
  return Object.keys(result).length ? result : undefined;
};

const parseArchitecture = (value: unknown): WorkflowArchitectureMetadata | undefined => {
  if (!isRecord(value)) return undefined;
  const infoSection = isRecord(value.info_section) ? value.info_section : undefined;
  const workflowsSection = parseWorkflowsSection(value.workflows_section);
  const uiStructure = isRecord(value.ui_structure) ? value.ui_structure : undefined;
  const pipelineStructure = Array.isArray(value.pipeline_structure)
    ? value.pipeline_structure.filter(isRecord)
    : undefined;
  const rationale = asString(value.rationale);

  if (!infoSection && !workflowsSection && !uiStructure && !pipelineStructure && !rationale) {
    return undefined;
  }

  return {
    infoSection: infoSection ?? {},
    workflowsSection: workflowsSection ?? {},
    uiStructure,
    pipelineStructure,
    rationale,
  };
};

const parseValidation = (value: unknown): WorkflowValidationMetadata | undefined => {
  if (!isRecord(value)) return undefined;
  const valid = asBoolean(value.valid);
  const schemaValid = asBoolean(value.schema_valid);
  const llmValid = asBoolean(value.llm_valid);
  const schemaErrors = asStringArray(value.schema_errors) ?? [];
  const llmErrors = asStringArray(value.llm_errors) ?? [];
  const suggestions = asStringArray(value.suggestions) ?? [];
  const allErrors = asStringArray(value.all_errors) ?? [...schemaErrors, ...llmErrors];

  if (
    valid === undefined &&
    schemaValid === undefined &&
    llmValid === undefined &&
    schemaErrors.length === 0 &&
    llmErrors.length === 0 &&
    suggestions.length === 0
  ) {
    return undefined;
  }

  return {
    valid,
    schemaValid,
    llmValid,
    schemaErrors,
    llmErrors,
    suggestions,
    allErrors,
  };
};

export const parseWorkflowMetadata = (metadata: unknown): WorkflowMetadata | null => {
  if (!isRecord(metadata)) return null;

  const workflowYaml = asString(metadata.workflow_yaml);
  const analysis = parseAnalysis(metadata.analysis);
  const architecture = parseArchitecture(metadata.architecture);
  const validation = parseValidation(metadata.validation);

  if (!workflowYaml && !analysis && !architecture && !validation) {
    return null;
  }

  return {
    workflowYaml,
    analysis,
    architecture,
    validation,
  };
};
