import { useCallback, useEffect, useState } from "react";
import { createWorkflowSession, executeWorkflowSession, fetchWorkflowSession } from "../api";
import type { SessionExecuteRequest, WorkflowSessionResponse } from "../types";

interface UseWorkflowSessionResult {
  session: WorkflowSessionResponse | null;
  sessionId: string | null;
  loading: boolean;
  error: string | null;
  initialize: () => Promise<void>;
  execute: (payload: SessionExecuteRequest) => Promise<WorkflowSessionResponse | null>;
  refresh: () => Promise<void>;
}

export function useWorkflowSession(pollIntervalMs = 1500): UseWorkflowSessionResult {
  const [session, setSession] = useState<WorkflowSessionResponse | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const initialize = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const created = await createWorkflowSession();
      setSession(created);
      setSessionId(created.session_id);
    } catch (err) {
      console.error("Failed to create workflow session", err);
      setError("セッションの作成に失敗しました。バックエンドの起動を確認してください。");
    } finally {
      setLoading(false);
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!sessionId) return;
    try {
      const current = await fetchWorkflowSession(sessionId);
      setSession(current);
      setError(null);
    } catch (err) {
      console.error("Failed to refresh session", err);
      setError("セッション情報の取得に失敗しました");
    }
  }, [sessionId]);

  const execute = useCallback(
    async (payload: SessionExecuteRequest) => {
      if (!sessionId) {
        console.warn("Cannot execute workflow without a session");
        return null;
      }
      setLoading(true);
      setError(null);
      try {
        const result = await executeWorkflowSession(sessionId, payload);
        setSession(result);
        return result;
      } catch (err) {
        console.error("Failed to execute workflow", err);
        setError("ワークフローの実行に失敗しました");
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [sessionId]
  );

  useEffect(() => {
    if (!sessionId) return;
    if (session?.status !== "running") return;

    const timer = setInterval(() => {
      void refresh();
    }, pollIntervalMs);

    return () => clearInterval(timer);
  }, [sessionId, session?.status, pollIntervalMs, refresh]);

  return {
    session,
    sessionId,
    loading,
    error,
    initialize,
    execute,
    refresh
  };
}
