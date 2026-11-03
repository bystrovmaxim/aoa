// src/api/client.test.ts
import { afterEach, describe, expect, it, vi } from "vitest";
import { graphApiUrl, graphFetch, setActiveSource } from "@/api/client";
import { readUrlDeepLink } from "@/lib/urlState";

const SOURCE = "https://service.test/graph-json";

/** Decode the query string the way the server does (``parse_qsl``: ``+`` is a space). */
function search(url: string): URLSearchParams {
  return new URLSearchParams(url.slice(url.indexOf("?") + 1));
}

afterEach(() => {
  setActiveSource(null);
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function busy(retryAfterSeconds: number): Response {
  return {
    ok: false,
    status: 503,
    headers: new Headers({ "Retry-After": String(retryAfterSeconds) }),
    json: async () => ({ detail: "busy" }),
    text: async () => "busy",
  } as unknown as Response;
}

function answer(body: unknown): Response {
  return {
    ok: true,
    status: 200,
    headers: new Headers(),
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

describe("graphApiUrl", () => {
  it("appends the active source", () => {
    setActiveSource(SOURCE);
    const url = graphApiUrl("/api/sidebar");
    expect(url.startsWith("/api/sidebar?")).toBe(true);
    expect(search(url).get("source")).toBe(SOURCE);
  });

  it("keeps the route's own query parameters", () => {
    setActiveSource(SOURCE);
    const params = new URLSearchParams({ domain_id: "dom-1" });
    const url = graphApiUrl("/api/v1/domain-use-case-diagram", params);
    expect(url.startsWith("/api/v1/domain-use-case-diagram?")).toBe(true);
    expect(search(url).get("domain_id")).toBe("dom-1");
    expect(search(url).get("source")).toBe(SOURCE);
  });

  it("throws without an active source", () => {
    expect(() => graphApiUrl("/api/sidebar")).toThrow(/no active source/i);
  });

  it("keeps an address with &, +, %2F and a space unchanged after encoding and decoding", () => {
    const awkward = "https://service.test/a&b+c/d e/graph-json";
    setActiveSource(awkward);
    expect(search(graphApiUrl("/api/sidebar")).get("source")).toBe(awkward);
  });
});

describe("deep link", () => {
  it("still yields the source and the view from ?source=…&view=…", () => {
    window.history.replaceState({}, "", `/?source=${encodeURIComponent(SOURCE)}&view=full-graph`);
    const link = readUrlDeepLink();
    expect(link.source).toBe(SOURCE);
    expect(link.view).toBe("full-graph");
  });
});

describe("a busy server", () => {
  it("waits Retry-After, doubles after each further 503, and never waits more than 30 s", async () => {
    vi.useFakeTimers();
    setActiveSource(SOURCE);
    const responses: Response[] = [busy(5), busy(5), busy(5), busy(5), answer({})];
    const fetchMock = vi.fn(async () => responses.shift()!);
    vi.stubGlobal("fetch", fetchMock);

    const read = graphFetch("/api/sidebar");

    await vi.advanceTimersByTimeAsync(4_999);
    expect(fetchMock).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock).toHaveBeenCalledTimes(2);

    await vi.advanceTimersByTimeAsync(9_999);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1);
    expect(fetchMock).toHaveBeenCalledTimes(3);

    await vi.advanceTimersByTimeAsync(20_000);
    expect(fetchMock).toHaveBeenCalledTimes(4);

    await vi.advanceTimersByTimeAsync(30_000);
    expect(fetchMock).toHaveBeenCalledTimes(5);
    expect((await read).status).toBe(200);
  });

  it("keeps one retry loop for the whole page, not one per read", async () => {
    vi.useFakeTimers();
    setActiveSource(SOURCE);
    let attempts = 0;
    const fetchMock = vi.fn(async () => {
      attempts += 1;
      return attempts <= 2 ? busy(5) : answer({});
    });
    vi.stubGlobal("fetch", fetchMock);

    const first = graphFetch("/api/sidebar");
    const second = graphFetch("/api/v1/full-graph");

    await vi.advanceTimersByTimeAsync(4_999);
    expect(fetchMock).toHaveBeenCalledTimes(2);
    await vi.advanceTimersByTimeAsync(1);
    await vi.advanceTimersByTimeAsync(0);
    expect(fetchMock).toHaveBeenCalledTimes(4);  // both reads retried on the same pause

    await Promise.all([first, second]);
    expect(fetchMock).toHaveBeenCalledTimes(4);
  });
});
