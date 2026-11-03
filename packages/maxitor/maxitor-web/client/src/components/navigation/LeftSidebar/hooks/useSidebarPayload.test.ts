// src/components/navigation/LeftSidebar/hooks/useSidebarPayload.test.ts
import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getSidebar } from "@/api/sidebar";
import { useSidebarPayload } from "./useSidebarPayload";

vi.mock("@/api/sidebar", () => ({ getSidebar: vi.fn(async () => ({ level1_nodes: [{ id: "root" }] })) }));

describe("the sidebar's read", () => {
  beforeEach(() => vi.mocked(getSidebar).mockClear());

  it("is one read for the calls of one moment", async () => {
    const { result } = renderHook(() => useSidebarPayload());
    await act(async () => {
      await Promise.all([result.current.reload(), result.current.reload()]);
    });
    expect(getSidebar).toHaveBeenCalledOnce();
  });

  it("reads again for a later call", async () => {
    const { result } = renderHook(() => useSidebarPayload());
    await act(async () => {
      await result.current.reload();
      await result.current.reload();
    });
    expect(getSidebar).toHaveBeenCalledTimes(2);
  });
});
