import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Divider,
  Grid,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";

import { buildDownloadUrl, createGenerationJob, fetchFeaturesConfig } from "./api";
import type {
  FeaturesConfig,
  GenerationRequest,
  JobStep,
  WorkflowAnalysisMetadata,
  WorkflowArchitectureMetadata,
  WorkflowGenerationMetadata,
  WorkflowValidationMetadata
} from "./types";
import { useJobPolling } from "./hooks/useJobPolling";
import { logger } from "./utils/logger";

const DEFAULT_PROMPT =
  "経理担当者が請求書をアップロードすると自動で内容を検証し、結果をダッシュボードで確認できるワークフローアプリを作成して";

const DEFAULT_FORM = {
  userId: "workflow-studio-user",
  projectId: "workflow-studio",
  projectName: "Workflow Studio Sample",
  projectDescription: "LLMエージェントで生成されたworkflow.yamlの実行パッケージを試すプロジェクト"
};

const STEP_STATUS_LABEL: Record<JobStep["status"], string> = {
  pending: "待機中",
  running: "実行中",
  completed: "完了",
  failed: "失敗"
};

const STEP_STATUS_COLOR: Record<JobStep["status"], "default" | "info" | "success" | "error"> = {
  pending: "default",
  running: "info",
  completed: "success",
  failed: "error"
};

