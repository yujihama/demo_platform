import { useState } from "react";
import { Container, Box, Grid, Typography } from "@mui/material";
import ChatUI from "./components/ChatUI";
import WorkflowPreview from "./components/WorkflowPreview";
import { downloadWorkflowPackage } from "./api";

export default function AppGenerator() {
  const [sessionId, setSessionId] = useState<string | null>(null);

  const handleWorkflowReady = (id: string) => {
    setSessionId(id);
  };

  const handleDownload = async () => {
    if (!sessionId) {
      return;
    }

    try {
      const blob = await downloadWorkflowPackage(sessionId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `workflow-app-${sessionId.substring(0, 8)}.zip`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error("Failed to download package:", error);
      alert("?????????????");
    }
  };

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="lg">
        <Typography variant="h4" fontWeight={700} gutterBottom sx={{ mb: 4 }}>
          LLM????????????
        </Typography>

        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <ChatUI onWorkflowReady={handleWorkflowReady} />
          </Grid>

          <Grid item xs={12} md={6}>
            {sessionId ? (
              <WorkflowPreview sessionId={sessionId} onDownload={handleDownload} />
            ) : (
              <Box
                sx={{
                  p: 4,
                  textAlign: "center",
                  bgcolor: "background.paper",
                  borderRadius: 1,
                  border: "2px dashed",
                  borderColor: "divider",
                }}
              >
                <Typography variant="body1" color="text.secondary">
                  ???????????????????????????????????????
                </Typography>
              </Box>
            )}
          </Grid>
        </Grid>
      </Container>
    </Box>
  );
}
