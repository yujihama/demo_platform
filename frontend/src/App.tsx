import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  Container,
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
  Typography
} from "@mui/material";

import {
  createWorkflowSession,
  executeWorkflow,
  fetchWorkflowDefinition,
  fetchWorkflowSession,
  uploadWorkflowInput
} from "./api";
import type { SessionState, UIComponent, UIStep, WorkflowYaml } from "./types";
import { resolvePath } from "./utils/path";
import { logger } from "./utils/logger";

const SESSION_STORAGE_KEY = "workflow_session_id";

export default function App() {
  const [workflow, setWorkflow] = useState<WorkflowYaml | null>(null);
  const [session, setSession] = useState<SessionState | null>(null);
  const [activeStep, setActiveStep] = useState(0);
  const [initialising, setInitialising] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [uploading, setUploading] = useState<Record<string, boolean>>({});

  useEffect(() => {
    let cancelled = false;
    const initialise = async () => {
      try {
        const loadedWorkflow = await fetchWorkflowDefinition();
        if (cancelled) return;
        setWorkflow(loadedWorkflow);

        let sessionId = localStorage.getItem(SESSION_STORAGE_KEY);
        let sessionState: SessionState | null = null;

        if (sessionId) {
          try {
            sessionState = await fetchWorkflowSession(sessionId);
          } catch (fetchError) {
            logger.warn("Failed to load existing session, creating new one", fetchError);
            sessionState = null;
          }
        }

        if (!sessionState) {
          sessionState = await createWorkflowSession();
          sessionId = sessionState.session_id;
          localStorage.setItem(SESSION_STORAGE_KEY, sessionId);
        }

        if (cancelled) return;
        setSession(sessionState);
        setActiveStep(0);
      } catch (initialError) {
        logger.error("Initialisation failed", initialError);
        if (!cancelled) {
          setError("初期化に失敗しました。バックエンドが起動しているか確認してください。");
        }
      } finally {
        if (!cancelled) {
          setInitialising(false);
        }
      }
    };

    void initialise();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!workflow || !session) return;
    const steps = workflow.ui?.steps ?? [];
    let highestUnlocked = 0;
    steps.forEach((step, index) => {
      if (isStepUnlocked(step, session)) {
        highestUnlocked = index;
      }
    });
    setActiveStep((prev) => Math.min(Math.max(prev, highestUnlocked), Math.max(steps.length - 1, 0)));
  }, [workflow, session]);

  const handleFileUpload = async (component: UIComponent) => {
    if (!session) return;
    const stepId = component.props.pipeline_step as string | undefined;
    if (!stepId) {
      setError("ファイルアップロード用のpipeline_stepが未設定です。");
      return;
    }
    const inputElement = document.createElement("input");
    inputElement.type = "file";
    if (Array.isArray(component.props.accept)) {
      inputElement.accept = (component.props.accept as string[]).join(",");
    }

    inputElement.onchange = async () => {
      const files = inputElement.files;
      if (!files || files.length === 0) return;
      const file = files[0];
      setUploading((prev) => ({ ...prev, [stepId]: true }));
      setError(null);
      try {
        const updated = await uploadWorkflowInput(session.session_id, stepId, file);
        setSession(updated);
        logger.info("Uploaded file for step %s", stepId);
      } catch (uploadError) {
        logger.error("Failed to upload file", uploadError);
        setError("ファイルのアップロードに失敗しました。");
      } finally {
        setUploading((prev) => ({ ...prev, [stepId]: false }));
      }
    };

    inputElement.click();
  };

  const handleExecute = async (component: UIComponent) => {
    if (!session) return;
    setError(null);
    setActionLoading(true);
    try {
      const updated = await executeWorkflow(session.session_id);
      setSession(updated);
      const nextStepId = component.props.next_step as string | undefined;
      if (nextStepId && workflow?.ui?.steps) {
        const nextIndex = workflow.ui.steps.findIndex((step) => step.id === nextStepId);
        if (nextIndex >= 0) {
          setActiveStep(nextIndex);
        }
      }
      logger.info("Pipeline executed successfully");
    } catch (execError) {
      logger.error("Pipeline execution failed", execError);
      setError("ワークフローの実行に失敗しました。入力内容を確認してください。");
    } finally {
      setActionLoading(false);
    }
  };

  const steps = useMemo(() => workflow?.ui?.steps ?? [], [workflow]);
  const currentStep = steps[activeStep];

  const handleResetSession = async () => {
    setActionLoading(true);
    setError(null);
    try {
      const newSession = await createWorkflowSession();
      localStorage.setItem(SESSION_STORAGE_KEY, newSession.session_id);
      setSession(newSession);
      setUploading({});
      setActiveStep(0);
      logger.info("Created new workflow session");
    } catch (resetError) {
      logger.error("Failed to create new session", resetError);
      setError("新しいセッションの作成に失敗しました。");
    } finally {
      setActionLoading(false);
    }
  };

  if (initialising) {
    return (
      <Container maxWidth="md" sx={{ py: 8 }}>
        <Stack spacing={3} alignItems="center">
          <CircularProgress />
          <Typography>起動中です...</Typography>
        </Stack>
      </Container>
    );
  }

  if (!workflow || !session) {
    return (
      <Container maxWidth="md" sx={{ py: 8 }}>
        <Alert severity="error">設定の読み込みに失敗しました。リロードしてください。</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="md" sx={{ py: 6 }}>
      <Stack spacing={4}>
        <Box>
          <Typography variant="h4" gutterBottom>
            {workflow.info.name}
          </Typography>
          <Typography color="text.secondary">{workflow.info.description}</Typography>
          <Button sx={{ mt: 2 }} variant="outlined" onClick={handleResetSession} disabled={actionLoading}>
            {actionLoading ? "再生成中..." : "新しいセッションを開始"}
          </Button>
        </Box>

        {error && <Alert severity="error">{error}</Alert>}

        <Paper elevation={2} sx={{ p: 3 }}>
          <Stepper activeStep={activeStep} alternativeLabel>
            {steps.map((step, index) => {
              const unlocked = isStepUnlocked(step, session);
              return (
                <Step key={step.id} completed={isStepCompleted(step, session)}>
                  <StepLabel
                    onClick={() => {
                      if (unlocked) {
                        setActiveStep(index);
                      }
                    }}
                    sx={{ cursor: unlocked ? "pointer" : "default" }}
                  >
                    {step.title}
                  </StepLabel>
                </Step>
              );
            })}
          </Stepper>
        </Paper>

        {currentStep ? (
          <Paper elevation={3} sx={{ p: 4 }}>
            <Stack spacing={3}>
              <Box>
                <Typography variant="h5" gutterBottom>
                  {currentStep.title}
                </Typography>
                {currentStep.description && (
                  <Typography color="text.secondary">{currentStep.description}</Typography>
                )}
              </Box>

              {currentStep.components.map((component) => (
                <Box key={component.id}>{renderComponent(component, session, handleFileUpload, handleExecute, uploading, actionLoading)}</Box>
              ))}
            </Stack>
          </Paper>
        ) : (
          <Paper elevation={3} sx={{ p: 4 }}>
            <Typography>利用可能なステップが定義されていません。</Typography>
          </Paper>
        )}
      </Stack>
    </Container>
  );
}

