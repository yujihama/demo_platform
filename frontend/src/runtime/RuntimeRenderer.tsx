import { useEffect, useMemo, useState } from "react";
import type { ChangeEvent } from "react";
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Stack,
  Step,
  StepLabel,
  Stepper,
  Typography,
  Alert
} from "@mui/material";

import type { RuntimeSession, UIComponent, WorkflowYaml } from "../types";

interface RuntimeRendererProps {
  workflow: WorkflowYaml;
  session: RuntimeSession;
  onAdvance: () => Promise<void> | void;
  onUploadFile: (component: UIComponent, file: File) => Promise<void> | void;
  onUpdateValue: (component: UIComponent, value: unknown) => Promise<void> | void;
  processing: boolean;
  error?: string | null;
}

export function RuntimeRenderer({
  workflow,
  session,
  onAdvance,
  onUploadFile,
  onUpdateValue,
  processing,
  error
}: RuntimeRendererProps) {
  const steps = workflow.ui?.steps ?? [];
  const [activeStepId, setActiveStepId] = useState<string | null>(steps[0]?.id ?? null);

  useEffect(() => {
    if (session.active_step_id) {
      setActiveStepId(session.active_step_id);
    } else if (session.status === "completed" && steps.length > 0) {
      setActiveStepId(steps[steps.length - 1].id);
    }
  }, [session.active_step_id, session.status, steps]);

  const activeIndex = useMemo(() => {
    if (!activeStepId) return 0;
    const index = steps.findIndex((step) => step.id === activeStepId);
    return index >= 0 ? index : 0;
  }, [activeStepId, steps]);

  const waitingForSet = useMemo(() => new Set(session.waiting_for), [session.waiting_for]);

  return (
    <Stack spacing={3}>
      <Card variant="outlined">
        <CardContent>
          <Typography variant="h5" fontWeight={700} gutterBottom>
            {workflow.info.name}
          </Typography>
          <Typography variant="body1" color="text.secondary">
            {workflow.info.description}
          </Typography>
        </CardContent>
      </Card>

      {steps.length > 0 && (
        <Card variant="outlined">
          <CardContent>
            <Stepper activeStep={activeIndex} alternativeLabel>
              {steps.map((step) => (
                <Step key={step.id}>
                  <StepLabel>{step.title}</StepLabel>
                </Step>
              ))}
            </Stepper>
          </CardContent>
        </Card>
      )}

      {error && <Alert severity="error">{error}</Alert>}

      {steps.map((step, index) => (
        <Card key={step.id} variant="outlined" sx={{ borderColor: index === activeIndex ? "primary.main" : undefined }}>
          <CardContent>
            <Stack spacing={2}>
              <Box>
                <Typography variant="h6" gutterBottom>
                  {step.title}
                </Typography>
                {step.description && (
                  <Typography variant="body2" color="text.secondary">
                    {step.description}
                  </Typography>
                )}
              </Box>

              <Stack spacing={2}>
                {step.components.map((component) => (
                  <RuntimeComponent
                    key={component.id}
                    component={component}
                    session={session}
                    waiting={waitingForSet.has(component.id)}
                    onAdvance={onAdvance}
                    onUploadFile={onUploadFile}
                    onUpdateValue={onUpdateValue}
                    processing={processing && session.waiting_for.includes(component.id)}
                  />
                ))}
              </Stack>
            </Stack>
          </CardContent>
        </Card>
      ))}
    </Stack>
  );
}

interface RuntimeComponentProps {
  component: UIComponent;
  session: RuntimeSession;
  waiting: boolean;
  processing: boolean;
  onAdvance: () => Promise<void> | void;
  onUploadFile: (component: UIComponent, file: File) => Promise<void> | void;
  onUpdateValue: (component: UIComponent, value: unknown) => Promise<void> | void;
}

