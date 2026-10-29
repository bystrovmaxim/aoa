// src/components/history/VersionMessage/VersionMessage.test.tsx
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import type { HistoryVersion } from "@/api/history";
import { liveLine } from "@/lib/liveLine";
import { MESSAGE_LINES, messageOf, VersionMessage } from "./VersionMessage";

afterEach(cleanup);

function version(extra: Partial<HistoryVersion>): HistoryVersion {
  return { sha: "a".repeat(40), date: "2026-10-30T10:00:00Z", tags: [], nodes: 1, edges: 1, source: "s", ...extra };
}

describe("the chosen version's message (FR-028 – FR-030)", () => {
  it("is the pull request's title and body, whole, with nothing above it", () => {
    render(<VersionMessage version={version({ pr: { number: 7, title: "Offer regions", body: "Model\n- a list\n- of regions", url: "" } })} repository="o/r" />);
    expect(screen.getByTestId("message").textContent).toBe("Offer regions\n\nModel\n- a list\n- of regions");
  });

  it("is the commit's message when there was no pull request", () => {
    expect(messageOf(version({ message: "Direct change\n\nwith a body" }))).toBe("Direct change\n\nwith a body");
  });

  it("draws Markdown and HTML as typed text, and only addresses and #n as links that open apart", () => {
    const body = "## Heading\n**bold**\n<script>window.hacked = true</script>\njavascript:alert(1)\nhttps://example.com/a and #142";
    render(<VersionMessage version={version({ pr: { number: 1, title: "T", body, url: "" } })} repository="o/r" />);
    const box = screen.getByTestId("message");
    expect(box.querySelector("script")).toBeNull();
    expect(box.querySelector("h2, strong")).toBeNull();
    expect(box.textContent).toContain("<script>window.hacked = true</script>");
    const anchors = [...box.querySelectorAll("a")];
    expect(anchors.map((a) => [a.textContent, a.getAttribute("href"), a.getAttribute("target"), a.getAttribute("rel")])).toEqual([
      ["https://example.com/a", "https://example.com/a", "_blank", "noopener noreferrer"],
      ["#142", "https://github.com/o/r/pull/142", "_blank", "noopener noreferrer"],
    ]);
  });

  it("stops at nine lines and scrolls inside, wrapping long lines by words, its text selectable", () => {
    render(<VersionMessage version={version({ message: Array.from({ length: 40 }, (_, i) => `line ${i}`).join("\n") })} repository={null} />);
    const style = getComputedStyle(screen.getByTestId("message"));
    expect(style.maxHeight).toBe(`${MESSAGE_LINES * 18 + 16}px`);
    expect(style.overflowY).toBe("auto");
    expect(style.whiteSpace).toBe("pre-wrap");
    expect(style.userSelect).toBe("text");
  });
});

describe("Live's closing line", () => {
  const versions = [version({ sha: `1${"a".repeat(39)}`, pr: { number: 3, title: "", body: "", url: "" }, date: "2026-10-29T00:00:00Z" })];
  const now = Date.parse("2026-10-30T12:00:00Z");

  it("says when Live was checked and the newest version (M4, M5)", () => {
    expect(liveLine(versions, { ok: true, at: now - 12_000 }, now)).toBe("checked 12 s ago · newest version #3, 2026-10-29");
  });

  it("leaves the newest version out when there is none (M6)", () => {
    expect(liveLine([], { ok: true, at: now - 120_000 }, now)).toBe("checked 2 min ago");
  });

  it("says since when Live cannot be reached", () => {
    expect(liveLine(versions, { ok: false, at: now }, now)).toMatch(/^cannot be reached since /);
  });

  it("stands in for the message of Live", () => {
    render(<VersionMessage version={null} repository="o/r" liveLine="checked 3 s ago" />);
    expect(screen.getByTestId("live-line").textContent).toBe("Livechecked 3 s ago");
    expect(screen.queryByTestId("message")).toBeNull();
  });
});
