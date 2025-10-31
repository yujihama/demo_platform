import { useEffect, useMemo, useState } from "react";
import { Box, Container, Paper, Stack, Typography, Tabs, Tab } from "@mui/material";

import { StepRequirements } from "./components/StepRequirements";
import { StepProgress } from "./components/StepProgress";
import { StepPreview } from "./components/StepPreview";
import { StepLogs } from "./components/StepLogs";
import { StepDownload } from "./components/StepDownload";
import { ErrorBanner } from "./components/ErrorBanner";
import { createGenerationJob, fetchFeaturesConfig } from "./api";
import type { FeaturesConfig, GenerationRequest, GenerationStatus, JobStep } from "./types";
import { useJobPolling } from "./hooks/useJobPolling";
import { usePreview } from "./hooks/usePreview";
import { logger } from "./utils/logger";

const STEP_NAME_MAP: Record<string, string> = {
  requirements: "要件受付",
  requirements_decomposition: "要件分解",
  app_type_classification: "アプリタイプ分類",
  component_selection: "コンポーネント選定",
  data_flow_design: "データフロー設計",
  validation: "仕様バリデーション",
  mock_agent: "モック仕様",
  preview: "プレビュー",
  template_generation: "テンプレート生成",
  backend_setup: "バックエンド構築",
  testing: "テスト準備",
  packaging: "パッケージング"
};

