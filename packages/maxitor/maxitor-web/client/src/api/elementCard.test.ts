import { beforeEach, describe, expect, it, vi } from "vitest";

const graphFetch = vi.fn();
const getActiveBase = vi.fn();
vi.mock("@/api/client", () => ({ graphFetch, getActiveBase, getActiveSource: () => "b" }));

const { fetchElementCard, forgetElementCards } = await import("@/api/elementCard");

const answer = (status: number, body: unknown = {}) => ({ status, ok: status < 400, json: async () => body });

describe("fetchElementCard", () => {
  beforeEach(() => {
    forgetElementCards();
    graphFetch.mockReset();
    getActiveBase.mockReset().mockReturnValue(null);
  });

  it("reads a node once", async () => {
    graphFetch.mockResolvedValue(answer(200, { id: "n" }));
    await fetchElementCard("n");
    await fetchElementCard("n");
    expect(graphFetch).toHaveBeenCalledTimes(1);
  });

  it("asks the older version for what the shown one does not hold", async () => {
    const base = { source: "a", key: "" };
    getActiveBase.mockReturnValue(base);
    graphFetch.mockResolvedValueOnce(answer(404)).mockResolvedValueOnce(answer(200, { id: "n" }));
    expect(await fetchElementCard("n")).toEqual({ id: "n" });
    expect(graphFetch.mock.calls[1]?.[2]).toBe(base);
  });

  it("does not keep a failed read", async () => {
    graphFetch.mockResolvedValueOnce(answer(500));
    await expect(fetchElementCard("n")).rejects.toThrow();
    graphFetch.mockResolvedValueOnce(answer(200, { id: "n" }));
    await expect(fetchElementCard("n")).resolves.toEqual({ id: "n" });
  });
});
