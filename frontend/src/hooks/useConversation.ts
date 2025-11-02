import { useCallback, useEffect, useMemo, useState } from "react";
import { fetchConversation, fetchWorkflowYaml, startConversation } from "../api";
import type { ConversationSession, ConversationStartRequest } from "../types";

interface UseConversationResult {
  session: ConversationSession | null;
  workflow: string | null;
  loading: boolean;
  error: string | null;
  start: (payload: ConversationStartRequest) => Promise<void>;
  refresh: () => Promise<void>;
  reset: () => void;
}

export function useConversation(pollIntervalMs = 2000): UseConversationResult {
  const [session, setSession] = useState<ConversationSession | null>(null);
  const [workflow, setWorkflow] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workflowFetchAttempted, setWorkflowFetchAttempted] = useState(false);

  const sessionId = useMemo(() => session?.session_id ?? null, [session?.session_id]);

  const start = useCallback(async (payload: ConversationStartRequest) => {
    setLoading(true);
    setError(null);
    try {
      const created = await startConversation(payload);
      setSession(created);
      setWorkflow(null);
      setWorkflowFetchAttempted(false);
    } catch (err) {
      console.error("Failed to start conversation", err);
      setError("会話の開始に失敗しました");
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const updated = await fetchConversation(sessionId);
      setSession(updated);
      setError(null);
      if (!updated.workflow_ready) {
        setWorkflowFetchAttempted(false);
      }
      if (updated.workflow_ready && !workflow) {
        try {
          const yaml = await fetchWorkflowYaml(sessionId);
          setWorkflow(yaml);
        } catch (err) {
          console.error("Failed to load workflow.yaml", err);
          setError("workflow.yaml の取得に失敗しました");
        }
      }
    } catch (err) {
      console.error("Failed to fetch conversation", err);
      setError("会話情報の取得に失敗しました");
    }
  }, [sessionId, workflow]);

  useEffect(() => {
    setWorkflowFetchAttempted(false);
  }, [sessionId]);

  useEffect(() => {
    if (!sessionId) return;
    if (!session) return;

    if (session.workflow_ready && !workflow && !workflowFetchAttempted) {
      setWorkflowFetchAttempted(true);
      void refresh();
    }

    const terminalStatuses: Array<ConversationSession["status"]> = ["completed", "failed"];
    if (terminalStatuses.includes(session.status)) {
      return;
    }

    const timer = setInterval(() => {
      void refresh();
    }, pollIntervalMs);

    return () => clearInterval(timer);
  }, [sessionId, session, workflow, refresh, pollIntervalMs, workflowFetchAttempted]);

  const reset = useCallback(() => {
    setSession(null);
    setWorkflow(null);
    setError(null);
    setWorkflowFetchAttempted(false);
  }, []);

  return {
    session,
    workflow,
    loading,
    error,
    start,
    refresh,
    reset
  };
}