export default function App() {
  const [features, setFeatures] = useState<FeaturesConfig | null>(null);
  const [form, setForm] = useState(DEFAULT_FORM);
  const [prompt, setPrompt] = useState(DEFAULT_PROMPT);
  const [submittedPrompt, setSubmittedPrompt] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    fetchFeaturesConfig()
      .then((config) => {
        if (!mounted) return;
        setFeatures(config);
      })
      .catch((error) => logger.warn("機能設定の取得に失敗しました", error));
    return () => {
      mounted = false;
    };
  }, []);

  const pollingInterval = useMemo(
    () => (features?.frontend?.polling_interval_seconds ?? 2) * 1000,
    [features]
  );

  const { status, loading: pollingLoading, error: pollingError, refresh } = useJobPolling(
    jobId,
    pollingInterval
  );

  const metadata = useMemo<WorkflowGenerationMetadata | null>(() => {
    if (!status?.metadata) return null;
    return status.metadata as WorkflowGenerationMetadata;
  }, [status]);

  const analysis = metadata?.analysis as WorkflowAnalysisMetadata | undefined;
  const architecture = metadata?.architecture as WorkflowArchitectureMetadata | undefined;
  const validation = metadata?.validation as WorkflowValidationMetadata | undefined;
  const workflowYaml = metadata?.workflow_yaml ?? null;

  const isProcessing = useMemo(() => {
    if (!jobId) return false;
    if (!status) return true;
    return status.status !== "completed" && status.status !== "failed";
  }, [jobId, status]);

  const failureMessage = useMemo(() => {
    if (status?.status !== "failed") return null;
    const failedStep = status.steps.find((step) => step.status === "failed");
    return failedStep?.message ?? "エージェントの実行に失敗しました";
  }, [status]);

  const errorMessage = submitError ?? pollingError ?? failureMessage;

  const downloadUrl = buildDownloadUrl(status?.download_url ?? null);

  const chatMessages = useMemo(
    () =>
      buildChatMessages({
        submittedPrompt,
        isProcessing,
        analysis,
        architecture,
        validation
      }),
    [submittedPrompt, isProcessing, analysis, architecture, validation]
  );

  const handleInputChange = (field: keyof typeof DEFAULT_FORM) =>
    (event: ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: event.target.value }));
    };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = prompt.trim();
    if (trimmed.length < 10) {
      setSubmitError("要件プロンプトは10文字以上で入力してください。");
      return;
    }

    setSubmitLoading(true);
    setSubmitError(null);

    const payload: GenerationRequest = {
      user_id: form.userId,
      project_id: form.projectId,
      project_name: form.projectName,
      description: form.projectDescription,
      mock_spec_id: "invoice-verification",
      options: {
        include_playwright: true,
        include_docker: true,
        include_logging: true
      },
      requirements_prompt: trimmed,
      use_mock: false
    };

    try {
      const response = await createGenerationJob(payload);
      setJobId(response.job_id);
      setSubmittedPrompt(trimmed);
      logger.info("ワークフロージョブを作成しました", response.job_id);
    } catch (error) {
      logger.error("ジョブの作成に失敗しました", error);
      setSubmitError("ジョブの作成に失敗しました。バックエンドが起動しているか確認してください。");
    } finally {
      setSubmitLoading(false);
    }
  };

  const handleReset = () => {
    setJobId(null);
    setSubmittedPrompt(null);
    setPrompt(DEFAULT_PROMPT);
    setSubmitError(null);
    logger.info("画面を初期状態に戻しました");
  };

  const steps = status?.steps ?? [];

  return (
    <Box sx={{ bgcolor: "#f5f7fb", minHeight: "100vh", py: 6 }}>
      <Container maxWidth="lg">
        <Stack spacing={3}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              ワークフロー生成スタジオ
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              LLMエージェントと対話しながらworkflow.yamlと汎用実行パッケージを生成します。
            </Typography>
          </Box>

          {errorMessage && (
            <Alert severity="error" onClose={() => setSubmitError(null)}>
              {errorMessage}
            </Alert>
          )}

          <Grid container spacing={3} alignItems="stretch">
            <Grid item xs={12} md={7}>
              <Stack spacing={3} sx={{ height: "100%" }}>
                <Paper variant="outlined" sx={{ p: 3, height: "100%" }}>
                  <Stack spacing={2} sx={{ height: "100%" }}>
                    <Typography variant="h6">LLMとの対話</Typography>
                    <Divider />
                    <Stack spacing={2} sx={{ flexGrow: 1, overflowY: "auto" }} data-testid="chat-messages">
                      {chatMessages.length === 0 ? (
                        <Typography color="text.secondary">
                          プロンプトを送信すると、エージェントとの対話ログがここに表示されます。
                        </Typography>
                      ) : (
                        chatMessages.map((message) => <ChatBubble key={message.key} message={message} />)
                      )}
                    </Stack>
                    {status && (
                      <Typography variant="caption" color="text.secondary">
                        ジョブ ID: {status.job_id}
                      </Typography>
                    )}
                  </Stack>
                </Paper>

                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    生成パラメータ
                  </Typography>
                  <Box component="form" onSubmit={handleSubmit} sx={{ display: "grid", gap: 2 }}>
                    <TextField
                      label="ユーザー ID"
                      value={form.userId}
                      onChange={handleInputChange("userId")}
                      disabled={submitLoading || isProcessing}
                      required
                    />
                    <TextField
                      label="プロジェクト ID"
                      value={form.projectId}
                      onChange={handleInputChange("projectId")}
                      disabled={submitLoading || isProcessing}
                      required
                    />
                    <TextField
                      label="プロジェクト名"
                      value={form.projectName}
                      onChange={handleInputChange("projectName")}
                      disabled={submitLoading || isProcessing}
                      required
                    />
                    <TextField
                      label="プロジェクト概要"
                      value={form.projectDescription}
                      onChange={handleInputChange("projectDescription")}
                      disabled={submitLoading || isProcessing}
                      required
                      multiline
                      minRows={2}
                    />
                    <TextField
                      label="要件プロンプト"
                      value={prompt}
                      onChange={(event) => setPrompt(event.target.value)}
                      disabled={submitLoading || isProcessing}
                      multiline
                      minRows={4}
                      helperText="例: 請求書をアップロードして検証結果を表示するアプリを作成して"
                      required
                    />
                    <Stack direction="row" spacing={2}>
                      <Button
                        type="submit"
                        variant="contained"
                        disabled={submitLoading || isProcessing}
                      >
                        {submitLoading ? "送信中" : "ワークフロー生成"}
                      </Button>
                      <Button variant="outlined" onClick={handleReset} disabled={submitLoading}>
                        リセット
                      </Button>
                      {pollingLoading && (
                        <Chip label="進行中" color="info" variant="outlined" />
                      )}
                    </Stack>
                  </Box>
                </Paper>
              </Stack>
            </Grid>

            <Grid item xs={12} md={5}>
              <Stack spacing={3}>
                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    生成ステータス
                  </Typography>
                  {steps.length === 0 ? (
                    <Typography color="text.secondary">まだジョブが開始されていません。</Typography>
                  ) : (
                    <Stack spacing={1}>
                      {steps.map((step) => (
                        <Box
                          key={step.id}
                          sx={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            gap: 1,
                            p: 1.5,
                            borderRadius: 1,
                            bgcolor: "#f9fafc"
                          }}
                        >
                          <Box>
                            <Typography fontWeight={600}>{step.label}</Typography>
                            {step.message && (
                              <Typography variant="body2" color="text.secondary">
                                {step.message}
                              </Typography>
                            )}
                          </Box>
                          <Chip label={STEP_STATUS_LABEL[step.status]} color={STEP_STATUS_COLOR[step.status]} />
                        </Box>
                      ))}
                    </Stack>
                  )}
                </Paper>

                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    バリデーション結果
                  </Typography>
                  {validation ? (
                    <ValidationSummary validation={validation} />
                  ) : (
                    <Typography color="text.secondary">
                      生成と検証が完了すると、ここに結果が表示されます。
                    </Typography>
                  )}
                </Paper>

                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    workflow.yaml プレビュー
                  </Typography>
                  {workflowYaml ? (
                    <Box
                      data-testid="yaml-preview"
                      sx={{
                        bgcolor: "#111827",
                        color: "#e5e7eb",
                        p: 2,
                        borderRadius: 1,
                        fontFamily: "'Fira Code', monospace",
                        fontSize: 13,
                        maxHeight: 280,
                        overflowY: "auto"
                      }}
                    >
                      <pre style={{ margin: 0 }}>{workflowYaml}</pre>
                    </Box>
                  ) : (
                    <Typography color="text.secondary">
                      生成が完了するとworkflow.yamlが表示されます。
                    </Typography>
                  )}
                </Paper>

                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    パッケージダウンロード
                  </Typography>
                  <Typography color="text.secondary" paragraph>
                    zipファイルにはdocker-compose.yml、.env、workflow.yaml、README.mdが含まれます。
                  </Typography>
                  <Button
                    variant="contained"
                    href={downloadUrl ?? undefined}
                    target="_blank"
                    rel="noopener noreferrer"
                    disabled={!downloadUrl}
                  >
                    ZIP をダウンロード
                  </Button>
                  {downloadUrl && (
                    <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                      {downloadUrl}
                    </Typography>
                  )}
                </Paper>
              </Stack>
            </Grid>
          </Grid>

          {status?.status === "failed" && (
            <Button variant="outlined" onClick={refresh} sx={{ alignSelf: "flex-start" }}>
              状態を再取得
            </Button>
          )}
        </Stack>
      </Container>
    </Box>
  );
}

