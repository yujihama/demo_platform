import { Box, Button, CircularProgress, Paper, Stack, Typography } from "@mui/material";

type Props = {
  html: string;
  loading: boolean;
  error: string | null;
  onApprove: () => void;
  onReject: () => void;
};

export function StepPreview({ html, loading, error, onApprove, onReject }: Props) {
  return (
    <Paper variant="outlined" sx={{ p: 3, display: "grid", gap: 3 }}>
      <Typography variant="h6">モックプレビュー</Typography>
      {loading && (
        <Stack direction="row" gap={2} alignItems="center">
          <CircularProgress size={20} />
          <Typography>プレビューを読み込んでいます...</Typography>
        </Stack>
      )}
      {error && (
        <Typography color="error" role="alert">
          {error}
        </Typography>
      )}
      {!loading && !error && (
        <Box
          sx={{
            borderRadius: 2,
            border: "1px solid",
            borderColor: "divider",
            overflow: "hidden",
            height: 360,
            bgcolor: "background.paper"
          }}
          dangerouslySetInnerHTML={{ __html: html }}
        />
      )}

      <Stack direction="row" justifyContent="flex-end" spacing={2}>
        <Button color="error" variant="outlined" onClick={onReject} disabled={loading}>
          差し戻す
        </Button>
        <Button color="primary" variant="contained" onClick={onApprove} disabled={loading}>
          承認して進む
        </Button>
      </Stack>
    </Paper>
  );
}

