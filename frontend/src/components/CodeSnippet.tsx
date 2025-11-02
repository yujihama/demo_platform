import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import { Box, IconButton, Tooltip } from "@mui/material";
import { useState } from "react";

type Props = {
  value: string;
  language?: string;
};

export function CodeSnippet({ value, language }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1500);
    } catch (error) {
      // Clipboard API が利用できない環境でも動作を続行する
      console.warn("Failed to copy content", error);
      setCopied(false);
    }
  };

  return (
    <Box
      sx={{
        position: "relative",
        bgcolor: "#0f172a",
        color: "#e2e8f0",
        borderRadius: 1,
        p: 2,
        fontFamily: "'Fira Code', 'Source Code Pro', monospace",
        fontSize: 14,
        lineHeight: 1.6,
        overflowX: "auto",
      }}
      data-language={language}
    >
      <Tooltip title={copied ? "コピーしました" : "コピー"} placement="top">
        <IconButton
          size="small"
          onClick={handleCopy}
          sx={{ position: "absolute", top: 8, right: 8, color: "#e2e8f0" }}
          aria-label="コードをコピー"
        >
          <ContentCopyIcon fontSize="small" />
        </IconButton>
      </Tooltip>
      <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{value}</pre>
    </Box>
  );
}