function RuntimeComponent({
  component,
  session,
  waiting,
  processing,
  onAdvance,
  onUploadFile,
  onUpdateValue
}: RuntimeComponentProps) {
  switch (component.type) {
    case "file_upload":
      return (
        <FileUploadField
          component={component}
          session={session}
          waiting={waiting}
          onUploadFile={onUploadFile}
        />
      );
    case "button":
      return (
        <RuntimeButton
          component={component}
          processing={processing}
          onAdvance={onAdvance}
          onUpdateValue={onUpdateValue}
        />
      );
    case "table":
      return <RuntimeTable component={component} session={session} />;
    default:
      return (
        <Alert severity="warning">未対応のコンポーネントタイプです: {component.type}</Alert>
      );
  }
}

function FileUploadField({
  component,
  session,
  waiting,
  onUploadFile
}: {
  component: UIComponent;
  session: RuntimeSession;
  waiting: boolean;
  onUploadFile: (component: UIComponent, file: File) => Promise<void> | void;
}) {
  const state = session.component_state[component.id];
  const props = component.props ?? {};
  const label = (props.label as string) ?? "ファイルを選択";
  const helperText = (props.helperText as string) ?? undefined;
  const filename = state?.value && typeof state.value === "object" && state.value !== null && "filename" in state.value ? (state.value as Record<string, unknown>).filename : null;

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (files && files.length > 0) {
      onUploadFile(component, files[0]);
    }
  };

  return (
    <Stack spacing={1}>
      <Button variant="outlined" component="label" disabled={session.status === "running" && !waiting}>
        {label}
        <input type="file" hidden onChange={handleChange} />
      </Button>
      {filename && <Typography variant="body2">選択中: {String(filename)}</Typography>}
      {waiting && (
        <Typography variant="body2" color="warning.main">
          入力待ちです。
        </Typography>
      )}
      {helperText && (
        <Typography variant="body2" color="text.secondary">
          {helperText}
        </Typography>
      )}
    </Stack>
  );
}

function RuntimeButton({
  component,
  processing,
  onAdvance,
  onUpdateValue
}: {
  component: UIComponent;
  processing: boolean;
  onAdvance: () => Promise<void> | void;
  onUpdateValue: (component: UIComponent, value: unknown) => Promise<void> | void;
}) {
  const props = component.props ?? {};
  const label = (props.label as string) ?? "実行";
  const variant = (props.variant as "text" | "outlined" | "contained") ?? "contained";
  const action = (props.action as string) ?? "advance";

  const handleClick = () => {
    if (action === "advance") {
      onAdvance();
    } else {
      onUpdateValue(component, { action });
    }
  };

  return (
    <Button variant={variant} onClick={handleClick} disabled={processing}>
      {processing ? <CircularProgress size={18} color="inherit" /> : label}
    </Button>
  );
}

function RuntimeTable({
  component,
  session
}: {
  component: UIComponent;
  session: RuntimeSession;
}) {
  const props = component.props ?? {};
  const binding = props.binding as string | undefined;
  const title = (props.title as string) ?? "テーブル";
  const columns = (props.columns as Array<{ field: string; headerName: string }>) ?? [];
  const rows = (binding ? (session.context[binding] as Array<Record<string, unknown>>) : []) ?? [];

  return (
    <Stack spacing={1}>
      <Typography variant="subtitle1" fontWeight={600}>
        {title}
      </Typography>
      <Box sx={{ overflowX: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column.field} style={{ textAlign: "left", padding: "8px", borderBottom: "1px solid #e0e0e0" }}>
                  {column.headerName}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr>
                <td colSpan={columns.length} style={{ padding: "12px", color: "#888" }}>
                  データがありません。
                </td>
              </tr>
            ) : (
              rows.map((row, index) => (
                <tr key={`${component.id}-${index}`}>
                  {columns.map((column) => (
                    <td key={column.field} style={{ padding: "8px", borderBottom: "1px solid #f0f0f0" }}>
                      {String(row[column.field] ?? "")}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </Box>
    </Stack>
  );
}

