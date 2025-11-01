import { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Container,
  Divider,
  FormControlLabel,
  Grid,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

import { ErrorBanner } from "./components/ErrorBanner";
import { createGenerationJob } from "./api";
import type { GenerationRequest, GenerationStatus } from "./types";
import { useJobPolling } from "./hooks/useJobPolling";
import { logger } from "./utils/logger";

const STEP_LABELS: Record<string, string> = {
  requirements: "要件受付",
  analysis: "要件分析",
  architecture: "アーキテクチャ設計",
  yaml_generation: "YAML生成",
  validation: "スキーマ検証",
  mock_workflow: "モックworkflow読込",
  packaging: "パッケージング",
};

type FormState = {
  userId: string;
  projectId: string;
  projectName: string;
  prompt: string;
  useMock: boolean;
};

const DEFAULT_FORM: FormState = {
  userId: "demo-user",
  projectId: "workflow-demo",
  projectName: "Workflow Demo App",
  prompt: "中小企業の請求書を検証して要約するアプリを作ってください",
  useMock: true,
};

export default function App() {
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const { status, loading: pollingLoading, error: pollingError, refresh, stop } = useJobPolling(jobId);

  const workflowYaml = useMemo(() => {
    const raw = status?.metadata?.workflow_yaml;
    return typeof raw === "string" ? raw : "";
  }, [status?.metadata]);

  const notes = useMemo(() => {
    const raw = status?.metadata?.notes;
    if (Array.isArray(raw)) {
      return raw.map((item) => String(item));
    }
    return [];
  }, [status?.metadata]);

  const handleChange = (field: keyof FormState) => (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = field === "useMock" ? event.target.checked : event.target.value;
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    setSubmitError(null);
    stop();

    const payload: GenerationRequest = {
      user_id: form.userId.trim() || "demo-user",
      project_id: form.projectId.trim() || "workflow-demo",
      project_name: form.projectName.trim() || "Workflow Demo App",
      description: form.prompt,
      mock_spec_id: "invoice-verification",
      options: {
        include_playwright: false,
        include_docker: false,
        include_logging: false,
      },
      requirements_prompt: form.prompt,
      use_mock: form.useMock,
    };

    try {
      const response = await createGenerationJob(payload);
      setJobId(response.job_id);
      logger.info("Generation job created", response.job_id);
    } catch (error) {
      setSubmitError("ジョブの作成に失敗しました。バックエンドが起動しているか確認してください。");
      logger.error("Failed to create generation job", error);
    } finally {
      setSubmitting(false);
    }
  };

  const handleReset = () => {
    stop();
    setJobId(null);
    setSubmitError(null);
  };

  const effectiveError = submitError ?? pollingError ?? (status?.status === "failed" ? "バックエンドでエラーが発生しました。" : null);
  const failingLogs = useMemo(() => {
    if (status?.status !== "failed") return undefined;
    const failure = status.steps.find((step) => step.status === "failed");
    return failure?.logs;
  }, [status]);

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="lg">
        <Stack spacing={4}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              宣言的ワークフロー生成ダッシュボード
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              プロンプトを入力すると、LLMエージェントが workflow.yaml を生成し、汎用エンジンで実行できるパッケージを作成します。
            </Typography>
          </Box>

          {effectiveError && (
            <ErrorBanner message={effectiveError} details={failingLogs ?? undefined} onRetry={refresh} />
          )}

          <Paper component="form" onSubmit={handleSubmit} variant="outlined" sx={{ p: 4 }}>
            <Stack spacing={3}>
              <Typography variant="h6">ワークフロー要件</Typography>
              <Grid container spacing={2}>
                <Grid item xs={12} md={4}>
                  <TextField
                    label="ユーザー ID"
                    value={form.userId}
                    onChange={handleChange("userId")}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    label="プロジェクト ID"
                    value={form.projectId}
                    onChange={handleChange("projectId")}
                    fullWidth
                  />
                </Grid>
                <Grid item xs={12} md={4}>
                  <TextField
                    label="プロジェクト名"
                    value={form.projectName}
                    onChange={handleChange("projectName")}
                    fullWidth
                  />
                </Grid>
              </Grid>

              <TextField
                label="アプリケーション要件 / プロンプト"
                value={form.prompt}
                onChange={handleChange("prompt")}
                fullWidth
                multiline
                minRows={4}
                placeholder="例: 請求書をアップロードして合計金額と期日を抽出し、検証レポートを作成してください"
              />

              <FormControlLabel
                control={<Switch checked={form.useMock} onChange={handleChange("useMock")} />}
                label="モックワークフローを使用 (LLMを使わず決め打ちの workflow.yaml を利用)"
              />

              <Stack direction="row" spacing={2}>
                <Button type="submit" variant="contained" disabled={submitting}>
                  {submitting ? "送信中..." : "workflow.yaml を生成"}
                </Button>
                <Button variant="outlined" onClick={handleReset} disabled={submitting && !jobId}>
                  リセット
                </Button>
              </Stack>

              {jobId && (
                <Alert severity="info">現在のジョブ ID: {jobId}</Alert>
              )}
            </Stack>
          </Paper>

          <Grid container spacing={3}>
            <Grid item xs={12} md={5}>
              <Paper variant="outlined" sx={{ p: 3 }}>
                <Typography variant="h6" gutterBottom>
                  進捗
                </Typography>
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  {pollingLoading && "進捗を取得しています..."}
                  {!pollingLoading && !status && "ジョブが開始されていません。"}
                  {status && `現在のステータス: ${translateJobStatus(status.status)}`}
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Stack spacing={1.5}>
                  {renderSteps(status)}
                </Stack>
              </Paper>

              <Paper variant="outlined" sx={{ p: 3, mt: 3 }}>
                <Typography variant="h6" gutterBottom>
                  メモ / サマリ
                </Typography>
                {notes.length === 0 ? (
                  <Typography variant="body2" color="text.secondary">
                    まだ注記はありません。
                  </Typography>
                ) : (
                  <Stack component="ul" spacing={1} sx={{ pl: 2 }}>
                    {notes.map((note, index) => (
                      <Typography component="li" key={index} variant="body2">
                        {note}
                      </Typography>
                    ))}
                  </Stack>
                )}
              </Paper>

              {status?.download_url && (
                <Paper variant="outlined" sx={{ p: 3, mt: 3 }}>
                  <Typography variant="h6" gutterBottom>
                    パッケージ
                  </Typography>
                  <Typography variant="body2" color="text.secondary" gutterBottom>
                    ダウンロードした zip に含まれる `workflow.yaml` と `.env` を調整し、`docker compose up` を実行してください。
                  </Typography>
                  <Button component="a" href={status.download_url} variant="contained">
                    app.zip をダウンロード
                  </Button>
                </Paper>
              )}
            </Grid>

            <Grid item xs={12} md={7}>
              <Paper variant="outlined" sx={{ p: 3, minHeight: 400 }}>
                <Typography variant="h6" gutterBottom>
                  workflow.yaml プレビュー
                </Typography>
                {workflowYaml ? (
                  <Box component="pre" sx={{ bgcolor: "#0b1021", color: "#d8dee9", p: 2, borderRadius: 1, overflowX: "auto" }}>
                    {workflowYaml}
                  </Box>
                ) : (
                  <Typography variant="body2" color="text.secondary">
                    まだ YAML が生成されていません。ジョブが完了するとここに表示されます。
                  </Typography>
                )}
              </Paper>
            </Grid>
          </Grid>
        </Stack>
      </Container>
    </Box>
  );
}

