// src/components/diagrams/DiagramShell/hooks/useDiagramLoader.test.ts
import { renderHook, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { NoSourceYetError } from "@/api/client";
import { useDiagramLoader } from "./useDiagramLoader";

describe("a diagram's read", () => {
  it("waits, spinner on and no error, while the tab has no source yet (spec 038)", async () => {
    const loader = () => Promise.reject(new NoSourceYetError());
    const { result } = renderHook(() => useDiagramLoader(loader));
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(result.current.error).toBeNull();
    expect(result.current.loading).toBe(true);
  });

  it("still reports a read that failed", async () => {
    const loader = () => Promise.reject(new Error("list-domains 422"));
    const { result } = renderHook(() => useDiagramLoader(loader));
    await waitFor(() => expect(result.current.error).toBe("list-domains 422"));
    expect(result.current.loading).toBe(false);
  });
});
