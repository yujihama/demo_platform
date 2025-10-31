import { Paper, Typography } from "@mui/material";

export function SamplePrompt() {
  return (
    <Paper variant="outlined" sx={{ p: 2, bgcolor: "background.default" }}>
      <Typography variant="subtitle2" gutterBottom>
        サンプルプロンプト
      </Typography>
      <Typography variant="body2" color="text.secondary">
        「経理担当者がアップロードした請求書を自動で検証し、金額超過や重複を検知して承認フローに回す React + FastAPI アプリを生成して」
      </Typography>
    </Paper>
  );
}

