import { useCallback, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
  Divider,
  IconButton,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import RefreshIcon from "@mui/icons-material/Refresh";

import { createConversation, downloadPackage, fetchConversation, fetchWorkflowYaml } from "./api";
import type { ConversationMessage, ConversationStatus } from "./types";

interface ConversationState {
  sessionId: string;
  status: ConversationStatus;
  messages: ConversationMessage[];
  workflowReady: boolean;
}

function MessageBubble({ message }: { message: ConversationMessage }) {
  const isUser = message.role === "user";
  return (
    <Stack
      alignItems={isUser ? "flex-end" : "flex-start"}
      sx={{
        width: "100%"
      }}
    >
      <Paper
        elevation={0}
        sx={{
          px: 2,
          py: 1.5,
          bgcolor: isUser ? "primary.main" : "grey.100",
          color: isUser ? "primary.contrastText" : "text.primary",
          maxWidth: "80%",
          whiteSpace: "pre-wrap"
        }}
      >
        {message.content}
      </Paper>
    </Stack>
  );
}

export default function App() {
  const [prompt, setPrompt] = useState("");
  const [conversation, setConversation] = useState<ConversationState | null>(null);
  const [workflowYaml, setWorkflowYaml] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!prompt.trim()) {
      setError("プロンプトを入力してください。");
      return;
    }
    setError(null);
    setLoading(true);
    try {
      const response = await createConversation({ prompt });
      const nextState: ConversationState = {
        sessionId: response.session_id,
        status: response.status,
        messages: response.messages,
        workflowReady: response.workflow_ready
      };
      setConversation(nextState);
      if (response.workflow_ready) {
        const yaml = await fetchWorkflowYaml(response.session_id);
        setWorkflowYaml(yaml);
      } else {
        setWorkflowYaml("");
      }
    } catch (err) {
      console.error("Failed to create conversation", err);
      setError("ワークフローの生成に失敗しました。バックエンドのログを確認してください。");
    } finally {
      setLoading(false);
    }
  }, [prompt]);

  const handleRefreshStatus = useCallback(async () => {
    if (!conversation) return;
    try {
      const status = await fetchConversation(conversation.sessionId);
      const nextState: ConversationState = {
        sessionId: status.session_id,
        status: status.status,
        messages: status.messages,
        workflowReady: status.workflow_ready
      };
      setConversation(nextState);
      if (status.workflow_ready) {
        const yaml = await fetchWorkflowYaml(status.session_id);
        setWorkflowYaml(yaml);
      }
    } catch (err) {
      console.error("Failed to refresh conversation", err);
      setError("セッション状態の取得に失敗しました。");
    }
  }, [conversation]);

  const handleDownload = useCallback(async () => {
    if (!conversation) return;
    setDownloading(true);
    try {
      const blob = await downloadPackage(conversation.sessionId);
      const url = window.URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "workflow-package.zip";
      anchor.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download package", err);
      setError("パッケージのダウンロードに失敗しました。");
    } finally {
      setDownloading(false);
    }
  }, [conversation]);

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="md">
        <Stack spacing={4}>
          <Stack spacing={1}>
            <Typography variant="h4" fontWeight={700}>
              LLM ワークフロー生成デモ
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              自然言語のプロンプトから workflow.yaml を生成し、即座にプレビューとパッケージングが行えます。
            </Typography>
          </Stack>

          <Paper variant="outlined" sx={{ p: 3 }}>
            <Stack spacing={2}>
              <TextField
                label="アプリの要件を入力"
                placeholder="請求書からデータを抽出するアプリを作って"
                multiline
                minRows={3}
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                disabled={loading}
              />
              <Stack direction="row" spacing={2} justifyContent="flex-end">
                {conversation && (
                  <IconButton onClick={() => void handleRefreshStatus()} disabled={loading} color="primary">
                    <RefreshIcon />
                  </IconButton>
                )}
                <Button
                  variant="contained"
                  size="large"
                  onClick={() => void handleSubmit()}
                  disabled={loading}
                >
                  {loading ? <CircularProgress size={20} color="inherit" /> : "workflow.yaml を生成"}
                </Button>
              </Stack>
              {error && <Alert severity="error">{error}</Alert>}
            </Stack>
          </Paper>

          {conversation && (
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Stack spacing={2}>
                <Stack direction="row" alignItems="center" justifyContent="space-between">
                  <Typography variant="h6">対話履歴</Typography>
                  <Typography variant="body2" color="text.secondary">
                    セッションID: {conversation.sessionId}
                  </Typography>
                </Stack>
                <Stack spacing={2}>
                  {conversation.messages.map((message, index) => (
                    <MessageBubble key={`${message.role}-${index}`} message={message} />
                  ))}
                </Stack>
                <Divider />
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="body2" color="text.secondary">
                    ステータス: {conversation.status}
                  </Typography>
                  {conversation.workflowReady && (
                    <Alert severity="success" sx={{ ml: 2, py: 0.5 }}>
                      workflow.yaml をダウンロードできます
                    </Alert>
                  )}
                </Stack>
              </Stack>
            </Paper>
          )}

          {workflowYaml && (
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Stack spacing={2}>
                <Stack direction="row" alignItems="center" justifyContent="space-between">
                  <Typography variant="h6">生成された workflow.yaml プレビュー</Typography>
                  <Button
                    variant="contained"
                    startIcon={<DownloadIcon />}
                    onClick={() => void handleDownload()}
                    disabled={downloading}
                  >
                    {downloading ? "準備中..." : "パッケージをダウンロード"}
                  </Button>
                </Stack>
                <Paper
                  variant="outlined"
                  sx={{ p: 2, bgcolor: "grey.100", maxHeight: 360, overflow: "auto", fontFamily: "monospace" }}
                >
                  <Typography component="pre" sx={{ m: 0, whiteSpace: "pre" }}>
                    {workflowYaml}
                  </Typography>
                </Paper>
              </Stack>
            </Paper>
          )}
        </Stack>
      </Container>
    </Box>
  );
}
