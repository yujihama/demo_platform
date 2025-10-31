import { Box, Button, Paper, Stack, Typography } from "@mui/material";
import type { GenerationStatus } from "../types";

type Props = {
  status: GenerationStatus | null;
  onRestart: () => void;
};

export function StepDownload({ status, onRestart }: Props) {
  const downloadUrl = status?.download_url ?? "";

  return (
    <Paper variant="outlined" sx={{ p: 3, display: "grid", gap: 2 }}>
      <Typography variant="h6">成果物ダウンロード</Typography>
      {downloadUrl ? (
        <Stack direction="row" spacing={2}>
          <Button
            component="a"
            href={downloadUrl}
            target="_blank"
            rel="noopener"
            variant="contained"
            color="primary"
          >
            ZIP をダウンロード
          </Button>
          <Button variant="outlined" onClick={onRestart}>
            再実行
          </Button>
        </Stack>
      ) : (
        <Typography color="text.secondary">成果物の準備が完了するとダウンロードリンクが表示されます。</Typography>
      )}

      {status?.metadata && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="subtitle2">メタデータ</Typography>
          <pre style={{ background: "#f5f7fb", padding: 16, borderRadius: 8 }}>
            {JSON.stringify(status.metadata, null, 2)}
          </pre>
        </Box>
      )}
    </Paper>
  );
}

