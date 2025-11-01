import { Box, Typography, Paper } from "@mui/material";
import type { GenerationStatus } from "../types";
import { WizardStepper } from "./WizardStepper";

type Props = {
  status: GenerationStatus | null;
  loading: boolean;
};

export function StepProgress({ status, loading }: Props) {
  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        生成進捗
      </Typography>
      {loading && <Typography>進捗を取得しています...</Typography>}
      {status && (
        <>
          <WizardStepper steps={status.steps} activeStep={computeActiveStep(status)} />
          <Box mt={2}>
            <Typography variant="body2" color="text.secondary">
              現在のジョブステータス: {translateStatus(status.status)}
            </Typography>
          </Box>
        </>
      )}
    </Paper>
  );
}

function computeActiveStep(status: GenerationStatus) {
  const completed = status.steps.filter((step) => step.status === "completed").length;
  return Math.min(completed, status.steps.length - 1);
}

function translateStatus(status: string) {
  switch (status) {
    case "spec_generating":
      return "仕様生成中";
    case "templates_rendering":
      return "テンプレートレンダリング中";
    case "packaging":
      return "パッケージング中";
    case "completed":
      return "完了";
    case "failed":
      return "失敗";
    default:
      return "受信済み";
  }
}

