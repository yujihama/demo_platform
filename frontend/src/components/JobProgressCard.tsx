import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import ErrorIcon from "@mui/icons-material/Error";
import HourglassTopIcon from "@mui/icons-material/HourglassTop";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import {
  Chip,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  Paper,
  Stack,
  Typography
} from "@mui/material";

import type { JobStatus, JobStep, StepStatus } from "../types";

const STATUS_LABEL: Record<StepStatus, string> = {
  pending: "待機中",
  running: "実行中",
  completed: "完了",
  failed: "失敗"
};

const ICON_BY_STATUS: Record<StepStatus, JSX.Element> = {
  pending: <HourglassTopIcon color="disabled" />, // pending
  running: <PlayArrowIcon color="info" />, // running
  completed: <CheckCircleIcon color="success" />, // completed
  failed: <ErrorIcon color="error" /> // failed
};

type Props = {
  steps: JobStep[];
  status: JobStatus | null;
};

export function JobProgressCard({ steps, status }: Props) {
  return (
    <Paper variant="outlined" sx={{ p: 3 }} aria-label="生成ステップ">
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          生成ステップ
        </Typography>
        {status && (
          <Chip
            label={status === "completed" ? "完了" : status === "failed" ? "失敗" : "実行中"}
            color={status === "completed" ? "success" : status === "failed" ? "error" : "info"}
            sx={{ alignSelf: "flex-start" }}
          />
        )}
        <List dense disablePadding>
          {steps.map((step) => (
            <ListItem key={step.id} sx={{ alignItems: "flex-start", py: 1 }}>
              <ListItemAvatar>
                {ICON_BY_STATUS[step.status]}
              </ListItemAvatar>
              <ListItemText
                primary={
                  <Typography variant="subtitle1" component="span">
                    {step.label}
                  </Typography>
                }
                secondary={
                  <Stack spacing={0.5}>
                    <Typography variant="body2" color="text.secondary">
                      {STATUS_LABEL[step.status]}
                    </Typography>
                    {step.message && (
                      <Typography variant="body2" color="text.secondary">
                        {step.message}
                      </Typography>
                    )}
                  </Stack>
                }
              />
            </ListItem>
          ))}
        </List>
      </Stack>
    </Paper>
  );
}