interface ChatMessage {
  key: string;
  role: "user" | "agent" | "system";
  title: string;
  content: JSX.Element;
}

function buildChatMessages(params: {
  submittedPrompt: string | null;
  isProcessing: boolean;
  analysis?: WorkflowAnalysisMetadata;
  architecture?: WorkflowArchitectureMetadata;
  validation?: WorkflowValidationMetadata;
}): ChatMessage[] {
  const { submittedPrompt, isProcessing, analysis, architecture, validation } = params;
  const messages: ChatMessage[] = [];

  if (submittedPrompt) {
    messages.push({
      key: "prompt",
      role: "user",
      title: "ユーザー",
      content: <Typography>{submittedPrompt}</Typography>
    });
  }

  if (isProcessing) {
    messages.push({
      key: "processing",
      role: "system",
      title: "システム",
      content: <Typography>エージェントがworkflow.yamlを生成しています…</Typography>
    });
  }

  if (analysis) {
    messages.push({
      key: "analysis",
      role: "agent",
      title: "Analyst Agent",
      content: <AnalysisSummary analysis={analysis} />
    });
  }

  if (architecture) {
    messages.push({
      key: "architecture",
      role: "agent",
      title: "Architect Agent",
      content: <ArchitectureSummary architecture={architecture} />
    });
  }

  if (validation) {
    messages.push({
      key: "validation",
      role: "agent",
      title: "Validator Agent",
      content: <ValidationSummary validation={validation} compact />
    });
  }

  return messages;
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const background =
    message.role === "user"
      ? "#e8f1ff"
      : message.role === "system"
      ? "#f1f5f9"
      : "#fff7ed";

  return (
    <Box
      sx={{
        borderRadius: 2,
        bgcolor: background,
        p: 2,
        border: "1px solid",
        borderColor: "divider"
      }}
    >
      <Typography variant="subtitle2" color="text.secondary" gutterBottom>
        {message.title}
      </Typography>
      {message.content}
    </Box>
  );
}

