import { useState, useEffect, useRef } from "react";
import {
  Box,
  Paper,
  TextField,
  Button,
  Stack,
  Typography,
  CircularProgress,
  Alert,
  Card,
  CardContent,
} from "@mui/material";
import SendIcon from "@mui/icons-material/Send";
import DownloadIcon from "@mui/icons-material/Download";
import { createConversation, getConversationStatus, type ConversationMessage } from "../api";

interface ChatUIProps {
  onWorkflowReady?: (sessionId: string) => void;
}

export default function ChatUI({ onWorkflowReady }: ChatUIProps) {
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workflowReady, setWorkflowReady] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (!sessionId || status === "completed" || status === "failed") {
      return;
    }

    const pollInterval = setInterval(async () => {
      try {
        const response = await getConversationStatus(sessionId);
        setStatus(response.status);
        setMessages(response.messages);
        setWorkflowReady(response.workflow_ready);

        if (response.workflow_ready && onWorkflowReady) {
          onWorkflowReady(sessionId);
        }

        if (response.status === "completed" || response.status === "failed") {
          clearInterval(pollInterval);
          setLoading(false);
        }
      } catch (err) {
        console.error("Failed to poll conversation status:", err);
        clearInterval(pollInterval);
        setLoading(false);
      }
    }, 2000);

    return () => clearInterval(pollInterval);
  }, [sessionId, status, onWorkflowReady]);

  const handleSend = async () => {
    if (!input.trim() || loading) {
      return;
    }

    const prompt = input.trim();
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const response = await createConversation({
        prompt,
        user_id: "default",
      });
      setSessionId(response.session_id);
      setStatus(response.status);
      setMessages([
        { role: "user", content: prompt },
        { role: "assistant", content: response.message || "?????????..." },
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "??????????");
      setLoading(false);
    }
  };

  const renderMessage = (message: ConversationMessage, index: number) => {
    const isUser = message.role === "user";
    return (
      <Box
        key={index}
        sx={{
          display: "flex",
          justifyContent: isUser ? "flex-end" : "flex-start",
          mb: 2,
        }}
      >
        <Paper
          sx={{
            p: 2,
            maxWidth: "70%",
            bgcolor: isUser ? "primary.light" : "grey.100",
            color: isUser ? "primary.contrastText" : "text.primary",
          }}
        >
          <Typography variant="body1" sx={{ whiteSpace: "pre-wrap" }}>
            {message.content}
          </Typography>
        </Paper>
      </Box>
    );
  };

  return (
    <Card sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <CardContent sx={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
        <Typography variant="h6" gutterBottom>
          LLM??????????
        </Typography>

        <Box
          sx={{
            flex: 1,
            overflowY: "auto",
            mb: 2,
            p: 2,
            bgcolor: "background.paper",
            borderRadius: 1,
            minHeight: 300,
          }}
        >
          {messages.length === 0 && (
            <Alert severity="info">
              ??????????????????????????????????????????????????
            </Alert>
          )}
          {messages.map((msg, idx) => renderMessage(msg, idx))}
          {loading && status !== "completed" && status !== "failed" && (
            <Box sx={{ display: "flex", justifyContent: "flex-start", mb: 2 }}>
              <CircularProgress size={24} />
              <Typography variant="body2" sx={{ ml: 1, alignSelf: "center" }}>
                ???...
              </Typography>
            </Box>
          )}
          <div ref={messagesEndRef} />
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {workflowReady && (
          <Alert severity="success" sx={{ mb: 2 }}>
            workflow.yaml???????????
          </Alert>
        )}

        <Stack direction="row" spacing={1}>
          <TextField
            fullWidth
            size="small"
            placeholder="???????????..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                void handleSend();
              }
            }}
            disabled={loading || workflowReady}
          />
          <Button
            variant="contained"
            endIcon={loading ? <CircularProgress size={20} /> : <SendIcon />}
            onClick={handleSend}
            disabled={loading || !input.trim() || workflowReady}
          >
            ??
          </Button>
        </Stack>
      </CardContent>
    </Card>
  );
}
