import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Container,
  Divider,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography
} from "@mui/material";

import dayjs from "dayjs";

import {
  downloadConversationPackage,
  fetchConversationPackage,
  fetchConversationStatus,
  fetchConversationWorkflow,
  fetchWorkflowDefinition,
  startConversation
} from "./api";
import { useWorkflowSession } from "./hooks/useWorkflowSession";
import type {
  ConversationMessage,
  GenerationJobStatus,
  JobStep,
  PackageMetadata,
  UIComponent,
  UIStep,
  WorkflowYaml
} from "./types";

function resolvePath(source: Record<string, unknown> | undefined, path: string | undefined) {
  if (!source || !path) return undefined;
  const normalizedPath = path.startsWith("view.") ? path.slice("view.".length) : path;
  const segments = normalizedPath.split(".");
  let current: unknown = source;
  for (const segment of segments) {
    if (typeof current !== "object" || current === null) return undefined;
    if (!(segment in current)) return undefined;
    current = (current as Record<string, unknown>)[segment];
  }
  return current;
}

function toBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = reader.result;
      if (typeof result === "string") {
        const base64 = result.split(",")[1] ?? result;
        resolve(base64);
      } else {
        reject(new Error("ファイルの読み込みに失敗しました"));
      }
    };
    reader.onerror = () => reject(reader.error ?? new Error("ファイルの読み込みに失敗しました"));
    reader.readAsDataURL(file);
  });
}

