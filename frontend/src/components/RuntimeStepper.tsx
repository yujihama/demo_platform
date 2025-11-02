import { Step, StepLabel, Stepper } from "@mui/material";

import type { UIStep, WorkflowSessionState } from "../types";

interface Props {
  steps: UIStep[];
  session: WorkflowSessionState | null;
}

export function RuntimeStepper({ steps, session }: Props) {
  const activeIndex = session && session.active_ui_step
    ? Math.max(0, steps.findIndex((step) => step.id === session.active_ui_step))
    : 0;

  return (
    <Stepper activeStep={activeIndex} alternativeLabel sx={{ py: 2 }}>
      {steps.map((step) => (
        <Step key={step.id} completed={session?.completed_ui_steps.includes(step.id)}>
          <StepLabel>{step.title}</StepLabel>
        </Step>
      ))}
    </Stepper>
  );
}
