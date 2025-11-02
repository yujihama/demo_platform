import { useState, useEffect } from "react";
import {
  Box,
  Paper,
  Typography,
  Button,
  Alert,
  CircularProgress,
  Stack,
  Card,
  CardContent,
} from "@mui/material";
import DownloadIcon from "@mui/icons-material/Download";
import { getConversationWorkflow } from "../api";

interface WorkflowPreviewProps {
  sessionId: string;
  onDownload?: () => void;
}

export default function WorkflowPreview({ sessionId, onDownload }: WorkflowPreviewProps) {
  const [workflowYaml, setWorkflowYaml] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const loadWorkflow = async () => {
      try {
        setLoading(true);
        setError(null);
        const response = await getConversationWorkflow(sessionId);
        setWorkflowYaml(response.workflow_yaml);
      } catch (err) {
        setError(err instanceof Error ? err.message : "????????????????");
      } finally {
        setLoading(false);
      }
    };

    if (sessionId) {
      void loadWorkflow();
    }
  }, [sessionId]);

  if (loading) {
    return (
      <Box sx={{ display: "flex", justifyContent: "center", p: 3 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Card>
      <CardContent>
        <Stack spacing={2}>
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <Typography variant="h6">????? workflow.yaml</Typography>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={onDownload}
            >
              ????????????
            </Button>
          </Box>

          <Paper
            variant="outlined"
            sx={{
              p: 2,
              bgcolor: "grey.50",
              maxHeight: 500,
              overflow: "auto",
              fontFamily: "monospace",
              fontSize: "0.875rem",
            }}
          >
            <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word" }}>
              {workflowYaml || "?????????????????"}
            </pre>
          </Paper>
        </Stack>
      </CardContent>
    </Card>
  );
}
