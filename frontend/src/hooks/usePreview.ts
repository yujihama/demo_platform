import { useEffect, useState } from "react";
import { fetchPreview } from "../api";

export function usePreview(specId: string | null) {
  const [html, setHtml] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!specId) {
      setHtml("");
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    fetchPreview(specId)
      .then((content) => {
        if (active) {
          setHtml(content);
        }
      })
      .catch(() => {
        if (active) setError("プレビューの取得に失敗しました");
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [specId]);

  return { html, loading, error };
}

