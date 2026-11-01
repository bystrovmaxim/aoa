// src/lib/urlState.ts
import { withKey } from "@/lib/historyAddress";
import { keyFor } from "@/lib/historyKey";
import type { DiagramSelection } from "@/model/diagramSelection";
import { VIEW_PARAMS } from "@/lib/viewUrl";

const PARAM_SOURCE = "source";
const PARAM_VIEW = "view";
const PARAM_DOMAIN = "domain";
const PARAM_NODE = "node";
const PARAM_HOST = "host";
const PARAM_ROOM = "room";
const PARAM_HISTORY = "history";
const PARAM_VERSION = "b";
const PARAM_OLDER = "a";
const PARAM_MODE = "mode";

/**
 * The history this tab shows and its version, or ``null``. While one is set, every address this
 * module writes names it as ``history`` and ``b`` in place of ``source``, and never its key (spec 037, FR-022);
 * in Diff also ``mode=diff`` and ``a``, the older version (spec 038, FR-014); in Side by side ``mode=split`` and ``a`` (spec 044).
 */
let currentHistory: { name: string; b: string | null; a?: string | null; split?: boolean } | null = null;

/** Name the history and version — or, with ``a``, the two compared — every later address carries; ``null`` for a plain source. */
export function setUrlHistory(history: { name: string; b: string | null; a?: string | null; split?: boolean } | null): void {
  currentHistory = history;
}

/**
 * The room this tab is in, or ``null``. Kept here rather than passed to every navigation, so that
 * each address this module writes keeps ``room`` while the tab is in one (spec 028, FR-017).
 */
let currentRoom: string | null = null;

/**
 * The view of the page on screen — its filters, layout, modes and paint (``@/lib/viewUrl``) — that every address this
 * module writes carries, so a reload or a copied link shows the same picture (spec 038).
 */
let currentView: Record<string, string> = {};

/** Put the page's view into the address, keeping every other parameter, without a new entry in the browser's history. */
export function setUrlView(view: Record<string, string>): void {
  currentView = view;
  const url = new URL(window.location.href);
  for (const param of VIEW_PARAMS) url.searchParams.delete(param);
  for (const [param, value] of Object.entries(view)) url.searchParams.set(param, value);
  const next = withHistoryKey(`${url.pathname}${url.search}`);
  if (next !== `${window.location.pathname}${window.location.search}${window.location.hash}`) window.history.replaceState(null, "", next);
}

/** The parameters of the address the page was opened with. */
export function readUrlParams(): URLSearchParams {
  return new URLSearchParams(window.location.search);
}

/** Deep-link slugs for ``view=`` — kept in sync with the aoa.run marketing site's "Try Maxitor" links. */
const VIEW_SLUG_BY_KIND: Record<DiagramSelection["kind"], string> = {
  interchange_graph: "full-graph",
  erd: "domain-erd",
  use_case: "use-case",
  use_case_all: "use-case-all",
  lifecycle_fsm: "lifecycle-fsm",
};

export type UrlDeepLink = {
  source: string | null;
  view: string | null;
  domain: string | null;
  node: string | null;
  host: string | null;
  room: string | null;
  /** The history the address names, its address without a key, or ``null``. */
  history?: string | null;
  /** The version the address names: a short sha, ``live``, or ``null``. In Diff, B. */
  b?: string | null;
  /** In Diff or Side by side (``mode=diff``, ``mode=split``), A — the older version; ``null`` otherwise. */
  a?: string | null;
  /** Whether the address opens Side by side: ``mode=split`` with an ``a``. */
  split?: boolean;
};

export function readUrlDeepLink(): UrlDeepLink {
  const params = new URLSearchParams(window.location.search);
  const mode = params.get(PARAM_MODE);
  const older = mode === "diff" || mode === "split" ? params.get(PARAM_OLDER) : null;
  return {
    source: params.get(PARAM_SOURCE),
    view: params.get(PARAM_VIEW),
    domain: params.get(PARAM_DOMAIN),
    node: params.get(PARAM_NODE),
    host: params.get(PARAM_HOST),
    room: params.get(PARAM_ROOM),
    history: params.get(PARAM_HISTORY),
    b: params.get(PARAM_VERSION),
    a: older,
    split: mode === "split" && older !== null,
  };
}

/** Fully-specified selections resolve without sidebar data (``erd`` with no ``domain`` means "all domains"). */
export function deepLinkToSelection(link: UrlDeepLink): DiagramSelection | null {
  if (link.view === "full-graph") return { kind: "interchange_graph" };
  if (link.view === "domain-erd") return { kind: "erd", qualifier: link.domain };
  if (link.view === "use-case" && link.domain) return { kind: "use_case", domain_qualifier: link.domain };
  if (link.view === "use-case-all") return { kind: "use_case_all" };
  if (link.view === "lifecycle-fsm" && link.node && link.host) {
    return { kind: "lifecycle_fsm", lifecycle_graph_node_id: link.node, host_entity_interchange_id: link.host };
  }
  return null;
}

