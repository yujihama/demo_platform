import { Paper, Typography, List, ListItem, ListItemText, Chip, Stack } from "@mui/material";
import type { JobStep } from "../types";

type Props = {
  title: string;
  steps: JobStep[];
};

export function StepLogs({ title, steps }: Props) {
  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        {title}
      </Typography>
      <List>
        {steps.map((step) => (
          <ListItem key={step.id} alignItems="flex-start">
            <ListItemText
              primary={
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="subtitle2">{step.label}</Typography>
                  <Chip size="small" label={mapStatus(step.status)} color={chipColor(step.status)} />
                </Stack>
              }
              secondary={step.message ?? ""}
            />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
}

function mapStatus(status: string) {
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

function chipColor(status: string): "default" | "primary" | "success" | "error" {
  if (status === "completed") return "success";
  if (status === "failed") return "error";
  if (status === "running") return "primary";
  return "default";
}

