import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Container,
  LinearProgress,
  Paper,
  Stack,
  TextField,
  Typography
} from "@mui/material";

import { createPackage, fetchFeaturesConfig, generateWorkflow } from "./api";
import type {
  AgentMessage,
  FeaturesConfig,
  PackageDescriptor,
  WorkflowGenerationRequest,
  WorkflowGenerationResponse
} from "./types";
import { logger } from "./utils/logger";

export default function App() {
  const [features, setFeatures] = useState<FeaturesConfig | null>(null);
  const [prompt, setPrompt] = useState("請求書の検証を自動化したい。PDFをアップロードして内容を確認し、異常値があればフラグを立ててほしい。");
  const [appName, setAppName] = useState("Invoice Validation Assistant");
  const [loading, setLoading] = useState(false);
  const [generation, setGeneration] = useState<WorkflowGenerationResponse | null>(null);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [packageInfo, setPackageInfo] = useState<PackageDescriptor | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    fetchFeaturesConfig()
      .then((config) => setFeatures(config))
      .catch((err) => logger.warn("機能設定の取得に失敗", err));
  }, []);

  const handleGenerate = async () => {
    setLoading(true);
    setError(null);
    setPackageInfo(null);

    const payload: WorkflowGenerationRequest = {
      prompt,
      app_name: appName || undefined,
      force_mock: features?.default_mock ?? true
    };

    try {
      const response = await generateWorkflow(payload);
      setGeneration(response);
      setMessages(response.messages);
      logger.info("workflow.yaml を生成しました", response.workflow.info.name);
    } catch (err) {
      logger.error("workflow.yaml の生成に失敗", err);
      setError("workflow.yaml の生成に失敗しました。入力内容を確認して再試行してください。");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!generation) return;
    setDownloading(true);
    setError(null);
    try {
      const response = await createPackage({
        workflow_yaml: generation.workflow_yaml,
        app_name: generation.workflow.info.name,
        include_mock_server: true,
        environment_variables: {}
      });
      setPackageInfo(response.package);
      window.location.href = response.package.download_url;
    } catch (err) {
      logger.error("パッケージ作成に失敗", err);
      setError("パッケージの生成に失敗しました。時間をおいて再試行してください。");
    } finally {
      setDownloading(false);
    }
  };

  const hasResult = Boolean(generation);

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="lg">
        <Stack spacing={4}>
          <Stack spacing={1}>
            <Typography variant="h4" fontWeight={700}>
              宣言的アプリ生成コンソール
            </Typography>
            <Typography color="text.secondary">
              自然言語の要求から multi-agent が `workflow.yaml` を生成し、汎用実行エンジン向けのパッケージをダウンロードできます。
            </Typography>
          </Stack>

          <Paper variant="outlined" sx={{ p: 4 }}>
            <Stack spacing={3}>
              <TextField
                label="アプリ名"
                value={appName}
                onChange={(event) => setAppName(event.target.value)}
                placeholder="例: Invoice Validation Assistant"
                fullWidth
              />

              <TextField
                label="要件プロンプト"
                value={prompt}
                onChange={(event) => setPrompt(event.target.value)}
                minRows={4}
                multiline
                placeholder="アプリに実装したい要件を日本語または英語で入力してください"
              />

              <Stack direction="row" alignItems="center" spacing={2}>
                <Button variant="contained" size="large" onClick={handleGenerate} disabled={loading}>
                  workflow.yaml を生成
                </Button>
                {loading && <LinearProgress sx={{ flexGrow: 1, maxWidth: 200 }} />}
              </Stack>

              {features && (
                <Typography variant="body2" color="text.secondary">
                  デフォルトモード: {features.default_mock ? "モック" : "LLM"}
                </Typography>
              )}

              {error && <Alert severity="error">{error}</Alert>}
            </Stack>
          </Paper>

          {hasResult && generation && (
            <Stack spacing={3}>
              <Paper variant="outlined" sx={{ p: 4 }}>
                <Stack spacing={2}>
                  <Typography variant="h6">エージェント実行ログ</Typography>
                  <AgentTimeline messages={messages} />
                </Stack>
              </Paper>

              <Paper variant="outlined" sx={{ p: 4 }}>
                <Stack spacing={3}>
                  <Stack direction="row" justifyContent="space-between" alignItems="center">
                    <Typography variant="h6">workflow.yaml プレビュー</Typography>
                    <Chip label={`生成時間 ${generation.duration_ms}ms`} color="primary" variant="outlined" />
                  </Stack>
                  <Paper variant="outlined" sx={{ p: 2, bgcolor: "#0c0c0c" }}>
                    <pre style={{ margin: 0, color: "#e8f5e9", overflowX: "auto" }}>{generation.workflow_yaml}</pre>
                  </Paper>
                  <Stack direction="row" spacing={2}>
                    <Button
                      variant="contained"
                      onClick={handleDownload}
                      disabled={downloading}
                    >
                      パッケージをダウンロード
                    </Button>
                    {downloading && <LinearProgress sx={{ flexGrow: 1, maxWidth: 200 }} />}
                  </Stack>
                  {packageInfo && (
                    <Alert severity="success">
                      パッケージを準備しました。自動的にダウンロードが開始されない場合は
                      <a href={packageInfo.download_url} style={{ marginLeft: 4 }}>
                        こちら
                      </a>
                      をクリックしてください。
                    </Alert>
                  )}
                </Stack>
              </Paper>
            </Stack>
          )}
        </Stack>
      </Container>
    </Box>
  );
}

function AgentTimeline({ messages }: { messages: AgentMessage[] }) {
  if (messages.length === 0) {
    return <Typography color="text.secondary">まだ実行ログはありません。</Typography>;
  }

  return (
    <Stack spacing={2}>
      {messages.map((message, index) => (
        <Paper variant="outlined" sx={{ p: 2 }} key={`${message.role}-${index}`}>
          <Stack spacing={1}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip
                size="small"
                color={message.success !== false ? "primary" : "error"}
                label={roleLabel(message.role)}
              />
              <Typography variant="subtitle1" fontWeight={600}>
                {message.title}
              </Typography>
            </Stack>
            <Typography whiteSpace="pre-line">{message.content}</Typography>
            {message.metadata && (
              <MetadataBlock metadata={message.metadata} />
            )}
          </Stack>
        </Paper>
      ))}
    </Stack>
  );
}

function MetadataBlock({ metadata }: { metadata: Record<string, unknown> }) {
  const entries = Object.entries(metadata);
  if (!entries.length) return null;

  return (
    <Paper variant="outlined" sx={{ p: 1.5, bgcolor: "#fafafa" }}>
      <Stack spacing={1}>
        {entries.map(([key, value]) => (
          <Stack key={key} spacing={0.5}>
            <Typography variant="caption" color="text.secondary">
              {key}
            </Typography>
            <Typography variant="body2" whiteSpace="pre-line">
              {formatMetadataValue(value)}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  );
}

function formatMetadataValue(value: unknown): string {
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  if (typeof value === "object" && value !== null) {
    return JSON.stringify(value, null, 2);
  }
  return String(value ?? "");
}

function roleLabel(role: AgentMessage["role"]) {
  switch (role) {
    case "analyst":
      return "Analyst";
    case "architect":
      return "Architect";
    case "specialist":
      return "Specialist";
    case "validator":
      return "Validator";
    default:
      return role;
  }
}

