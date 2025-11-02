import { Alert, Chip, Stack, Typography } from "@mui/material";

import type { WorkflowSessionState } from "../types";

function translateStatus(status: WorkflowSessionState["status"]) {
  switch (status) {
    case "processing":
      return "処理中";
    case "completed":
      return "完了";
    case "error":
      return "エラー";
    default:
      return "入力待ち";
  }
}

interface Props {
  session: WorkflowSessionState | null;
}

export function SessionStatus({ session }: Props) {
  if (!session) return null;
  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={1} alignItems="center">
        <Typography variant="subtitle1">セッション状態:</Typography>
        <Chip label={translateStatus(session.status)} color={session.status === "completed" ? "success" : session.status === "processing" ? "primary" : session.status === "error" ? "error" : "default"} />
        <Typography variant="body2" color="text.secondary">
          最終更新: {new Date(session.updated_at).toLocaleString()}
        </Typography>
      </Stack>
      {session.last_error && (
        <Alert severity="error" variant="outlined">
          {session.last_error}
        </Alert>
      )}
    </Stack>
  );
}