function AnalysisSummary({ analysis }: { analysis: WorkflowAnalysisMetadata }) {
  return (
    <Stack spacing={1}>
      <Typography fontWeight={600}>{analysis.summary}</Typography>
      <Typography variant="body2" color="text.secondary">
        主要目標: {analysis.primary_goal}
      </Typography>
      <Divider flexItem />
      <Stack spacing={1}>
        {analysis.requirements.map((req) => (
          <Box key={req.id} sx={{ borderLeft: "3px solid #2563eb", pl: 1.5 }}>
            <Typography fontWeight={600}>{req.title}</Typography>
            <Typography variant="body2" color="text.secondary">
              {req.description}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              カテゴリ: {req.category} / 受け入れ基準: {req.acceptance_criteria.join("、 ") || "なし"}
            </Typography>
          </Box>
        ))}
      </Stack>
    </Stack>
  );
}

function ArchitectureSummary({ architecture }: { architecture: WorkflowArchitectureMetadata }) {
  const workflowCount = Object.keys(architecture.workflows_section ?? {}).length;
  const pipelineCount = architecture.pipeline_structure?.length ?? 0;
  const infoName =
    typeof architecture.info_section?.name === "string"
      ? (architecture.info_section.name as string)
      : null;

  return (
    <Stack spacing={1}>
      <Typography fontWeight={600}>設計方針</Typography>
      <Typography variant="body2" color="text.secondary">
        {architecture.rationale}
      </Typography>
      <Divider flexItem />
      <Typography variant="body2">
        ワークフロー: {workflowCount} 件 / パイプラインステップ: {pipelineCount} 件
      </Typography>
      {infoName && (
        <Typography variant="body2" color="text.secondary">
          アプリ名: {infoName}
        </Typography>
      )}
      <Typography variant="caption" color="text.secondary">
        UI構造と詳細な設定はworkflow.yamlに含まれます。
      </Typography>
    </Stack>
  );
}

function ValidationSummary({
  validation,
  compact
}: {
  validation: WorkflowValidationMetadata;
  compact?: boolean;
}) {
  const errors = validation.all_errors ?? validation.schema_errors ?? [];
  const suggestions = validation.suggestions ?? [];

  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Chip
          label={validation.valid ? "検証成功" : "検証失敗"}
          color={validation.valid ? "success" : "error"}
        />
        {!validation.valid && (
          <Typography variant="body2" color="text.secondary">
            schema: {validation.schema_valid ? "OK" : "NG"} / llm: {validation.llm_valid ? "OK" : "NG"}
          </Typography>
        )}
      </Stack>
      {!compact && (
        <Typography variant="body2" color="text.secondary">
          LLM検証とスキーマ検証の結果を集約したメタデータです。
        </Typography>
      )}
      {errors.length > 0 && (
        <Stack spacing={0.5}>
          <Typography variant="subtitle2">エラー</Typography>
          {errors.map((error, index) => (
            <Typography key={`${error}-${index}`} variant="body2" color="error">
              ・{error}
            </Typography>
          ))}
        </Stack>
      )}
      {suggestions.length > 0 && (
        <Stack spacing={0.5}>
          <Typography variant="subtitle2">改善提案</Typography>
          {suggestions.map((suggestion, index) => (
            <Typography key={`${suggestion}-${index}`} variant="body2" color="text.secondary">
              ・{suggestion}
            </Typography>
          ))}
        </Stack>
      )}
    </Stack>
  );
}
