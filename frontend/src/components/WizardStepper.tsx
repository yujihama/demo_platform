import {
  Box,
  Step,
  StepLabel,
  Stepper,
  Typography,
  Chip
} from "@mui/material";
import type { JobStep, StepStatus } from "../types";

const statusColorMap: Record<StepStatus, "default" | "primary" | "error" | "success"> = {
  pending: "default",
  running: "primary",
  completed: "success",
  failed: "error"
};

type Props = {
  steps: JobStep[];
  activeStep: number;
};

export function WizardStepper({ steps, activeStep }: Props) {
  return (
    <Box>
      <Stepper activeStep={activeStep} alternativeLabel>
        {steps.map((step) => (
          <Step key={step.id}>
            <StepLabel>
              <Box sx={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                <Typography variant="body2" fontWeight={600}>
                  {step.label}
                </Typography>
                <Chip
                  size="small"
                  color={statusColorMap[step.status]}
                  label={translateStatus(step.status)}
                  sx={{ mt: 1 }}
                />
              </Box>
            </StepLabel>
          </Step>
        ))}
      </Stepper>
    </Box>
  );
}

function translateStatus(status: StepStatus) {
  switch (status) {
    case "running":
      return "進行中";
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    default:
      return "待機";
  }
}

