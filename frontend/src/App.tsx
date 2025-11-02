import { ChangeEvent, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HourglassBottomIcon from "@mui/icons-material/HourglassBottom";
import PlayArrowRoundedIcon from "@mui/icons-material/PlayArrowRounded";

import { createGenerationJob } from "./api";
import type { GenerationRequest, GenerationStatus, JobStep, WorkflowMetadata } from "./types";
import { useJobPolling } from "./hooks/useJobPolling";
import { logger } from "./utils/logger";

const DEFAULT_FORM = {
  userId: "demo-user",
  projectId: "workflow-app",
  projectName: "宣言的ワークフローアプリ",
  description: "LLMエージェントが生成したworkflow.yamlを確認するためのプロジェクト",
  requirements: "請求書のAIチェックを行うワークフローを作成してください。"
};

function buildRequest(form: typeof DEFAULT_FORM): GenerationRequest {
  return {
    user_id: form.userId,
    project_id: form.projectId,
    project_name: form.projectName,
    description: form.description,
    mock_spec_id: "invoice-verification",
    options: {
      include_docker: true,
      include_logging: true,
      include_playwright: true
    },
    requirements_prompt: form.requirements,
    use_mock: false
  };
}

function stepIcon(step: JobStep) {
  if (step.status === "completed") {
    return <CheckCircleOutlineIcon color="success" />;
  }
  if (step.status === "failed") {
    return <ErrorOutlineIcon color="error" />;
  }
  if (step.status === "running") {
    return <HourglassBottomIcon color="warning" />;
  }
  return <HourglassBottomIcon color="disabled" />;
}

function StepList({ status }: { status: GenerationStatus | null }) {
  if (!status) {
    return (
      <Typography color="text.secondary" variant="body2">
        まだジョブは開始されていません。
      </Typography>
    );
  }

  return (
    <List disablePadding>
      {status.steps.map((step) => (
        <ListItem key={step.id} sx={{ alignItems: "flex-start" }}>
          <ListItemIcon sx={{ minWidth: 40 }}>{stepIcon(step)}</ListItemIcon>
          <ListItemText
            primary={`${step.label}`}
            secondary={step.message ?? "進行中"}
            primaryTypographyProps={{ fontWeight: step.status === "running" ? 600 : 500 }}
          />
          <Chip label={translateStepStatus(step.status)} size="small" color={chipColor(step.status)} />
        </ListItem>
      ))}
    </List>
  );
}

function chipColor(status: JobStep["status"]) {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "error";
    case "running":
      return "warning";
    default:
      return "default";
  }
}

function translateStepStatus(status: JobStep["status"]) {
  switch (status) {
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    case "running":
      return "進行中";
    default:
      return "待機";
  }
}

function MetadataPanels({ metadata }: { metadata: WorkflowMetadata | null | undefined }) {
  if (!metadata) {
    return (
      <Typography color="text.secondary" variant="body2">
        生成が完了すると、解析結果とworkflow.yamlが表示されます。
      </Typography>
    );
  }

  return (
    <Stack spacing={3}>
      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          要件分析サマリー
        </Typography>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "var(--font-mono, 'Roboto Mono', monospace)" }}>
          {JSON.stringify(metadata.analysis, null, 2)}
        </pre>
      </Paper>

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          アーキテクチャ設計
        </Typography>
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", fontFamily: "var(--font-mono, 'Roboto Mono', monospace)" }}>
          {JSON.stringify(metadata.architecture, null, 2)}
        </pre>
      </Paper>

      <Paper variant="outlined" sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          workflow.yaml
        </Typography>
        <Box component="pre" sx={{ mt: 1, p: 2, bgcolor: "grey.100", borderRadius: 1, overflow: "auto" }}>
          {metadata.workflow_yaml}
        </Box>
      </Paper>
    </Stack>
  );
}

