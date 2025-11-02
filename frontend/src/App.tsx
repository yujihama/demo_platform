import { useEffect, useMemo, useState } from "react";
import { Box, Container, Grid, Stack, Typography } from "@mui/material";

import { PromptComposer, PromptComposerErrors, PromptComposerValues } from "./components/PromptComposer";
import { ConversationPanel, type ConversationMessage } from "./components/ConversationPanel";
import { JobProgressCard } from "./components/JobProgressCard";
import { YamlPreviewCard } from "./components/YamlPreviewCard";
import { WorkflowInsights } from "./components/WorkflowInsights";
import { DownloadArtifactCard } from "./components/DownloadArtifactCard";
import { ErrorBanner } from "./components/ErrorBanner";
import { createWorkflowJob, fetchFeaturesConfig, fetchWorkflowJob } from "./api";
import type {
  FeaturesConfig,
  GenerationRequest,
  JobStep,
  StepStatus,
  WorkflowAnalysisMetadata,
  WorkflowArchitectureMetadata,
  WorkflowMetadata,
  WorkflowValidationMetadata
} from "./types";
import { useJobPolling } from "./hooks/useJobPolling";
import { logger } from "./utils/logger";

const DEFAULT_FORM_VALUES: PromptComposerValues = {
  prompt: "",
  userId: "workflow-user",
  projectId: "workflow-app",
  projectName: "Workflow Assistant",
  description: "宣言的な workflow.yaml を生成するデモプロジェクト"
};

const WORKFLOW_STEP_ORDER: Array<{ id: string; label: string }> = [
  { id: "analysis", label: "要件分析" },
  { id: "architecture", label: "アーキテクチャ設計" },
  { id: "yaml_generation", label: "workflow.yaml 生成" },
  { id: "validation", label: "仕様バリデーション" },
  { id: "packaging", label: "パッケージング" }
];

