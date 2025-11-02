import { useCallback, useEffect, useRef, useState } from "react";
import type { GenerationStatus } from "../types";
import { fetchJob } from "../api";

type PollingState = {
  status: GenerationStatus | null;
  loading: boolean;
  error: string | null;
};

export function useJobPolling(
  jobId: string | null,
  intervalMs = 2000,
  fetcher: (jobId: string) => Promise<GenerationStatus> = fetchJob
) {
  const [state, setState] = useState<PollingState>({
    status: null,
    loading: Boolean(jobId),
    error: null
  });

  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stop = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const tick = useCallback(async () => {
    if (!jobId) return;
    try {
      const result = await fetcher(jobId);
      setState({ status: result, loading: false, error: null });
      if (result.status === "completed" || result.status === "failed") {
        stop();
      }
    } catch (error) {
      stop();
      setState((prev) => ({ ...prev, loading: false, error: "進捗の取得に失敗しました" }));
    }
  }, [fetcher, jobId, stop]);

  useEffect(() => {
    if (!jobId) {
      setState({ status: null, loading: false, error: null });
      stop();
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));
    void tick();
    timerRef.current = setInterval(tick, intervalMs);

    return () => stop();
  }, [jobId, intervalMs, stop, tick]);

  return {
    status: state.status,
    loading: state.loading,
    error: state.error,
    refresh: tick,
    stop
  };
}