export default function App() {
  const [form, setForm] = useState(DEFAULT_FORM);
  const [jobId, setJobId] = useState<string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [submitLoading, setSubmitLoading] = useState(false);

  const { status, loading: pollingLoading, error: pollingError, refresh } = useJobPolling(jobId);

  const effectiveMetadata = useMemo(() => status?.metadata ?? null, [status]);

  const handleChange = (field: keyof typeof DEFAULT_FORM) =>
    (event: ChangeEvent<HTMLInputElement>) => {
      setForm((prev) => ({ ...prev, [field]: event.target.value }));
    };

  const handleSubmit = async () => {
    setSubmitLoading(true);
    setSubmitError(null);
    try {
      const payload = buildRequest(form);
      const response = await createGenerationJob(payload);
      setJobId(response.job_id);
      logger.info("Workflow generation job created", response.job_id);
    } catch (error) {
      logger.error("Failed to create workflow generation job", error);
      setSubmitError("ジョブの作成に失敗しました。バックエンドのログを確認してください。");
    } finally {
      setSubmitLoading(false);
    }
  };

  const showDownload = status?.status === "completed" && status.download_url;

  return (
    <Box sx={{ bgcolor: "#f5f7fb", minHeight: "100vh", py: 6 }}>
      <Container maxWidth="lg">
        <Stack spacing={4}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              宣言的ワークフロー生成（Phase 3）
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              LLMエージェントに要求を伝えると、workflow.yamlと実行パッケージが生成されます。
            </Typography>
          </Box>

          {(submitError || pollingError) && (
            <Alert severity="error">{submitError ?? pollingError}</Alert>
          )}

          <Grid container spacing={3} alignItems="stretch">
            <Grid item xs={12} md={5}>
              <Paper variant="outlined" sx={{ p: 3, height: "100%" }}>
                <Stack spacing={2}>
                  <Typography variant="h6">LLMへの依頼内容</Typography>
                  <TextField
                    label="要件プロンプト"
                    multiline
                    minRows={6}
                    value={form.requirements}
                    onChange={handleChange("requirements")}
                    helperText="アプリの目的や要件を自然言語で記述してください"
                    fullWidth
                  />
                  <Divider />
                  <Typography variant="subtitle2" color="text.secondary">
                    メタデータ
                  </Typography>
                  <TextField label="ユーザーID" value={form.userId} onChange={handleChange("userId")} fullWidth />
                  <TextField label="プロジェクトID" value={form.projectId} onChange={handleChange("projectId")} fullWidth />
                  <TextField label="プロジェクト名" value={form.projectName} onChange={handleChange("projectName")} fullWidth />
                  <TextField
                    label="プロジェクト概要"
                    multiline
                    minRows={3}
                    value={form.description}
                    onChange={handleChange("description")}
                    fullWidth
                  />
                  <Button
                    variant="contained"
                    startIcon={<PlayArrowRoundedIcon />}
                    onClick={handleSubmit}
                    disabled={submitLoading}
                  >
                    {submitLoading ? "生成を開始しています..." : "workflow.yamlを生成"}
                  </Button>
                </Stack>
              </Paper>
            </Grid>

            <Grid item xs={12} md={7}>
              <Stack spacing={3} sx={{ height: "100%" }}>
                <Paper variant="outlined" sx={{ p: 3 }}>
                  <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
                    <Typography variant="h6">進捗</Typography>
                    {pollingLoading && <HourglassBottomIcon color="warning" />}
                  </Stack>
                  <Divider sx={{ my: 2 }} />
                  <StepList status={status ?? null} />
                  <Divider sx={{ my: 2 }} />
                  <Stack direction="row" spacing={2}>
                    {jobId && (
                      <Chip label={`ジョブID: ${jobId}`} size="small" color="default" variant="outlined" />
                    )}
                    {status && <Chip label={`状態: ${translateJobStatus(status.status)}`} size="small" color="primary" />}
                    {showDownload && (
                      <Button variant="outlined" href={status?.download_url ?? undefined} target="_blank" rel="noreferrer">
                        ZIPをダウンロード
                      </Button>
                    )}
                    {status?.status === "failed" && (
                      <Button variant="outlined" onClick={refresh}>
                        再読込
                      </Button>
                    )}
                  </Stack>
                </Paper>

                <MetadataPanels metadata={effectiveMetadata} />
              </Stack>
            </Grid>
          </Grid>
        </Stack>
      </Container>
    </Box>
  );
}

function translateJobStatus(status: GenerationStatus["status"]) {
  switch (status) {
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    case "packaging":
      return "パッケージング";
    case "spec_generating":
      return "仕様生成中";
    case "templates_rendering":
      return "テンプレート生成";
    case "received":
    default:
      return "待機";
  }
}