/** A ``view`` that named a kind needing a qualifier (domain / node+host) the URL didn't supply. */
export function deepLinkNeedsSidebarDefault(link: UrlDeepLink): "use_case" | "lifecycle_fsm" | null {
  if (link.view === "use-case" && !link.domain) return "use_case";
  if (link.view === "lifecycle-fsm" && !(link.node && link.host)) return "lifecycle_fsm";
  return null;
}

export function selectionToParams(sel: DiagramSelection): Record<string, string> {
  const view = VIEW_SLUG_BY_KIND[sel.kind];
  if (sel.kind === "erd") return sel.qualifier ? { view, domain: sel.qualifier } : { view };
  if (sel.kind === "use_case") return { view, domain: sel.domain_qualifier };
  if (sel.kind === "lifecycle_fsm") return { view, node: sel.lifecycle_graph_node_id, host: sel.host_entity_interchange_id };
  return { view };
}

function buildUrl(serviceUrl: string | null, selection: DiagramSelection | null): string {
  const params = new URLSearchParams();
  if (currentHistory) {
    params.set(PARAM_HISTORY, currentHistory.name);
    if (currentHistory.a && currentHistory.b) {
      params.set(PARAM_MODE, currentHistory.split ? "split" : "diff");
      params.set(PARAM_OLDER, currentHistory.a);
    }
    if (currentHistory.b) params.set(PARAM_VERSION, currentHistory.b);
  } else if (serviceUrl) params.set(PARAM_SOURCE, serviceUrl);
  if (selection) {
    for (const [k, v] of Object.entries(selectionToParams(selection))) params.set(k, v);
  }
  if (currentRoom) params.set(PARAM_ROOM, currentRoom);
  for (const [param, value] of Object.entries(currentView)) params.set(param, value);
  const qs = params.toString();
  return withHistoryKey(qs ? `${window.location.pathname}?${qs}` : window.location.pathname);
}

/**
 * ``address`` with the read key of the history it names after ``#key=``, when this tab holds one: the address
 * bar is the link to share, so copying it opens the same private history elsewhere (spec 037, FR-010a). No
 * browser sends what follows ``#`` to a server.
 */
function withHistoryKey(address: string): string {
  const history = new URL(address, window.location.origin).searchParams.get("history");
  return withKey(address, history ? keyFor(history) : "");
}

/**
 * Keeps the URL accurate as state resolves (e.g. a bare ``view=use-case`` deep link gaining
 * its ``domain=`` once the sidebar picks a default) — via ``replaceState``, so it never adds
 * a history entry on its own. Safe to call on every render; call after ``pushUrlState`` too,
 * it will just overwrite the entry that was just pushed with the same content.
 */
export function syncUrlToState(serviceUrl: string | null, selection: DiagramSelection | null): void {
  window.history.replaceState(null, "", buildUrl(serviceUrl, selection));
}

/**
 * Creates a back/forward-able checkpoint for a user-initiated navigation (sidebar click,
 * loading a service, switching service) — one entry per action, so the Back button steps
 * through them one at a time.
 */
export function pushUrlState(
  serviceUrl: string | null,
  selection: DiagramSelection | null,
  options: { replace?: boolean } = {},
): void {
  const url = buildUrl(serviceUrl, selection);
  if (options.replace) window.history.replaceState(null, "", url);
  else window.history.pushState(null, "", url);
}

/**
 * Put ``room`` into the address, or take it out with ``null``, keeping every other parameter.
 * Every later address this module writes keeps it until it is taken out.
 */
export function setUrlRoom(room: string | null): void {
  currentRoom = room;
  const url = new URL(window.location.href);
  if (room) url.searchParams.set(PARAM_ROOM, room);
  else url.searchParams.delete(PARAM_ROOM);
  window.history.replaceState(null, "", withHistoryKey(`${url.pathname}${url.search}`));
}

/**
 * ``href`` with ``room`` set: the link Copy link hands out is the page being looked at, in the room.
 * On a private history it also carries the tab's read key after ``#key=``, since that is what opens
 * the history elsewhere; it is shown with the key as dots (spec 037, FR-010).
 */
export function roomLink(href: string, room: string): string {
  const url = new URL(href);
  url.searchParams.set(PARAM_ROOM, room);
  url.hash = "";
  const history = url.searchParams.get("history");
  const key = history ? keyFor(history) : "";
  return withKey(url.toString(), key);
}
