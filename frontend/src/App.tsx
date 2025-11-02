import { useState } from "react";
import { Box, Button, CircularProgress, Container, Stack, Typography, Alert } from "@mui/material";

import { useRuntimeSession } from "./hooks/useRuntimeSession";
import { RuntimeRenderer } from "./runtime/RuntimeRenderer";
import type { UIComponent } from "./types";

export default function App() {
  const { workflow, session, loading, error, initialise, advance, uploadFile, updateValue } = useRuntimeSession();
  const [processing, setProcessing] = useState(false);

  const handleAdvance = async () => {
    if (!session) return;
    setProcessing(true);
    try {
      await advance();
    } finally {
      setProcessing(false);
    }
  };

  const handleUpload = async (component: UIComponent, file: File) => {
    setProcessing(true);
    try {
      await uploadFile(component, file);
    } finally {
      setProcessing(false);
    }
  };

  const handleUpdate = async (component: UIComponent, value: unknown) => {
    setProcessing(true);
    try {
      await updateValue(component, value);
    } finally {
      setProcessing(false);
    }
  };

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="md">
        <Stack spacing={4}>
          <Stack spacing={1}>
            <Typography variant="h4" fontWeight={700}>
              汎用実行エンジン プレビュー
            </Typography>
            <Typography variant="body1" color="text.secondary">
              workflow.yaml に基づき、UIとパイプラインを動的に実行します。
            </Typography>
          </Stack>

          <Stack direction="row" spacing={2}>
            <Button variant="outlined" onClick={() => initialise()} disabled={loading || processing}>
              セッションをリセット
            </Button>
            {processing && <CircularProgress size={24} />}
          </Stack>

          {loading && (
            <Stack alignItems="center" spacing={2}>
              <CircularProgress />
              <Typography variant="body2" color="text.secondary">
                セッションを初期化しています…
              </Typography>
            </Stack>
          )}

          {!loading && error && <Alert severity="error">{error}</Alert>}

          {!loading && workflow && session && (
            <RuntimeRenderer
              workflow={workflow}
              session={session}
              onAdvance={handleAdvance}
              onUploadFile={handleUpload}
              onUpdateValue={handleUpdate}
              processing={processing}
              error={session.last_error ?? null}
            />
          )}
        </Stack>
      </Container>
    </Box>
  );
}

