// src/api/client.test.ts
import { afterEach, describe, expect, it } from "vitest";
import { graphApiUrl, setActiveSource } from "@/api/client";
import { readUrlDeepLink } from "@/lib/urlState";

const SOURCE = "https://service.test/graph-json";

/** Decode the query string the way the server does (``parse_qsl``: ``+`` is a space). */
function search(url: string): URLSearchParams {
  return new URLSearchParams(url.slice(url.indexOf("?") + 1));
}

afterEach(() => setActiveSource(null));

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
