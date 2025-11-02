import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Divider,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import { useCallback, useEffect, useMemo, useState } from "react";

import {
  downloadConversationPackage,
  fetchConversation,
  startConversation
} from "./api";
import type { ConversationMessage, ConversationSession } from "./types";

const POLLING_INTERVAL = 2500;
const DEFAULT_USER_ID = "demo-user";
const DEFAULT_PROJECT_ID = "invoice-workflow";
const DEFAULT_PROJECT_NAME = "請求書データ抽出アプリ";

function roleLabel(role: ConversationMessage["role"]): string {
  switch (role) {
    case "user":
      return "ユーザー";
    case "assistant":
      return "アシスタント";
    case "system":
      return "システム";
    default:
      return String(role);
  }
}

export default function App() {
  const [userId, setUserId] = useState(DEFAULT_USER_ID);
  const [projectId, setProjectId] = useState(DEFAULT_PROJECT_ID);
  const [projectName, setProjectName] = useState(DEFAULT_PROJECT_NAME);
  const [prompt, setPrompt] = useState("");
  const [session, setSession] = useState<ConversationSession | null>(null);
  const [workflowPreview, setWorkflowPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [pollingError, setPollingError] = useState<string | null>(null);

  const isRunning = session?.status === "running";
  const canDownload = session?.status === "completed" && Boolean(session.workflow_yaml ?? workflowPreview);

  useEffect(() => {
    if (!session || session.status !== "running") {
      return undefined;
    }
    let cancelled = false;
    let timer: number | undefined;

    const poll = async () => {
      try {
        const updated = await fetchConversation(session.session_id);
        if (cancelled) return;
        setSession(updated);
        setPollingError(null);
        if (updated.workflow_yaml) {
          setWorkflowPreview(updated.workflow_yaml);
        }
        if (updated.status === "running") {
          timer = window.setTimeout(poll, POLLING_INTERVAL);
        }
      } catch (err) {
        console.error("Failed to poll conversation", err);
        if (!cancelled) {
          setPollingError("対話の更新に失敗しました。ネットワークを確認してください。");
          timer = window.setTimeout(poll, POLLING_INTERVAL * 2);
        }
      }
    };

    timer = window.setTimeout(poll, POLLING_INTERVAL);
    return () => {
      cancelled = true;
      if (timer !== undefined) {
        window.clearTimeout(timer);
      }
    };
  }, [session?.session_id, session?.status]);

  const handleSubmit = useCallback(async () => {
    const trimmedPrompt = prompt.trim();
    if (!trimmedPrompt) {
      setError("プロンプトを入力してください。");
      return;
    }
    if (!userId.trim() || !projectId.trim() || !projectName.trim()) {
      setError("ユーザーID、プロジェクトID、プロジェクト名を入力してください。");
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await startConversation({
        user_id: userId.trim(),
        project_id: projectId.trim(),
        project_name: projectName.trim(),
        prompt: trimmedPrompt
      });
      setSession(response);
      setWorkflowPreview(response.workflow_yaml ?? null);
      setError(null);
      setPrompt("");
    } catch (err) {
      console.error("Failed to start conversation", err);
      setError("LLMとの対話を開始できませんでした。サーバーの状態を確認してください。");
    } finally {
      setIsSubmitting(false);
    }
  }, [prompt, userId, projectId, projectName]);

  const handleReset = useCallback(() => {
    setSession(null);
    setWorkflowPreview(null);
    setError(null);
    setPollingError(null);
    setPrompt("");
  }, []);

  const handleDownload = useCallback(async () => {
    if (!session) return;
    setIsDownloading(true);
    try {
      const blob = await downloadConversationPackage(session.session_id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${projectId || "app"}.zip`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download package", err);
      setError("成果物のダウンロードに失敗しました。");
    } finally {
      setIsDownloading(false);
    }
  }, [session, projectId]);

  const conversationMessages = useMemo(() => session?.messages ?? [], [session]);

  return (
    <Container maxWidth="lg" sx={{ py: 6 }}>
      <Stack spacing={4}>
        <Box>
          <Typography variant="h4" fontWeight={700} gutterBottom>
            宣言的アプリ生成コンソール
          </Typography>
          <Typography variant="body1" color="text.secondary">
            自然言語で要件を入力すると、LLMが workflow.yaml を生成し、Docker パッケージとしてダウンロードできます。
          </Typography>
        </Box>

        <Paper elevation={2} sx={{ p: 3 }}>
          <Stack spacing={2}>
            <Typography variant="h6" fontWeight={600}>
              プロジェクト情報
            </Typography>
            <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
              <TextField
                label="ユーザーID"
                value={userId}
                onChange={(event) => setUserId(event.target.value)}
                fullWidth
              />
              <TextField
                label="プロジェクトID"
                value={projectId}
                onChange={(event) => setProjectId(event.target.value)}
                fullWidth
              />
              <TextField
                label="プロジェクト名"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                fullWidth
              />
            </Stack>
            <TextField
              label="生成したいアプリの要件"
              placeholder="例: 請求書のPDFから金額と取引先を抽出してスプレッドシートにまとめてください"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              multiline
              minRows={3}
              disabled={isRunning}
            />
            <Stack direction="row" spacing={2}>
              <Button
                variant="contained"
                onClick={handleSubmit}
                disabled={isSubmitting || isRunning}
              >
                {isSubmitting ? <CircularProgress size={20} color="inherit" /> : "LLMに依頼"}
              </Button>
              <Button variant="outlined" color="inherit" onClick={handleReset} disabled={!session}>
                リセット
              </Button>
            </Stack>
            {error && <Alert severity="error">{error}</Alert>}
            {pollingError && <Alert severity="warning">{pollingError}</Alert>}
          </Stack>
        </Paper>

        <Stack direction={{ xs: "column", md: "row" }} spacing={3}>
          <Paper elevation={2} sx={{ p: 3, flex: 1 }}>
            <Stack spacing={2}>
              <Typography variant="h6" fontWeight={600}>
                LLMとの対話ログ
              </Typography>
              <Divider />
              {conversationMessages.length === 0 ? (
                <Typography color="text.secondary">
                  ここに対話の流れが表示されます。まずは要件を入力してください。
                </Typography>
              ) : (
                <Stack spacing={2}>
                  {conversationMessages.map((message, index) => (
                    <Box key={`${message.created_at}-${index}`}>
                      <Typography variant="subtitle2" color="text.secondary">
                        {roleLabel(message.role)}
                      </Typography>
                      <Paper variant="outlined" sx={{ p: 2, mt: 0.5 }}>
                        <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
                          {message.content}
                        </Typography>
                      </Paper>
                    </Box>
                  ))}
                  {isRunning && (
                    <Stack direction="row" spacing={1} alignItems="center">
                      <CircularProgress size={16} />
                      <Typography variant="body2" color="text.secondary">
                        workflow.yaml を生成しています...
                      </Typography>
                    </Stack>
                  )}
                </Stack>
              )}
            </Stack>
          </Paper>

          <Paper elevation={2} sx={{ p: 3, flex: 1 }}>
            <Stack spacing={2} sx={{ height: "100%" }}>
              <Typography variant="h6" fontWeight={600}>
                workflow.yaml プレビュー
              </Typography>
              <Divider />
              {workflowPreview ? (
                <Box
                  component="pre"
                  sx={{
                    bgcolor: "grey.900",
                    color: "grey.100",
                    p: 2,
                    borderRadius: 1,
                    fontFamily: "monospace",
                    overflow: "auto",
                    flex: 1,
                    maxHeight: 360
                  }}
                >
                  {workflowPreview}
                </Box>
              ) : (
                <Typography color="text.secondary">
                  生成が完了すると、ここに workflow.yaml の内容が表示されます。
                </Typography>
              )}
              <Button
                variant="contained"
                color="secondary"
                disabled={!canDownload || isDownloading}
                onClick={() => void handleDownload()}
              >
                {isDownloading ? <CircularProgress size={20} color="inherit" /> : "Dockerパッケージをダウンロード"}
              </Button>
            </Stack>
          </Paper>
        </Stack>
      </Stack>
    </Container>
  );
}