export default function App() {
  const [workflow, setWorkflow] = useState<WorkflowYaml | null>(null);
  const [workflowError, setWorkflowError] = useState<string | null>(null);
  const [loadingWorkflow, setLoadingWorkflow] = useState(true);
  const [activeStepIndex, setActiveStepIndex] = useState(0);
  const [formValues, setFormValues] = useState<Record<string, unknown>>({});
  const [prompt, setPrompt] = useState("");
  const [conversationSessionId, setConversationSessionId] = useState<string | null>(null);
  const [conversationStatus, setConversationStatus] = useState<GenerationJobStatus | null>(null);
  const [conversationMessages, setConversationMessages] = useState<ConversationMessage[]>([]);
  const [conversationSteps, setConversationSteps] = useState<JobStep[]>([]);
  const [workflowPreview, setWorkflowPreview] = useState<string | null>(null);
  const [packageInfo, setPackageInfo] = useState<PackageMetadata | null>(null);
  const [generationError, setGenerationError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [downloadingPackage, setDownloadingPackage] = useState(false);
  const [artifactsFetchedFor, setArtifactsFetchedFor] = useState<string | null>(null);
  const statusLabelMap: Record<GenerationJobStatus, string> = {
    received: "受付済み",
    spec_generating: "仕様生成中",
    templates_rendering: "テンプレート生成中",
    packaging: "パッケージング中",
    completed: "完了",
    failed: "失敗"
  };
  const statusColorMap: Record<GenerationJobStatus, "default" | "info" | "warning" | "success" | "error"> = {
    received: "default",
    spec_generating: "info",
    templates_rendering: "info",
    packaging: "warning",
    completed: "success",
    failed: "error"
  };
  const stepStatusLabel: Record<JobStep["status"], string> = {
    pending: "待機中",
    running: "実行中",
    completed: "完了",
    failed: "失敗"
  };
  const stepStatusColor: Record<JobStep["status"], "default" | "info" | "success" | "error"> = {
    pending: "default",
    running: "info",
    completed: "success",
    failed: "error"
  };

  const formatFileSize = useCallback((bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  }, []);

  const handleStartConversation = useCallback(async () => {
    const trimmed = prompt.trim();
    if (!trimmed) {
      setGenerationError("プロンプトを入力してください。");
      return;
    }
    setIsGenerating(true);
    setGenerationError(null);
    setConversationMessages([]);
    setConversationSteps([]);
    setWorkflowPreview(null);
    setPackageInfo(null);
    setArtifactsFetchedFor(null);
    setConversationSessionId(null);
    setConversationStatus(null);

    const timestamp = Date.now();
    const projectId = `project-${timestamp}`;
    const projectName = trimmed.slice(0, 30) || "生成アプリ";

    try {
      const response = await startConversation({
        user_id: "demo-user",
        project_id: projectId,
        project_name: projectName,
        prompt: trimmed,
        description: trimmed
      });
      setConversationSessionId(response.session_id);
      setConversationStatus(response.status);
      setConversationMessages(response.messages);
    } catch (error) {
      console.error("Failed to start conversation", error);
      setGenerationError("生成セッションの作成に失敗しました。");
    } finally {
      setIsGenerating(false);
    }
  }, [prompt]);

  const handleDownloadPackage = useCallback(async () => {
    if (!conversationSessionId) return;
    setDownloadingPackage(true);
    try {
      const data = await downloadConversationPackage(conversationSessionId);
      const blob = new Blob([data], { type: "application/zip" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = packageInfo?.filename ?? "app.zip";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error("Failed to download package", error);
      setGenerationError("パッケージのダウンロードに失敗しました。");
    } finally {
      setDownloadingPackage(false);
    }
  }, [conversationSessionId, packageInfo?.filename]);

  const { session, sessionId, loading: sessionLoading, error: sessionError, initialize, execute } = useWorkflowSession();

  useEffect(() => {
    let cancelled = false;
    setLoadingWorkflow(true);
    fetchWorkflowDefinition()
      .then((definition) => {
        if (cancelled) return;
        setWorkflow(definition);
        setWorkflowError(null);
      })
      .catch((error) => {
        console.error("Failed to load workflow definition", error);
        setWorkflowError("workflow.yaml の読み込みに失敗しました。バックエンドを確認してください。");
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingWorkflow(false);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!workflow) return;
    void initialize();
  }, [workflow, initialize]);

  useEffect(() => {
    if (!conversationSessionId) return;

    let cancelled = false;

    const refreshStatus = async () => {
      try {
        const status = await fetchConversationStatus(conversationSessionId);
        if (cancelled) return;
        setConversationStatus(status.status);
        setConversationMessages(status.messages);
        setConversationSteps(status.steps);

        if (status.status === "completed" && artifactsFetchedFor !== conversationSessionId) {
          try {
            const [workflowContent, packageMeta] = await Promise.all([
              fetchConversationWorkflow(conversationSessionId),
              fetchConversationPackage(conversationSessionId).catch(() => null)
            ]);
            if (cancelled) return;
            setWorkflowPreview(workflowContent);
            setPackageInfo(packageMeta ?? null);
            setArtifactsFetchedFor(conversationSessionId);
          } catch (error) {
            console.error("Failed to fetch generated artifacts", error);
            if (!cancelled) {
              setGenerationError("生成物の取得に失敗しました。");
            }
          }
        }

        if (status.status === "failed") {
          const lastMessage = status.messages[status.messages.length - 1];
          if (lastMessage?.role === "assistant") {
            setGenerationError(lastMessage.content);
          }
        }
      } catch (error) {
        console.error("Failed to fetch conversation status", error);
      }
    };

    void refreshStatus();

    if (conversationStatus === "completed" || conversationStatus === "failed") {
      return () => {
        cancelled = true;
      };
    }

    const timer = window.setInterval(() => {
      void refreshStatus();
    }, 2500);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [conversationSessionId, conversationStatus, artifactsFetchedFor]);

  const steps = useMemo(() => workflow?.ui?.steps ?? [], [workflow]);
  const activeStep = steps[activeStepIndex];

  useEffect(() => {
    if (!session) return;
    setFormValues({});
    setActiveStepIndex(0);
  }, [session?.session_id]);

  const handleFileChange = async (componentId: string, fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) {
      setFormValues((prev) => {
        const next = { ...prev };
        delete next[componentId];
        return next;
      });
      return;
    }
    const file = fileList[0];
    const content = await toBase64(file);
    setFormValues((prev) => ({
      ...prev,
      [componentId]: {
        name: file.name,
        content_type: file.type,
        content
      }
    }));
  };

  const handleSubmitStep = async (step: UIStep) => {
    if (!sessionId) {
      console.warn("Session not ready");
      return;
    }
    const inputs: Record<string, unknown> = {};
    step.components.forEach((component) => {
      if (formValues[component.id] !== undefined) {
        inputs[component.id] = formValues[component.id];
      }
    });
    try {
      const result = await execute({ step_id: step.id, inputs });
      if (result) {
        const nextIndex = Math.min(activeStepIndex + 1, Math.max(steps.length - 1, 0));
        setActiveStepIndex(nextIndex);
      }
    } catch (error) {
      console.error("Failed to execute workflow", error);
    }
  };

  const renderComponent = (component: UIComponent) => {
    const props = component.props ?? {};
    switch (component.type) {
      case "file_upload": {
        const accept = Array.isArray(props.accept) ? props.accept.join(",") : undefined;
        const value = formValues[component.id];
        const fileInfo = typeof value === "object" && value !== null ? (value as { name?: string }) : null;
        return (
          <Stack spacing={1} key={component.id}>
            {typeof props.label === "string" && (
              <Typography variant="subtitle1" fontWeight={600}>
                {props.label}
              </Typography>
            )}
            <Button variant="outlined" component="label">
              ファイルを選択
              <input
                type="file"
                hidden
                accept={accept}
                onChange={(event) => void handleFileChange(component.id, event.target.files)}
              />
            </Button>
            {fileInfo && (
              <Typography variant="body2" color="text.secondary">
                {fileInfo.name ?? "ファイルが選択されました"}
              </Typography>
            )}
          </Stack>
        );
      }
      case "button": {
        const action = props.action ?? "submit";
        const label = typeof props.label === "string" ? props.label : "実行";
        return (
          <Button
            key={component.id}
            variant="contained"
            size="large"
            disabled={sessionLoading}
            onClick={() => {
              if (action === "submit" && activeStep) {
                void handleSubmitStep(activeStep);
              }
            }}
          >
            {sessionLoading ? <CircularProgress size={20} color="inherit" /> : label}
          </Button>
        );
      }
      case "alert": {
        const severity = typeof props.severity === "string" ? (props.severity as any) : "info";
        const message = typeof props.message === "string" ? props.message : "";
        return (
          <Alert key={component.id} severity={severity} sx={{ whiteSpace: "pre-wrap" }}>
            {message}
          </Alert>
        );
      }
      case "table": {
        const dataPath = typeof props.data_path === "string" ? props.data_path : undefined;
        const resolved = resolvePath(session?.view as Record<string, unknown>, dataPath);
        const rows = Array.isArray(resolved)
          ? (resolved as Array<Record<string, unknown>>)
          : [];
        const columns = Array.isArray(props.columns) ? (props.columns as Array<Record<string, unknown>>) : [];
        return (
          <Box key={component.id}>
            {typeof props.title === "string" && (
              <Typography variant="h6" gutterBottom>
                {props.title}
              </Typography>
            )}
            <Table size="small">
              <TableHead>
                <TableRow>
                  {columns.map((column) => (
                    <TableCell key={String(column.field)}>{String(column.label ?? column.field)}</TableCell>
                  ))}
                </TableRow>
              </TableHead>
              <TableBody>
                {rows.map((row, rowIndex) => (
                  <TableRow key={`${component.id}-${rowIndex}`}>
                    {columns.map((column) => (
                      <TableCell key={String(column.field)}>
                        {String(row[column.field as string] ?? "-")}
                      </TableCell>
                    ))}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        );
      }
      default:
        return (
          <Alert key={component.id} severity="warning">
            未対応のコンポーネントタイプ: {component.type}
          </Alert>
        );
    }
  };

  const header = (
    <Stack spacing={1}>
      <Typography variant="h4" fontWeight={700}>
        {workflow?.info.name ?? "ワークフローデモ"}
      </Typography>
      {workflow?.info.description && (
        <Typography variant="subtitle1" color="text.secondary">
          {workflow.info.description}
        </Typography>
      )}
    </Stack>
  );

  if (loadingWorkflow) {
    return (
      <Box sx={{ display: "flex", minHeight: "100vh", alignItems: "center", justifyContent: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (workflowError) {
    return (
      <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
        <Container maxWidth="md">
          <Stack spacing={3}>
            {header}
            <Alert severity="error">{workflowError}</Alert>
          </Stack>
        </Container>
      </Box>
    );
  }

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="md">
        <Stack spacing={3}>
          <Paper variant="outlined" sx={{ p: 3 }}>
            <Stack spacing={2}>
              <Typography variant="h5" fontWeight={600}>
                アプリ生成チャット
              </Typography>
              <Typography variant="body2" color="text.secondary">
                自然言語で要件を入力すると、workflow.yaml と Docker パッケージを生成します。
              </Typography>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="stretch">
                <TextField
                  fullWidth
                  multiline
                  minRows={2}
                  label="アプリの要件"
                  placeholder="請求書からデータを抽出するアプリを作って"
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                />
                <Button
                  variant="contained"
                  color="primary"
                  disabled={isGenerating}
                  sx={{ minWidth: { sm: 140 }, alignSelf: { xs: "stretch", sm: "flex-end" } }}
                  onClick={() => void handleStartConversation()}
                >
                  {isGenerating ? <CircularProgress size={20} color="inherit" /> : "送信"}
                </Button>
              </Stack>
              {generationError && <Alert severity="error">{generationError}</Alert>}
              {conversationStatus && (
                <Chip
                  label={`ステータス: ${statusLabelMap[conversationStatus]}`}
                  color={statusColorMap[conversationStatus]}
                  sx={{ alignSelf: "flex-start" }}
                />
              )}
              {conversationMessages.length > 0 && (
                <Stack spacing={1}>
                  {conversationMessages.map((message, index) => (
                    <Box
                      key={`${message.timestamp}-${index}`}
                      sx={{
                        p: 1.5,
                        borderRadius: 1,
                        bgcolor:
                          message.role === "user"
                            ? "primary.50"
                            : message.role === "assistant"
                            ? "success.50"
                            : "grey.100"
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {message.role === "user" ? "ユーザー" : message.role === "assistant" ? "アシスタント" : "システム"}
                        {" ・ "}
                        {dayjs(message.timestamp).format("HH:mm:ss")}
                      </Typography>
                      <Typography variant="body2" sx={{ whiteSpace: "pre-wrap" }}>
                        {message.content}
                      </Typography>
                    </Box>
                  ))}
                </Stack>
              )}
              {conversationSteps.length > 0 && (
                <Box>
                  <Divider sx={{ my: 2 }} />
                  <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                    処理ステップ
                  </Typography>
                  <List dense disablePadding>
                    {conversationSteps.map((step) => (
                      <ListItem
                        key={step.id}
                        disableGutters
                        secondaryAction={
                          <Chip size="small" label={stepStatusLabel[step.status]} color={stepStatusColor[step.status]} />
                        }
                      >
                        <ListItemText
                          primary={step.label}
                          secondary={step.message ?? undefined}
                          primaryTypographyProps={{ variant: "body2" }}
                          secondaryTypographyProps={{ variant: "caption", sx: { whiteSpace: "pre-wrap" } }}
                        />
                      </ListItem>
                    ))}
                  </List>
                </Box>
              )}
              {workflowPreview && (
                <Paper variant="outlined" sx={{ p: 2, bgcolor: "grey.50" }}>
                  <Typography variant="subtitle2" gutterBottom>
                    生成された workflow.yaml プレビュー
                  </Typography>
                  <Box component="pre" sx={{ maxHeight: 280, overflow: "auto", fontSize: 13, m: 0 }}>
                    {workflowPreview}
                  </Box>
                </Paper>
              )}
              {packageInfo && (
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2} alignItems="center">
                  <Typography variant="body2" color="text.secondary" sx={{ flexGrow: 1 }}>
                    パッケージ: {packageInfo.filename}（{formatFileSize(packageInfo.size_bytes)}）
                  </Typography>
                  <Button
                    variant="contained"
                    color="secondary"
                    disabled={downloadingPackage}
                    onClick={() => void handleDownloadPackage()}
                  >
                    {downloadingPackage ? <CircularProgress size={20} color="inherit" /> : "ダウンロード"}
                  </Button>
                </Stack>
              )}
            </Stack>
          </Paper>

          {header}
          {sessionError && <Alert severity="error">{sessionError}</Alert>}
          {session?.error && <Alert severity="error">{session.error}</Alert>}

          {steps.length > 0 && (
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Stepper activeStep={activeStepIndex} alternativeLabel>
                {steps.map((step) => (
                  <Step key={step.id}>
                    <StepLabel>{step.title}</StepLabel>
                  </Step>
                ))}
              </Stepper>
            </Paper>
          )}

          {activeStep ? (
            <Paper variant="outlined" sx={{ p: 4 }}>
              <Stack spacing={3}>
                <Box>
                  <Typography variant="h5" fontWeight={600} gutterBottom>
                    {activeStep.title}
                  </Typography>
                  {activeStep.description && (
                    <Typography variant="body1" color="text.secondary">
                      {activeStep.description}
                    </Typography>
                  )}
                </Box>
                <Stack spacing={3}>{activeStep.components.map(renderComponent)}</Stack>
                {activeStepIndex > 0 && (
                  <Button variant="outlined" onClick={() => setActiveStepIndex(Math.max(activeStepIndex - 1, 0))}>
                    戻る
                  </Button>
                )}
              </Stack>
            </Paper>
          ) : (
            <Alert severity="info">workflow.yaml に UI ステップが定義されていません。</Alert>
          )}

          {session && (
            <Paper variant="outlined" sx={{ p: 3 }}>
              <Typography variant="subtitle2" color="text.secondary" gutterBottom>
                セッション情報
              </Typography>
              <Stack spacing={1}>
                <Typography variant="body2">セッションID: {session.session_id}</Typography>
                <Typography variant="body2">ステータス: {session.status}</Typography>
              </Stack>
            </Paper>
          )}
        </Stack>
      </Container>
    </Box>
  );
}
