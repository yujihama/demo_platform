import CloudDownloadIcon from "@mui/icons-material/CloudDownload";
import RefreshIcon from "@mui/icons-material/Refresh";
import { Box, Button, Paper, Stack, Typography } from "@mui/material";

type Props = {
  downloadUrl?: string | null;
  disabled?: boolean;
  onRestart?: () => void;
};

export function DownloadArtifactCard({ downloadUrl, disabled, onRestart }: Props) {
  const canDownload = Boolean(downloadUrl) && !disabled;

  return (
    <Paper variant="outlined" sx={{ p: 3 }} aria-label="成果物ダウンロード">
      <Stack spacing={2}>
        <Typography variant="h6" component="h2">
          成果物
        </Typography>
        <Typography variant="body2" color="text.secondary">
          パッケージには workflow.yaml、docker-compose.yml、.env テンプレートが含まれています。
        </Typography>
        <Box sx={{ display: "flex", gap: 2 }}>
          <Button
            component="a"
            href={canDownload ? downloadUrl ?? undefined : undefined}
            variant="contained"
            color="primary"
            startIcon={<CloudDownloadIcon />}
            disabled={!canDownload}
            target="_blank"
            rel="noopener noreferrer"
          >
            成果物をダウンロード
          </Button>
          <Button
            type="button"
            variant="outlined"
            color="secondary"
            onClick={onRestart}
            startIcon={<RefreshIcon />}
          >
            新しいリクエスト
          </Button>
        </Box>
      </Stack>
    </Paper>
  );
}
