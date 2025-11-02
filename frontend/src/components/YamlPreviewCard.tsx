import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { Box, Button, Paper, Stack, Typography } from "@mui/material";

import { useState } from "react";

type Props = {
  yaml?: string | null;
};

export function YamlPreviewCard({ yaml }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    if (!yaml) return;
    try {
      await navigator.clipboard.writeText(yaml);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      console.error("Failed to copy yaml", error);
    }
  };

  return (
    <Paper variant="outlined" sx={{ p: 3, height: "100%" }} aria-label="workflow.yaml プレビュー">
      <Stack spacing={2} sx={{ height: "100%" }}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
          <Typography variant="h6" component="h2">
            生成された workflow.yaml
          </Typography>
          <Button
            variant="outlined"
            startIcon={<ContentCopyIcon />}
            onClick={handleCopy}
            disabled={!yaml}
          >
            {copied ? "コピーしました" : "コピー"}
          </Button>
        </Stack>

        {yaml ? (
          <Box
            component="pre"
            sx={{
              flexGrow: 1,
              overflow: "auto",
              bgcolor: "grey.50",
              borderRadius: 1,
              p: 2,
              border: "1px solid",
              borderColor: "divider",
              fontFamily: "'Fira Code', monospace",
              fontSize: 14,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word"
            }}
          >
            {yaml}
          </Box>
        ) : (
          <Typography variant="body2" color="text.secondary">
            生成結果が表示されると workflow.yaml をプレビューできます。
          </Typography>
        )}
      </Stack>
    </Paper>
  );
}
