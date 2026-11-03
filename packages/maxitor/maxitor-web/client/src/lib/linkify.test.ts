// src/lib/linkify.test.ts
import { describe, expect, it } from "vitest";
import { linkify } from "./linkify";

const links = (text: string, repository: string | null = "owner/service") =>
  linkify(text, repository)
    .filter((part) => part.kind === "link")
    .map((part) => (part.kind === "link" ? [part.text, part.href] : []));

describe("a message as plain text with two kinds of links (FR-028a)", () => {
  it("keeps Markdown, HTML and other schemes as typed text", () => {
    const text = "## Heading\n**bold** <script>alert(1)</script> javascript:alert(1) mailto:a@b";
    expect(linkify(text, "owner/service")).toEqual([{ kind: "text", text }]);
  });

  it("links an http(s) address, leaving trailing punctuation and an unbalanced bracket out", () => {
    expect(links("See https://example.com/a). Then http://x.test/b?c=1, done")).toEqual([
      ["https://example.com/a", "https://example.com/a"],
      ["http://x.test/b?c=1", "http://x.test/b?c=1"],
    ]);
    expect(links("(https://example.com/wiki/A_(b))")).toEqual([["https://example.com/wiki/A_(b)", "https://example.com/wiki/A_(b)"]]);
  });

  it("links #n to that pull request of the history's repository, and nothing else that looks like it", () => {
    expect(links("Fixes #142 and owner/repo#5 and a#7")).toEqual([["#142", "https://github.com/owner/service/pull/142"]]);
  });

  it("links no #n for a history that is not on GitHub", () => {
    expect(links("Fixes #142", null)).toEqual([]);
  });

  it("keeps every character of the message, in order", () => {
    const text = "Line one https://example.com/x.\n\n#3 and more";
    expect(linkify(text, "o/r").map((part) => part.text).join("")).toBe(text);
  });
});
