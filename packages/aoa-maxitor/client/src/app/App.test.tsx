// src/app/App.test.tsx
import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "@/app/App";
import { setActiveSource } from "@/api/client";

// The viewers pull in G6 and the Graphviz wasm at import time; this test is about which requests
// the page makes, so they are replaced by placeholders.
vi.mock("@/components/diagrams/FullGraphViewer", () => ({ FullGraphViewer: () => null }));
vi.mock("@/components/diagrams/ErdViewer", () => ({ ErdViewer: () => null }));
vi.mock("@/components/diagrams/LifecycleFsmViewer", () => ({ LifecycleFsmViewer: () => null }));
vi.mock("@/components/diagrams/UseCaseDiagramViewer", () => ({ UseCaseDiagramViewer: () => null }));

const SOURCE = "https://service.test/graph-json";

type Call = { url: string; method: string };

let calls: Call[] = [];

const EMPTY_SIDEBAR = {
  level1_nodes: [],
  level2_diagrams: [],
  level2_nodes: [],
  level3_diagrams: [],
};

function ok(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

beforeEach(() => {
  calls = [];
  setActiveSource(null);
  vi.stubGlobal("fetch", async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = (init?.method ?? "GET").toUpperCase();
    calls.push({ url, method });
    return url.startsWith("/api/load") ? ok({ status: "ok" }) : ok(EMPTY_SIDEBAR);
  });
  // MUI's Drawer/useMediaQuery reach for these; jsdom has neither.
  vi.stubGlobal("matchMedia", () => ({
    matches: false,
    addEventListener: () => {},
    removeEventListener: () => {},
    addListener: () => {},
    removeListener: () => {},
    dispatchEvent: () => false,
  }));
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState({}, "", "/");
});

describe("App", () => {
  it("sends every graph read of a deep link with the link's source", async () => {
    window.history.replaceState({}, "", `/?source=${encodeURIComponent(SOURCE)}`);

    render(<App />);

    await waitFor(() => {
      expect(calls.some((c) => c.url.startsWith("/api/sidebar"))).toBe(true);
    });
    await waitFor(() => {
      expect(calls.filter((c) => c.method === "POST" && c.url.startsWith("/api/load"))).toHaveLength(1);
    });

    const reads = calls.filter((c) => c.method === "GET");
    expect(reads.length).toBeGreaterThan(0);
    for (const read of reads) {
      expect(new URL(read.url, "http://localhost").searchParams.get("source")).toBe(SOURCE);
    }
    expect(calls.filter((c) => c.url.startsWith("/api/sidebar")).length).toBeGreaterThan(0);
    // The source is set during the first render, never in an effect: the page's first request
    // already knows it, instead of waiting for the load that would go out ahead of it.
    expect(calls[0].method).toBe("GET");
    expect(new URL(calls[0].url, "http://localhost").searchParams.get("source")).toBe(SOURCE);
  });

  it("asks the server for nothing graph-related on the start page", async () => {
    window.history.replaceState({}, "", "/");

    render(<App />);

    await new Promise((resolve) => setTimeout(resolve, 50));
    expect(calls).toHaveLength(0);
  });
});
