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

import { fetchWorkflowDefinition } from "./api";
import { useWorkflowSession } from "./hooks/useWorkflowSession";
import type { UIComponent, UIStep, WorkflowYaml } from "./types";

function resolvePath(source: Record<string, unknown> | undefined, path: string | undefined) {
  if (!source || !path) return undefined;
  const segments = path.split(".");
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
        return (
          <Stack spacing={1} key={component.id}>
            {props.label && (
              <Typography variant="subtitle1" fontWeight={600}>
                {String(props.label)}
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
            {formValues[component.id] && typeof formValues[component.id] === "object" && (
              <Typography variant="body2" color="text.secondary">
                {(formValues[component.id] as { name?: string }).name ?? "ファイルが選択されました"}
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
            {props.title && (
              <Typography variant="h6" gutterBottom>
                {String(props.title)}
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