export default function App() {
  const [features, setFeatures] = useState<FeaturesConfig | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [specId, setSpecId] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [previewApproved, setPreviewApproved] = useState(false);
  const [lastUseMock, setLastUseMock] = useState(true);

  useEffect(() => {
    let active = true;
    fetchFeaturesConfig()
      .then((config) => {
        if (!active) return;
        setFeatures(config);
        setLastUseMock(config.agents.use_mock);
      })
      .catch((error) => logger.warn("Failed to load feature config", error));
    return () => {
      active = false;
    };
  }, []);

  const stepLabels = useMemo(
    () => [
      "要件入力",
      "進捗ダッシュボード",
      lastUseMock ? "モックプレビュー" : "エージェント設計",
      "テンプレート生成",
      "バックエンド設定",
      "テスト・パッケージ",
      "成果物ダウンロード"
    ],
    [lastUseMock]
  );

  const { status, loading: pollingLoading, error: pollingError, refresh, stop } = useJobPolling(jobId);
  const { html, loading: previewLoading, error: previewError } = usePreview(specId);

  const handleSubmit = async (payload: GenerationRequest) => {
    setSubmitLoading(true);
    setSubmitError(null);
    try {
      const response = await createGenerationJob(payload);
      const effectiveUseMock = payload.use_mock ?? features?.agents.use_mock ?? true;
      setJobId(response.job_id);
      setLastUseMock(effectiveUseMock);
      setSpecId(effectiveUseMock ? payload.mock_spec_id : null);
      setActiveStep(1);
      setPreviewApproved(!effectiveUseMock);
      logger.info("Generation job created", response.job_id);
    } catch (error) {
      setSubmitError("ジョブの作成に失敗しました。バックエンドが起動しているか確認してください。");
      logger.error("Failed to create generation job", error);
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleApprovePreview = () => {
    setPreviewApproved(true);
    setActiveStep((prev) => Math.max(prev, 3));
    logger.info("Preview approved, proceeding to build steps");
  };

  const handleRejectPreview = () => {
    stop();
    setJobId(null);
    setSpecId(null);
    setActiveStep(0);
    logger.warn("Preview rejected by user; returning to requirements");
  };

  const handleRestart = () => {
    stop();
    setJobId(null);
    setSpecId(null);
    const defaultUseMock = features?.agents.use_mock ?? true;
    setLastUseMock(defaultUseMock);
    setPreviewApproved(!defaultUseMock);
    setActiveStep(0);
    setSubmitError(null);
    logger.info("Wizard restarted");
  };

  const errorMessage = useMemo(() => {
    if (submitError) return submitError;
    if (pollingError) return pollingError;
    if (status?.status === "failed") {
      const failingStep = status.steps.find((step) => step.status === "failed");
      return failingStep?.message ?? "バックエンドでエラーが発生しました。";
    }
    return null;
  }, [submitError, pollingError, status]);

  const errorDetails = useMemo(() => {
    if (status?.status !== "failed") return null;
    const failingStep = status.steps.find((step) => step.status === "failed");
    return failingStep?.logs ?? null;
  }, [status]);

  const templateSteps = filterSteps(status, ["template_generation"]);
  const backendSteps = filterSteps(status, ["backend_setup"]);
  const packagingSteps = filterSteps(status, ["testing", "packaging"]);

  const canShowPreview = Boolean(status);

  useEffect(() => {
    if (!jobId) return;
    setActiveStep((prev) => (prev < 1 ? 1 : prev));
  }, [jobId]);

  useEffect(() => {
    if (!status) return;
    if (status.status === "failed") return;

    if (previewApproved) {
      setActiveStep((prev) => Math.max(prev, 3));
    }

    if (status.status === "templates_rendering" && previewApproved) {
      setActiveStep((prev) => Math.max(prev, 3));
    }

    if (status.status === "packaging") {
      setActiveStep((prev) => Math.max(prev, 5));
      logger.info("Packaging in progress", status.job_id);
    }

    if (status.status === "completed") {
      setActiveStep((prev) => Math.max(prev, 6));
      logger.info("Generation completed", status.job_id);
    }
  }, [status, previewApproved]);

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="lg">
        <Stack spacing={3}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              モック生成ウィザード
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Phase 1 (MVP) の要件に基づき、モック仕様からテンプレートベースの成果物を生成します。
            </Typography>
          </Box>

          <Paper variant="outlined">
            <Tabs
              value={activeStep}
              onChange={(_, value) => canNavigateToStep(value, { jobId, status, previewApproved }) && setActiveStep(value)}
              variant="scrollable"
              scrollButtons="auto"
            >
              {stepLabels.map((label, index) => (
                <Tab key={label} label={`${index + 1}. ${label}`} />
              ))}
            </Tabs>
          </Paper>

          {errorMessage && <ErrorBanner message={errorMessage} details={errorDetails ?? undefined} onRetry={refresh} />}

          {activeStep === 0 && (
            <Paper variant="outlined" sx={{ p: 4 }}>
              <StepRequirements onSubmit={handleSubmit} loading={submitLoading} error={submitError} features={features} />
            </Paper>
          )}

          {activeStep === 1 && (
            <StepProgress status={status ?? null} loading={pollingLoading} />
          )}

          {activeStep === 2 && (
            lastUseMock ? (
              canShowPreview && (
                <StepPreview
                  html={html}
                  loading={previewLoading}
                  error={previewError}
                  onApprove={handleApprovePreview}
                  onReject={handleRejectPreview}
                />
              )
            ) : (
              <Paper variant="outlined" sx={{ p: 4 }}>
                <Typography variant="h6" gutterBottom>
                  エージェント設計プレビュー
                </Typography>
                <Typography color="text.secondary">
                  LLMモードではプレビューはありません。進捗ダッシュボードで各エージェントのステータスを確認してください。
                </Typography>
              </Paper>
            )
          )}

          {activeStep === 3 && (
            <StepLogs title="テンプレート生成" steps={templateSteps} />
          )}

          {activeStep === 4 && (
            <StepLogs title="バックエンド構築" steps={backendSteps} />
          )}

          {activeStep === 5 && (
            <StepLogs title="テスト・パッケージング" steps={packagingSteps} />
          )}

          {activeStep === 6 && <StepDownload status={status ?? null} onRestart={handleRestart} />}

          <Paper variant="outlined" sx={{ p: 3 }}>
            <Typography variant="subtitle2" gutterBottom>
              現在のジョブ ID
            </Typography>
            <Typography color="text.secondary">{jobId ?? "未生成"}</Typography>
          </Paper>
        </Stack>
      </Container>
    </Box>
  );
}

function filterSteps(status: GenerationStatus | null | undefined, ids: string[]): JobStep[] {
  if (!status) {
    return ids.map(
      (id) => ({ id, label: STEP_NAME_MAP[id] ?? id, status: "pending" } as JobStep)
    );
  }
  return status.steps.filter((step) => ids.includes(step.id));
}

function canNavigateToStep(
  step: number,
  context: { jobId: string | null; status: GenerationStatus | null | undefined; previewApproved: boolean }
) {
  const { jobId, status, previewApproved } = context;
  if (step === 0) return true;
  if (!jobId) return false;
  if (step === 1) return true;
  if (step === 2) return Boolean(status);
  if (step >= 3 && step <= 5) {
    if (!status) return false;
    if (!previewApproved) return false;
    return true;
  }
  if (step === 6) {
    return status?.status === "completed";
  }
  return false;
}

