import { useCallback, useEffect, useRef, useState } from "react";
import {
  advanceRuntimeSession,
  createRuntimeSession,
  fetchRuntimeSession,
  uploadComponentFile,
  updateComponentValue
} from "../api";
import type { RuntimeSession, UIComponent, WorkflowYaml } from "../types";
import { logger } from "../utils/logger";

interface RuntimeState {
  workflow: WorkflowYaml | null;
  session: RuntimeSession | null;
  loading: boolean;
  error: string | null;
}

export function useRuntimeSession() {
  const [state, setState] = useState<RuntimeState>({ workflow: null, session: null, loading: true, error: null });
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const startPolling = useCallback((sessionId: string) => {
    if (pollingRef.current) return;
    pollingRef.current = setInterval(async () => {
      try {
        const { session } = await fetchRuntimeSession(sessionId);
        setState((prev) => ({ ...prev, session }));
      } catch (error) {
        logger.error("セッション状態の取得に失敗", error);
      }
    }, 2000);
  }, []);

  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  const initialise = useCallback(async () => {
    setState({ workflow: null, session: null, loading: true, error: null });
    try {
      const created = await createRuntimeSession();
      setState({ workflow: created.workflow, session: created.session, loading: false, error: null });
      if (created.session.status !== "completed") {
        startPolling(created.session.session_id);
      }
    } catch (error) {
      logger.error("セッション初期化に失敗", error);
      setState({ workflow: null, session: null, loading: false, error: "セッションの作成に失敗しました。" });
    }
  }, [startPolling]);

  useEffect(() => {
    initialise();
    return () => stopPolling();
  }, [initialise, stopPolling]);

  const advance = useCallback(async () => {
    if (!state.session) return;
    try {
      const { session } = await advanceRuntimeSession(state.session.session_id);
      setState((prev) => ({ ...prev, session }));
      if (session.status === "completed" || session.status === "failed") {
        stopPolling();
      } else {
        startPolling(session.session_id);
      }
    } catch (error) {
      logger.error("パイプラインの実行に失敗", error);
      setState((prev) => ({ ...prev, error: "パイプラインの実行に失敗しました。" }));
    }
  }, [state.session, startPolling, stopPolling]);

  const uploadFile = useCallback(
    async (component: UIComponent, file: File) => {
      if (!state.session) return;
      try {
        const { session } = await uploadComponentFile(state.session.session_id, component.id, file);
        setState((prev) => ({ ...prev, session }));
      } catch (error) {
        logger.error("ファイルのアップロードに失敗", error);
        setState((prev) => ({ ...prev, error: "ファイルのアップロードに失敗しました。" }));
      }
    },
    [state.session]
  );

  const updateValue = useCallback(
    async (component: UIComponent, value: unknown) => {
      if (!state.session) return;
      try {
        const { session } = await updateComponentValue(state.session.session_id, component.id, value);
        setState((prev) => ({ ...prev, session }));
      } catch (error) {
        logger.error("コンポーネント値の更新に失敗", error);
        setState((prev) => ({ ...prev, error: "コンポーネントの更新に失敗しました。" }));
      }
    },
    [state.session]
  );

  return {
    ...state,
    initialise,
    advance,
    uploadFile,
    updateValue,
  };
}

