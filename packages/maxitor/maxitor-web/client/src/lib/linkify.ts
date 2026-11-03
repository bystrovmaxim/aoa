// src/lib/linkify.ts
/**
 * A version's message as plain text with two kinds of links (spec 037, FR-028a, research R12).
 *
 * Markdown and HTML are never rendered: the message is split into text and links, which the page
 * draws as text nodes and anchors — nothing is ever set as HTML. Only ``http://`` and ``https://``
 * addresses become links (trailing punctuation and an unbalanced closing bracket left out), and
 * ``#<number>``, which points at that pull request of the history's own GitHub repository. Every
 * other scheme and ``owner/repo#<number>`` stay text.
 */

/** A run of the message: text as typed, or a link with the text it shows. */
export type MessagePart = { kind: "text"; text: string } | { kind: "link"; text: string; href: string };

const TOKEN = /https?:\/\/[^\s<>"]+|#\d+/g;
const TRAILING = /[.,;:!?'"]+$/;

/** Trim what is not part of an address: trailing punctuation, then closing brackets with no opening one. */
function trimAddress(raw: string): string {
  let address = raw.replace(TRAILING, "");
  for (const [open, close] of [["(", ")"], ["[", "]"], ["{", "}"]] as const) {
    while (address.endsWith(close) && address.split(close).length > address.split(open).length) {
      address = address.slice(0, -1).replace(TRAILING, "");
    }
  }
  return address;
}

/**
 * ``text`` split into parts; ``#n`` links to ``https://github.com/<repository>/pull/n`` only when
 * ``repository`` is given (a GitHub history).
 */
export function linkify(text: string, repository: string | null): MessagePart[] {
  const parts: MessagePart[] = [];
  let last = 0;
  const push = (kind: "text", value: string) => {
    if (!value) return;
    const previous = parts.at(-1);
    if (previous?.kind === kind) previous.text += value;
    else parts.push({ kind, text: value });
  };
  for (const match of text.matchAll(TOKEN)) {
    const at = match.index ?? 0;
    const raw = match[0];
    if (raw.startsWith("#")) {
      const before = at > 0 ? text[at - 1] : "";
      if (!repository || /[\w/]/.test(before)) continue;
      push("text", text.slice(last, at));
      parts.push({ kind: "link", text: raw, href: `https://github.com/${repository}/pull/${raw.slice(1)}` });
      last = at + raw.length;
      continue;
    }
    const address = trimAddress(raw);
    push("text", text.slice(last, at));
    parts.push({ kind: "link", text: address, href: address });
    last = at + address.length;
  }
  push("text", text.slice(last));
  return parts;
}