function isStepUnlocked(step: UIStep, session: SessionState) {
  const requirements = (step.props?.required_steps as string[] | undefined) ?? [];
  if (requirements.length === 0) return true;
  return requirements.every((requirement) => session.steps[requirement]?.status === "completed");
}

function isStepCompleted(step: UIStep, session: SessionState) {
  const requirements = (step.props?.required_steps as string[] | undefined) ?? [];
  if (requirements.length === 0) return false;
  return requirements.every((requirement) => session.steps[requirement]?.status === "completed");
}

function renderComponent(
  component: UIComponent,
  session: SessionState,
  onUpload: (component: UIComponent) => void,
  onExecute: (component: UIComponent) => void,
  uploading: Record<string, boolean>,
  actionLoading: boolean
) {
  const props = component.props as Record<string, unknown>;
  switch (component.type) {
    case "file_upload": {
      const pipelineStep = props.pipeline_step as string | undefined;
      const state = pipelineStep ? session.steps[pipelineStep] : undefined;
      const isUploading = pipelineStep ? uploading[pipelineStep] : false;
      const label = typeof props.label === "string" ? props.label : "ファイルをアップロード";
      const description = typeof props.description === "string" ? props.description : undefined;
      const uploadedInfo =
        state?.output && typeof state.output === "object" && state.output !== null
          ? (state.output as Record<string, unknown>)
          : null;
      return (
        <Stack spacing={1}>
          <Typography>{label}</Typography>
          {description && (
            <Typography color="text.secondary" variant="body2">
              {description}
            </Typography>
          )}
          <Button variant="contained" onClick={() => onUpload(component)} disabled={isUploading}>
            {isUploading ? "アップロード中..." : "ファイルを選択"}
          </Button>
          {uploadedInfo && (
            <Typography variant="body2" color="text.secondary">
              {typeof uploadedInfo.filename === "string" ? uploadedInfo.filename : "ファイル"} をアップロード済み
            </Typography>
          )}
        </Stack>
      );
    }
    case "button": {
      const action = props.action as string | undefined;
      const label = typeof props.label === "string" ? props.label : "実行";
      return (
        <Button
          variant="contained"
          onClick={() => onExecute(component)}
          disabled={actionLoading || action !== "execute_pipeline"}
        >
          {actionLoading ? "実行中..." : label}
        </Button>
      );
    }
    case "table": {
      const rows = resolvePath(session, props.data_path as string | undefined);
      const columns = (props.columns as { key: string; label: string }[] | undefined) ?? [];
      if (!Array.isArray(rows) || rows.length === 0) {
        return <Alert severity="info">表示できるデータがまだありません。</Alert>;
      }
      return (
        <Table size="small">
          <TableHead>
            <TableRow>
              {columns.map((column) => (
                <TableCell key={column.key}>{column.label}</TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, index) => (
              <TableRow key={index}>
                {columns.map((column) => (
                  <TableCell key={column.key}>{formatCellValue((row as Record<string, unknown>)[column.key])}</TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      );
    }
    case "alert": {
      const severity = (props.severity as "error" | "warning" | "info" | "success") ?? "info";
      const title = typeof props.title === "string" ? props.title : "";
      const bodyValue = resolvePath(session, props.body_path as string | undefined);
      return (
        <Alert severity={severity}>
          {title && <Typography fontWeight="bold">{title}</Typography>}
          {renderAlertBody(bodyValue)}
        </Alert>
      );
    }
    default:
      return <Alert severity="warning">未対応のコンポーネント: {component.type}</Alert>;
  }
}

function renderAlertBody(value: unknown) {
  if (value == null) {
    return <Typography variant="body2">データが未取得です。</Typography>;
  }
  if (typeof value === "object") {
    return (
      <Stack spacing={0.5} mt={1}>
        {Object.entries(value as Record<string, unknown>).map(([key, val]) => (
          <Typography variant="body2" key={key}>
            {key}: {String(val)}
          </Typography>
        ))}
      </Stack>
    );
  }
  return <Typography variant="body2">{String(value)}</Typography>;
}

function formatCellValue(value: unknown) {
  if (value == null) return "";
  if (typeof value === "number") return value.toLocaleString();
  return String(value);
}
