import { FormEvent, useCallback, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import RefreshIcon from "@mui/icons-material/Refresh";
import DownloadIcon from "@mui/icons-material/Download";

import { downloadPackage } from "./api";
import { useConversation } from "./hooks/useConversation";

function formatStatusLabel(status: string) {
  switch (status) {
    case "received":
      return "受付";
    case "spec_generating":
      return "仕様生成中";
    case "templates_rendering":
      return "テンプレート処理";
    case "packaging":
      return "パッケージング";
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    default:
      return status;
  }
}

function MessageBubble({ role, content, timestamp }: { role: string; content: string; timestamp: string }) {
  const isUser = role === "user";
  const alignment = isUser ? "flex-end" : "flex-start";
  const bgColor = isUser ? "primary.main" : "grey.200";
  const textColor = isUser ? "primary.contrastText" : "text.primary";
  return (
    <Stack spacing={0.5} alignItems={alignment}>
      <Typography variant="caption" color="text.secondary">
        {role === "assistant" ? "LLM" : role === "user" ? "あなた" : "システム"} · {new Date(timestamp).toLocaleTimeString()}
      </Typography>
      <Box
        sx={{
          bgcolor: bgColor,
          color: textColor,
          px: 2,
          py: 1.5,
          borderRadius: 2,
          maxWidth: "80%",
          whiteSpace: "pre-wrap"
        }}
      >
        {content}
      </Box>
    </Stack>
  );
}

export default function App() {
  const [userId, setUserId] = useState("demo-user");
  const [projectId, setProjectId] = useState("invoice-workflow");
  const [projectName, setProjectName] = useState("請求書抽出アプリ");
  const [prompt, setPrompt] = useState("");
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const { session, workflow, loading, error, start, refresh } = useConversation();

  const handleSubmit = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      if (!prompt.trim()) {
        return;
      }
      setDownloadError(null);
      try {
        await start({
          user_id: userId || "demo-user",
          project_id: projectId || "workflow-app",
          project_name: projectName || "生成アプリ",
          prompt: prompt.trim(),
          description: prompt.trim()
        });
        setPrompt("");
      } catch (err) {
        // start() already sets error state
      }
    },
    [prompt, userId, projectId, projectName, start]
  );

  const handleDownload = useCallback(async () => {
    if (!session) return;
    try {
      const blob = await downloadPackage(session.session_id);
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `${projectId || "app"}.zip`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
      setDownloadError(null);
    } catch (err) {
      console.error("Failed to download package", err);
      setDownloadError("パッケージのダウンロードに失敗しました");
    }
  }, [session, projectId]);

  const statusChip = useMemo(() => {
    if (!session) return null;
    const color = session.status === "failed" ? "error" : session.status === "completed" ? "success" : "default";
    return <Chip label={formatStatusLabel(session.status)} color={color as any} />;
  }, [session]);

  return (
    <Box sx={{ minHeight: "100vh", bgcolor: "#f5f7fb", py: 6 }}>
      <Container maxWidth="md">
        <Stack spacing={4}>
          <Stack spacing={1}>
            <Typography variant="h4" fontWeight={700}>
              宣言的アプリ生成デモ
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              LLM と対話しながら workflow.yaml を生成し、Docker パッケージとして取得できます。
            </Typography>
          </Stack>

          {(error || downloadError) && (
            <Alert severity="error">{error ?? downloadError}</Alert>
          )}

          <Paper variant="outlined" sx={{ p: 3 }}>
            <Stack component="form" spacing={2} onSubmit={handleSubmit}>
              <Typography variant="h6" fontWeight={600}>
                プロジェクト設定
              </Typography>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                <TextField
                  label="ユーザーID"
                  value={userId}
                  onChange={(event) => setUserId(event.target.value)}
                  fullWidth
                  required
                />
                <TextField
                  label="プロジェクトID"
                  value={projectId}
                  onChange={(event) => setProjectId(event.target.value)}
                  fullWidth
                  required
                />
              </Stack>
              <TextField
                label="プロジェクト名"
                value={projectName}
                onChange={(event) => setProjectName(event.target.value)}
                required
              />
              <Divider sx={{ my: 1 }} />
              <Typography variant="subtitle1" fontWeight={600}>
                要件プロンプト
              </Typography>
              <TextField
                label="例: 請求書からデータを抽出するアプリを作って"
                multiline
                minRows={3}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
              />
              <Stack direction="row" spacing={2} justifyContent="flex-end">
                <Button
                  type="submit"
                  variant="contained"
                  size="large"
                  disabled={loading}
                  startIcon={loading ? <CircularProgress size={18} color="inherit" /> : undefined}
                >
                  {loading ? "生成開始中" : "会話を開始"}
                </Button>
              </Stack>
            </Stack>
          </Paper>

          <Paper variant="outlined" sx={{ p: 3, minHeight: 320 }}>
            <Stack spacing={2} sx={{ height: "100%" }}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="h6" fontWeight={600}>
                  チャット履歴
                </Typography>
                <Stack direction="row" spacing={1} alignItems="center">
                  {statusChip}
                  {session && (
                    <IconButton onClick={() => void refresh()} aria-label="refresh" size="small">
                      <RefreshIcon fontSize="small" />
                    </IconButton>
                  )}
                </Stack>
              </Stack>
              <Divider />
              <Stack spacing={2} sx={{ flexGrow: 1, overflowY: "auto" }}>
                {session ? (
                  session.messages.map((message) => (
                    <MessageBubble
                      key={`${message.timestamp}-${message.role}-${message.content.slice(0, 8)}`}
                      role={message.role}
                      content={message.content}
                      timestamp={message.timestamp}
                    />
                  ))
                ) : (
                  <Alert severity="info">会話を開始するとここにメッセージが表示されます。</Alert>
                )}
              </Stack>
            </Stack>
          </Paper>

          <Paper variant="outlined" sx={{ p: 3 }}>
            <Stack spacing={2}>
              <Stack direction="row" justifyContent="space-between" alignItems="center">
                <Typography variant="h6" fontWeight={600}>
                  workflow.yaml プレビュー
                </Typography>
                <Button
                  variant="contained"
                  startIcon={<DownloadIcon />}
                  disabled={!session || !session.workflow_ready}
                  onClick={() => void handleDownload()}
                >
                  パッケージをダウンロード
                </Button>
              </Stack>
              <Divider />
              {workflow ? (
                <Paper variant="outlined" sx={{ p: 2, maxHeight: 400, overflow: "auto", bgcolor: "grey.50" }}>
                  <Typography component="pre" variant="body2" sx={{ m: 0, fontFamily: "monospace" }}>
                    {workflow}
                  </Typography>
                </Paper>
              ) : session ? (
                <Alert severity="info">workflow.yaml が生成されるとプレビューが表示されます。</Alert>
              ) : (
                <Alert severity="info">会話を開始して workflow.yaml を生成してください。</Alert>
              )}
            </Stack>
          </Paper>
        </Stack>
      </Container>
    </Box>
  );
}
