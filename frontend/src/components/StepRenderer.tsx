import {
  Box,
  Button,
  Paper,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Typography
} from "@mui/material";
import { useMemo } from "react";

import type { PipelineStepDefinition, UIStep, WorkflowDefinition, WorkflowSessionState } from "../types";
import { renderTemplate, resolvePath } from "../utils/runtime";

interface Props {
  step: UIStep;
  definition: WorkflowDefinition;
  session: WorkflowSessionState | null;
  formState: Record<string, unknown>;
  onFileChange: (componentId: string, file: File | null) => void;
  onSubmit: (stepId: string) => Promise<void>;
  onReset: () => Promise<void> | void;
  submittingStepId: string | null;
}

export function StepRenderer({
  step,
  definition,
  session,
  formState,
  onFileChange,
  onSubmit,
  onReset,
  submittingStepId
}: Props) {
  const context = session?.context ?? {};

  const pipelineMap = useMemo(() => {
    return new Map<string, PipelineStepDefinition>(
      definition.pipeline.steps.map((pipelineStep) => [pipelineStep.id, pipelineStep])
    );
  }, [definition.pipeline.steps]);

  return (
    <Stack spacing={3}>
      {step.description && (
        <Typography variant="body1" color="text.secondary">
          {step.description}
        </Typography>
      )}

      {step.components.map((component) => {
        const props = component.props ?? {};
        switch (component.type) {
          case "file_upload": {
            const selected = formState[component.id] as File | undefined;
            const helperText = typeof props.helperText === "string" ? (props.helperText as string) : undefined;
            return (
              <Paper key={component.id} variant="outlined" sx={{ p: 3 }}>
                <Stack spacing={1.5}>
                  <Typography variant="subtitle1" fontWeight={600}>
                    {(props.label as string) ?? "ファイルを選択"}
                  </Typography>
                  <Button
                    variant="contained"
                    component="label"
                    color={props.color as any ?? "primary"}
                  >
                    ファイルを選択
                    <input
                      type="file"
                      hidden
                      accept={(props.accept as string) ?? undefined}
                      onChange={(event) => {
                        const file = event.target.files?.[0] ?? null;
                        onFileChange(component.id, file);
                      }}
                    />
                  </Button>
                  <Typography variant="body2" color="text.secondary">
                    {selected ? `${selected.name} (${Math.round(selected.size / 1024)} KB)` : "未選択"}
                  </Typography>
                  {helperText && (
                    <Typography variant="body2" color="text.secondary">
                      {helperText}
                    </Typography>
                  )}
                </Stack>
              </Paper>
            );
          }
          case "text": {
            const template = props.template as string | undefined;
            const variant = (props.variant as any) ?? "body1";
            if (!template) return null;
            return (
              <Typography key={component.id} variant={variant} sx={{ whiteSpace: "pre-wrap" }}>
                {renderTemplate(template, context)}
              </Typography>
            );
          }
          case "table": {
            const rows = (resolvePath(context, props.source as string) as any[]) ?? [];
            const columns = Array.isArray(props.columns) ? props.columns : [];
            if (!Array.isArray(rows) || rows.length === 0) {
              return (
                <Typography key={component.id} variant="body2" color="text.secondary">
                  表示可能なデータがまだありません。
                </Typography>
              );
            }
            return (
              <Paper key={component.id} variant="outlined" sx={{ p: 2 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      {columns.map((column: any) => (
                        <TableCell key={column.field}>{column.label ?? column.field}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {rows.map((row, index) => (
                      <TableRow key={index}>
                        {columns.map((column: any) => (
                          <TableCell key={column.field}>{row[column.field] ?? "-"}</TableCell>
                        ))}
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </Paper>
            );
          }
          case "button": {
            const action = props.action as string | undefined;
            const targetStep = props.target_step as string | undefined;
            const color = (props.color as any) ?? "primary";
            const variant = (props.variant as any) ?? "contained";
            const label = (props.label as string) ?? "実行";

            if (action === "submit" && targetStep) {
              const pipelineStep = pipelineMap.get(targetStep);
              const requiredComponents = Array.isArray(pipelineStep?.params?.input_components)
                ? (pipelineStep?.params?.input_components as string[])
                : [];
              const hasAllInputs = requiredComponents.every((componentId) => {
                const value = formState[componentId];
                if (value instanceof File) return true;
                return value !== undefined && value !== null && value !== "";
              });
              const isSubmitting = submittingStepId === targetStep;
              return (
                <Box key={component.id}>
                  <Button
                    variant={variant}
                    color={color}
                    disabled={isSubmitting || (requiredComponents.length > 0 && !hasAllInputs)}
                    onClick={() => onSubmit(targetStep)}
                  >
                    {isSubmitting ? "処理中..." : label}
                  </Button>
                </Box>
              );
            }

            if (action === "reset") {
              return (
                <Box key={component.id}>
                  <Button variant={variant} color={color} onClick={onReset}>
                    {label}
                  </Button>
                </Box>
              );
            }

            return (
              <Box key={component.id}>
                <Button variant={variant} color={color} disabled>
                  {label}
                </Button>
              </Box>
            );
          }
          default:
            return (
              <Typography key={component.id} color="text.secondary">
                未対応のコンポーネントタイプ: {component.type}
              </Typography>
            );
        }
      })}
    </Stack>
  );
}
