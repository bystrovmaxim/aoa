// src/lib/historyAddress.ts
/**
 * History addresses — tell a history's address from a graph's, split off its key, and hide the key.
 *
 * The address field takes three kinds of address, each one full URL (spec 037, FR-001): a private
 * history (its port's history URL with the read key after ``#key=``), a public history (a GitHub link
 * to a graph file), and anything else — a running service or a graph-json address. The rules are the
 * server's (``maxitor.web.model.core.history_address``), so the two never disagree on what a history is.
 *
 * Wherever an address is shown, its key is eight dots, whatever its length (FR-010).
 */

/** What stands for a key wherever an address is shown. */
export const KEY_DOTS = "••••••••";

const PORT_PATH = /^(.*)\/api\/v1\/history\/([^/]+)\/?$/;
const GITHUB_PATH = /^\/([^/]+)\/([^/]+)\/blob\/([^/]+)\/(.+[^/])$/;

/** A private history: its port, its id, the key that opens it, and its name (the address without the key). */
export type PrivateHistory = { kind: "private"; port: string; id: string; key: string; name: string; title: string };

/** A public history: a GitHub link to its graph file, with its version file when given; together they are its name. */
export type PublicHistory = { kind: "public"; link: string; name: string; title: string; versionLink?: string; versionKey?: string };

export type History = PrivateHistory | PublicHistory;

/** An address that looks like a history but is out of shape; the message names what is wrong, never the address. */
export class HistoryAddressError extends Error {}

/** The version file of a public address; any other query is refused, the same as the server's. */
function versionParameters(query: URLSearchParams): { versionLink: string | null; versionKey: string | null } {
  const names = [...query.keys()];
  const known = names.every((name) => name === "version_link" || name === "version_key");
  if (!known || new Set(names).size !== names.length || [...query.values()].some((value) => !value)) {
    throw new HistoryAddressError("A public history's link takes only one 'version_link=' and one 'version_key=' in its query.");
  }
  const versionLink = query.get("version_link");
  const versionKey = query.get("version_key");
  if (versionKey && !versionLink) throw new HistoryAddressError("'version_key=' names a key of the file in 'version_link=', so it needs one.");
  return { versionLink, versionKey };
}

/**
 * The history an address names, ``null`` for a service or graph-json address; throws
 * ``HistoryAddressError`` for a history's address out of shape.
 */
export function parseHistory(address: string): History | null {
  const text = address.trim();
  if ((text.match(/#/g) ?? []).length > 1) {
    throw new HistoryAddressError("The address has more than one '#'; a history's key follows a single '#key='.");
  }
  const [base, fragment = ""] = text.split("#", 2);
  let url: URL;
  try {
    url = new URL(base);
  } catch {
    return null;
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") return null;
  if (url.hostname === "github.com") {
    const linked = GITHUB_PATH.exec(url.pathname);
    if (fragment || !linked) {
      throw new HistoryAddressError("A public history is a GitHub link to a graph file: https://github.com/<owner>/<repo>/blob/<branch>/<path>.");
    }
    const link = `https://github.com${url.pathname}`;
    const { versionLink, versionKey } = versionParameters(url.searchParams);
    const title = `${linked[1]}/${linked[2]}`;
    if (!versionLink) return { kind: "public", link, name: link, title };
    const query = [`version_link=${encodeURIComponent(versionLink)}`, ...(versionKey ? [`version_key=${encodeURIComponent(versionKey)}`] : [])].join("&");
    return { kind: "public", link, name: `${link}?${query}`, title, versionLink, ...(versionKey ? { versionKey } : {}) };
  }
  const named = PORT_PATH.exec(url.pathname);
  if (!named) return null;
  const key = fragment.startsWith("key=") ? fragment.slice("key=".length).trim() : "";
  if (url.search) throw new HistoryAddressError("A history's address carries no query; give the port's history URL and '#key=<key>'.");
  if (!key) throw new HistoryAddressError("A private history's address needs its read key after '#key='.");
  const port = `${url.protocol}//${url.host}${named[1]}`;
  const id = decodeURIComponent(named[2]);
  return { kind: "private", port, id, key, name: `${port}/api/v1/history/${named[2]}`, title: id };
}

/** ``address`` with its key, if it has one, shown as eight dots; everything else stays readable. */
export function mask(address: string): string {
  const at = address.indexOf("#key=");
  return at < 0 ? address : `${address.slice(0, at)}#key=${KEY_DOTS}`;
}

/** ``link`` carrying ``key`` after ``#key=``: what **Copy link** and a room's link hand out. */
export function withKey(link: string, key: string): string {
  return key ? `${link.split("#", 1)[0]}#key=${key}` : link;
}
