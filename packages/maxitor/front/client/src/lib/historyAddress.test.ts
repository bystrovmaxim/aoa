// src/lib/historyAddress.test.ts
import { describe, expect, it } from "vitest";
import { HistoryAddressError, KEY_DOTS, mask, parseHistory, withKey } from "./historyAddress";

const PORT = "https://repo-graph-port.aoa.run";

describe("a history's address", () => {
  it("names a private history by its port and id, and holds its key apart from its name", () => {
    const history = parseHistory(`${PORT}/api/v1/history/orders#key= abc-123 `);
    expect(history).toEqual({ kind: "private", port: PORT, id: "orders", key: "abc-123", name: `${PORT}/api/v1/history/orders`, title: "orders" });
  });

  it("names a public history by its GitHub link", () => {
    expect(parseHistory("https://github.com/owner/repo/blob/main/graph.json")).toEqual({
      kind: "public",
      link: "https://github.com/owner/repo/blob/main/graph.json",
      name: "https://github.com/owner/repo/blob/main/graph.json",
      title: "owner/repo",
    });
  });

  it("leaves a service or graph-json address alone", () => {
    for (const address of ["http://127.0.0.1:8001", "https://dev.demo.aoa.run/examples/model/graph-json", "demo:8100"]) {
      expect(parseHistory(address)).toBeNull();
    }
  });

  it("refuses a history's address out of shape, without echoing it", () => {
    const cases = [`${PORT}/api/v1/history/orders`, `${PORT}/api/v1/history/orders#key=a#b`, "https://github.com/owner/repo", `${PORT}/api/v1/history/orders?x=1#key=a`];
    for (const address of cases) {
      expect(() => parseHistory(address)).toThrow(HistoryAddressError);
      try {
        parseHistory(address);
      } catch (error) {
        expect((error as Error).message).not.toContain("orders");
      }
    }
  });
});

describe("a key shown", () => {
  it("is eight dots whatever its length, the rest readable", () => {
    for (const length of [8, 43, 100]) {
      const shown = mask(`${PORT}/api/v1/history/orders#key=${"k".repeat(length)}`);
      expect(shown).toBe(`${PORT}/api/v1/history/orders#key=${KEY_DOTS}`);
      expect(KEY_DOTS).toHaveLength(8);
    }
  });

  it("leaves an address with no key as it is", () => {
    expect(mask("https://github.com/owner/repo/blob/main/graph.json")).toBe("https://github.com/owner/repo/blob/main/graph.json");
  });

  it("is carried whole by a copied link", () => {
    expect(withKey("https://maxitor.example/?history=h&b=abc#old", "the-key")).toBe("https://maxitor.example/?history=h&b=abc#key=the-key");
  });
});
