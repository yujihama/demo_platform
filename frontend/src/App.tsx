import { useEffect, useMemo, useState } from "react";
import {
  Box,
  CircularProgress,
  Container,
  Paper,
  Stack,
  Typography
} from "@mui/material";
import axios from "axios";

import {
  createRuntimeSession,
  fetchRuntimeSession,
  fetchWorkflowDefinition,
  submitRuntimeStep
} from "./api";
import { RuntimeStepper } from "./components/RuntimeStepper";
import { SessionStatus } from "./components/SessionStatus";
import { StepRenderer } from "./components/StepRenderer";
import type { PipelineStepDefinition, WorkflowDefinition, WorkflowSessionState } from "./types";

const SESSION_STORAGE_KEY = "workflow_runtime_session_id";
const POLLING_INTERVAL = Number(import.meta.env.VITE_RUNTIME_POLLING ?? 2000);

function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.join("\n");
  }
  if (error instanceof Error) return error.message;
  return "予期せぬエラーが発生しました。";
}

export default function App() {
  const [definition, setDefinition] = useState<WorkflowDefinition | null>(null);
  const [session, setSession] = useState<WorkflowSessionState | null>(null);
  const [formState, setFormState] = useState<Record<string, unknown>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submittingStepId, setSubmittingStepId] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    async function initialise() {
      try {
        const workflow = await fetchWorkflowDefinition();
        if (!mounted) return;
        setDefinition(workflow);

        const sessionState = await loadOrCreateSession();
        if (!mounted) return;
        setSession(sessionState);
      } catch (initialError) {
        if (!mounted) return;
        setError(getErrorMessage(initialError));
      } finally {
        if (mounted) setLoading(false);
      }
    }

    initialise();
    return () => {
      mounted = false;
    };
  }, []);

  useEffect(() => {
    if (!session || session.status !== "processing") return;
    const interval = window.setInterval(async () => {
      try {
        const updated = await fetchRuntimeSession(session.session_id);
        setSession(updated);
      } catch (pollError) {
        setError(getErrorMessage(pollError));
      }
    }, POLLING_INTERVAL);
    return () => window.clearInterval(interval);
  }, [session?.session_id, session?.status]);

  const activeUIStep = useMemo(() => {
    const steps = definition?.ui?.steps ?? [];
    if (!steps.length) return null;
    if (!session?.active_ui_step) return steps[0];
    return steps.find((step) => step.id === session.active_ui_step) ?? steps[0];
  }, [definition, session]);

  const handleFileChange = (componentId: string, file: File | null) => {
    setFormState((prev) => {
      const next = { ...prev };
      if (file) {
        next[componentId] = file;
      } else {
        delete next[componentId];
      }
      return next;
    });
  };

  const handleSubmit = async (stepId: string) => {
    if (!session || !definition) return;
    const pipelineStep = findPipelineStep(definition.pipeline.steps, stepId);
    const requiredComponents = Array.isArray(pipelineStep?.params?.input_components)
      ? (pipelineStep?.params?.input_components as string[])
      : [];

    const data: Record<string, unknown> = {};
    let file: File | null = null;
    for (const componentId of requiredComponents) {
      const value = formState[componentId];
      if (value instanceof File) {
        file = value;
      } else if (value !== undefined) {
        data[componentId] = value;
      }
    }

    setSubmittingStepId(stepId);
    setError(null);
    try {
      const updated = await submitRuntimeStep(session.session_id, stepId, {
        data,
        file
      });
      setSession(updated);
      setFormState((prev) => {
        const next = { ...prev };
        for (const componentId of requiredComponents) {
          delete next[componentId];
        }
        return next;
      });
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setSubmittingStepId(null);
    }
  };

  const handleReset = async () => {
    setSubmittingStepId(null);
    setError(null);
    localStorage.removeItem(SESSION_STORAGE_KEY);
    try {
      const newSession = await loadOrCreateSession(true);
      setSession(newSession);
      setFormState({});
    } catch (resetError) {
      setError(getErrorMessage(resetError));
    }
  };

  async function loadOrCreateSession(forceNew = false) {
    if (!forceNew) {
      const storedId = localStorage.getItem(SESSION_STORAGE_KEY);
      if (storedId) {
        try {
          const existing = await fetchRuntimeSession(storedId);
          localStorage.setItem(SESSION_STORAGE_KEY, existing.session_id);
          return existing;
        } catch (fetchError) {
          console.warn("既存セッションの復元に失敗したため、新しいセッションを作成します", fetchError);
        }
      }
    }
    const created = await createRuntimeSession();
    localStorage.setItem(SESSION_STORAGE_KEY, created.session_id);
    return created;
  }

  if (loading) {
    return (
      <Box sx={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <CircularProgress />
      </Box>
    );
  }

  if (!definition || !definition.ui) {
    return (
      <Box sx={{ p: 4 }}>
        <Typography variant="h5">workflow.yaml の UI 定義が見つかりませんでした。</Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ py: 6, bgcolor: "#f5f7fb", minHeight: "100vh" }}>
      <Container maxWidth="md">
        <Stack spacing={4}>
          <Box>
            <Typography variant="h4" fontWeight={700} gutterBottom>
              {definition.info.name}
            </Typography>
            <Typography variant="body1" color="text.secondary">
              {definition.info.description}
            </Typography>
          </Box>

          <Paper variant="outlined" sx={{ p: 3 }}>
            <SessionStatus session={session} />
          </Paper>

          <Paper variant="outlined" sx={{ p: 3 }}>
            <RuntimeStepper steps={definition.ui.steps} session={session} />
          </Paper>

          {error && (
            <Paper variant="outlined" sx={{ p: 3, borderColor: "error.light" }}>
              <Typography variant="body1" color="error.main">
                {error}
              </Typography>
            </Paper>
          )}

          {activeUIStep && (
            <Paper variant="outlined" sx={{ p: 4 }}>
              <Stack spacing={3}>
                <Typography variant="h5" fontWeight={600}>
                  {activeUIStep.title}
                </Typography>

                <StepRenderer
                  step={activeUIStep}
                  definition={definition}
                  session={session}
                  formState={formState}
                  submittingStepId={submittingStepId}
                  onFileChange={handleFileChange}
                  onSubmit={handleSubmit}
                  onReset={handleReset}
                />
              </Stack>
            </Paper>
          )}
        </Stack>
      </Container>
    </Box>
  );
}

function findPipelineStep(steps: PipelineStepDefinition[], stepId: string) {
  return steps.find((step) => step.id === stepId);
}