export default function App() {
  const [features, setFeatures] = useState<FeaturesConfig | null>(null);
  const [formValues, setFormValues] = useState<PromptComposerValues>(DEFAULT_FORM_VALUES);
  const [formErrors, setFormErrors] = useState<PromptComposerErrors>({});
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [activePrompt, setActivePrompt] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    fetchFeaturesConfig()
      .then((config) => {
        if (!mounted) return;
        setFeatures(config);
      })
      .catch((error) => logger.warn("Failed to load feature config", error));
    return () => {
      mounted = false;
    };
  }, []);

  const pollingInterval = useMemo(() => {
    const seconds = features?.frontend?.polling_interval_seconds ?? 2;
    return Math.max(1, seconds) * 1000;
  }, [features]);

  const { status, loading: pollingLoading, error: pollingError, refresh, stop } = useJobPolling(
    jobId,
    pollingInterval,
    fetchWorkflowJob
  );

  const workflowMetadata: WorkflowMetadata | null | undefined = status?.metadata ?? null;
  const analysis = workflowMetadata?.analysis as WorkflowAnalysisMetadata | undefined;
  const architecture = workflowMetadata?.architecture as WorkflowArchitectureMetadata | undefined;
  const validation = workflowMetadata?.validation as WorkflowValidationMetadata | undefined;
  const workflowYaml = typeof workflowMetadata?.workflow_yaml === "string" ? workflowMetadata.workflow_yaml : undefined;

  const conversationMessages = useMemo<ConversationMessage[]>(() => {
    const messages: ConversationMessage[] = [];
    if (activePrompt) {
      messages.push({
        id: "prompt",
        role: "user",
        title: "あなた",
        content: (
          <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
            {activePrompt}
          </Typography>
        )
      });
    }
    if (analysis) {
      messages.push({
        id: "analysis",
        role: "agent",
        title: "要件アナリスト",
        content: (
          <Stack spacing={1}>
            <Typography variant="body1">{analysis.summary}</Typography>
            <Typography variant="body2" color="text.secondary">
              主要な目的: {analysis.primary_goal}
            </Typography>
            <Typography variant="subtitle2">抽出された要件 ({analysis.requirements.length} 件)</Typography>
            <Stack component="ul" sx={{ pl: 3, m: 0 }}>
              {analysis.requirements.map((requirement) => (
                <Typography component="li" variant="body2" key={requirement.id}>
                  {requirement.title}
                </Typography>
              ))}
            </Stack>
          </Stack>
        )
      });
    }
    if (architecture) {
      messages.push({
        id: "architecture",
        role: "agent",
        title: "アーキテクト",
        content: (
          <Stack spacing={1}>
            <Typography variant="body1">{architecture.rationale}</Typography>
            <Typography variant="body2" color="text.secondary">
              UI ステップ: {Array.isArray(architecture.ui_structure?.steps) ? architecture.ui_structure.steps.length : 0} /
              パイプライン: {architecture.pipeline_structure.length} ステップ
            </Typography>
          </Stack>
        )
      });
    }
    if (validation) {
      messages.push({
        id: "validation",
        role: "agent",
        title: "バリデータ",
        content: (
          <Stack spacing={1}>
            <Typography variant="body1">
              {validation.valid ? "workflow.yaml はすべての検証を通過しました。" : "workflow.yaml の修正が必要です。"}
            </Typography>
            {(validation.schema_errors.length > 0 || validation.llm_errors.length > 0) && (
              <Stack spacing={0.5}>
                {validation.schema_errors.length > 0 && (
                  <Typography variant="body2" color="text.secondary">
                    スキーマエラー: {validation.schema_errors.join(" / ")}
                  </Typography>
                )}
                {validation.llm_errors.length > 0 && (
                  <Typography variant="body2" color="text.secondary">
                    LLM エラー: {validation.llm_errors.join(" / ")}
                  </Typography>
                )}
              </Stack>
            )}
          </Stack>
        )
      });
    }
    if (workflowYaml) {
      messages.push({
        id: "yaml",
        role: "agent",
        title: "YAML スペシャリスト",
        content: (
          <Typography variant="body1">
            workflow.yaml の生成とパッケージングが完了しました。ダウンロードしてローカルで実行できます。
          </Typography>
        )
      });
    }
    return messages;
  }, [activePrompt, analysis, architecture, validation, workflowYaml]);

  const progressSteps = useMemo<JobStep[]>(() => {
    const jobSteps = status?.steps ?? [];
    return WORKFLOW_STEP_ORDER.map(({ id, label }) => {
      const existing = jobSteps.find((step) => step.id === id);
      if (existing) {
        return existing;
      }
      return {
        id,
        label,
        status: "pending" as StepStatus,
        message: undefined,
        logs: []
      };
    });
  }, [status]);

  const errorMessage = useMemo(() => {
    if (submitError) return submitError;
    if (pollingError) return pollingError;
    if (status?.status === "failed") {
      const failingStep = status.steps.find((step) => step.status === "failed");
      return failingStep?.message ?? "ワークフロー生成でエラーが発生しました。";
    }
    return null;
  }, [submitError, pollingError, status]);

  const errorDetails = useMemo(() => {
    if (status?.status !== "failed") return undefined;
    const failingStep = status.steps.find((step) => step.status === "failed");
    return failingStep?.logs && failingStep.logs.length > 0 ? failingStep.logs : undefined;
  }, [status]);

  const isProcessing = useMemo(() => {
    if (!jobId) return false;
    if (!status) return true;
    return status.status !== "completed" && status.status !== "failed";
  }, [jobId, status]);

  const handleFormChange = <K extends keyof PromptComposerValues>(field: K, value: PromptComposerValues[K]) => {
    setFormValues((prev) => ({ ...prev, [field]: value }));
  };

  const validateForm = () => {
    const errors: PromptComposerErrors = {};
    if (!formValues.prompt || formValues.prompt.trim().length < 10) {
      errors.prompt = "10文字以上で入力してください";
    }
    if (!formValues.userId.trim()) {
      errors.userId = "ユーザー ID を入力してください";
    }
    if (!formValues.projectId.trim()) {
      errors.projectId = "プロジェクト ID を入力してください";
    }
    if (!formValues.projectName.trim()) {
      errors.projectName = "プロジェクト名を入力してください";
    }
    if (!formValues.description.trim()) {
      errors.description = "プロジェクト概要を入力してください";
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async () => {
    if (!validateForm()) {
      return;
    }
    const payload: GenerationRequest = {
      user_id: formValues.userId.trim(),
      project_id: formValues.projectId.trim(),
      project_name: formValues.projectName.trim(),
      description: formValues.description.trim(),
      mock_spec_id: "invoice-verification",
      options: {
        include_playwright: true,
        include_docker: true,
        include_logging: true
      },
      requirements_prompt: formValues.prompt.trim(),
      use_mock: false
    };

    setSubmitting(true);
    setSubmitError(null);
    try {
      const response = await createWorkflowJob(payload);
      setJobId(response.job_id);
      setActivePrompt(payload.requirements_prompt ?? "");
      logger.info("Workflow generation job created", response.job_id);
    } catch (error) {
      setSubmitError("ジョブの作成に失敗しました。バックエンドが起動しているか確認してください。");
      logger.error("Failed to create workflow job", error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    stop();
    setJobId(null);
    setActivePrompt("");
    setFormErrors({});
    setFormValues(DEFAULT_FORM_VALUES);
    setSubmitError(null);
  };

  return (
    <Box sx={{ bgcolor: "#f5f7fb", minHeight: "100vh", py: 6 }}>
      <Container maxWidth="lg">
        <Stack spacing={3}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              Declarative Workflow Studio
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              プロンプトから workflow.yaml を生成し、アプリケーションとしてダウンロードできます。
            </Typography>
          </Box>

          {errorMessage && (
            <ErrorBanner message={errorMessage} details={errorDetails} onRetry={status?.status === "failed" ? refresh : undefined} />
          )}

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <PromptComposer
                values={formValues}
                errors={formErrors}
                onChange={handleFormChange}
                onSubmit={handleSubmit}
                onReset={handleReset}
                submitting={submitting || pollingLoading}
                disabled={isProcessing}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <ConversationPanel messages={conversationMessages} />
            </Grid>
          </Grid>

          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <JobProgressCard steps={progressSteps} status={status?.status ?? null} />
            </Grid>
            <Grid item xs={12} md={6}>
              <YamlPreviewCard yaml={workflowYaml} />
            </Grid>
          </Grid>

          <WorkflowInsights analysis={analysis} architecture={architecture} validation={validation} />

          <DownloadArtifactCard
            downloadUrl={status?.download_url}
            disabled={status?.status !== "completed"}
            onRestart={handleReset}
          />
        </Stack>
      </Container>
    </Box>
  );
}
