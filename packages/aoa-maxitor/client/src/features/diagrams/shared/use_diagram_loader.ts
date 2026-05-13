// packages/aoa-maxitor/client/src/features/diagrams/shared/use_diagram_loader.ts
import { useEffect, useState } from "react";

export type DiagramLoaderResult<T> = {
  data: T | null;
  loading: boolean;
  error: string | null;
};

/**
 * Async diagram data loader with cancellation. Pass ``loader`` from ``useCallback`` so
 * dependency changes do not cause accidental reload loops.
 */
export function useDiagramLoader<T>(loader: () => Promise<T>): DiagramLoaderResult<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    setData(null);
    setLoading(true);
    void loader()
      .then((value) => {
        if (!cancelled) setData(value);
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loader]);

  return { data, loading, error };
}