function renderSteps(status: GenerationStatus | null | undefined) {
  if (!status) {
    return <Typography variant="body2">ステップ情報がありません。</Typography>;
  }
  return status.steps.map((step) => (
    <Paper key={step.id} variant="outlined" sx={{ p: 2 }}>
      <Typography variant="subtitle2">{STEP_LABELS[step.id] ?? step.label ?? step.id}</Typography>
      <Typography variant="caption" color="text.secondary">
        ステータス: {translateStepStatus(step.status)}
      </Typography>
      {step.message && (
        <Typography variant="body2" sx={{ mt: 0.5 }}>
          {step.message}
        </Typography>
      )}
    </Paper>
  ));
}

function translateJobStatus(status: GenerationStatus["status"]): string {
  switch (status) {
    case "received":
      return "要件受付";
    case "analysing":
      return "要件分析中";
    case "architecting":
      return "アーキテクチャ設計中";
    case "workflow_generating":
      return "workflow.yaml 生成中";
    case "validating":
      return "スキーマ検証中";
    case "packaging":
      return "パッケージング中";
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    default:
      return status;
  }
}

function translateStepStatus(status: string): string {
  switch (status) {
    case "pending":
      return "未着手";
    case "running":
      return "実行中";
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    default:
      return status;
  }
}

