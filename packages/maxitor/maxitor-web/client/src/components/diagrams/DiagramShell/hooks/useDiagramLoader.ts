// src/components/diagrams/DiagramShell/hooks/useDiagramLoader.ts
import { NoSourceYetError } from "@/api/client";
import { useEffect, useState } from "react";

export type DiagramLoaderResult<T> = {
  data: T | null;
  dataVersion: number;
  loading: boolean;
  error: string | null;
};

export type UseDiagramLoaderOptions = {
  /** Keep showing the previous payload until the next request finishes (avoids remounting UI state). */
  keepPreviousData?: boolean;
};

/**
 * Async diagram data loader with cancellation. Pass ``loader`` from ``useCallback`` so
 * dependency changes do not cause accidental reload loops.
 */
export function useDiagramLoader<T>(
  loader: () => Promise<T>,
  options?: UseDiagramLoaderOptions,
): DiagramLoaderResult<T> {
  const keepPreviousData = options?.keepPreviousData ?? false;
  const [data, setData] = useState<T | null>(null);
  const [dataVersion, setDataVersion] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    if (!keepPreviousData) {
      setData(null);
    }
    setLoading(true);
    // No source yet is waiting, not failing: the spinner stays until the source is named and the read runs again.
    let waiting = false;
    void loader()
      .then((value) => {
        if (!cancelled) {
          setData(value);
          setDataVersion((v) => v + 1);
        }
      })
      .catch((e: unknown) => {
        if (cancelled) return;
        if (e instanceof NoSourceYetError) waiting = true;
        else setError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled && !waiting) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [loader]);

  return { data, dataVersion, loading, error };
}
