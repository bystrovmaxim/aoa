// src/lib/urlState.ts
import { withKey } from "@/lib/historyAddress";
import { keyFor } from "@/lib/historyKey";
import type { DiagramSelection } from "@/model/diagramSelection";

const PARAM_SOURCE = "source";
const PARAM_VIEW = "view";
const PARAM_DOMAIN = "domain";
const PARAM_NODE = "node";
const PARAM_HOST = "host";
const PARAM_ROOM = "room";
const PARAM_HISTORY = "history";
const PARAM_VERSION = "b";

/**
 * The history this tab shows and its version, or ``null``. While one is set, every address this
 * module writes names it as ``history`` and ``b`` in place of ``source``, and never its key (spec 037, FR-022).
 */
let currentHistory: { name: string; b: string | null } | null = null;

/** Name the history and version every later address carries, or ``null`` for a plain source. */
export function setUrlHistory(history: { name: string; b: string | null } | null): void {
  currentHistory = history;
}

/**
 * The room this tab is in, or ``null``. Kept here rather than passed to every navigation, so that
 * each address this module writes keeps ``room`` while the tab is in one (spec 028, FR-017).
 */
let currentRoom: string | null = null;

/** Deep-link slugs for ``view=`` — kept in sync with the aoa.run marketing site's "Try Maxitor" links. */
const VIEW_SLUG_BY_KIND: Record<DiagramSelection["kind"], string> = {
  interchange_graph: "full-graph",
  erd: "domain-erd",
  use_case: "use-case",
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
  /** The version the address names: a short sha, ``live``, or ``null``. */
  b?: string | null;
};

export function readUrlDeepLink(): UrlDeepLink {
  const params = new URLSearchParams(window.location.search);
  return {
    source: params.get(PARAM_SOURCE),
    view: params.get(PARAM_VIEW),
    domain: params.get(PARAM_DOMAIN),
    node: params.get(PARAM_NODE),
    host: params.get(PARAM_HOST),
    room: params.get(PARAM_ROOM),
    history: params.get(PARAM_HISTORY),
    b: params.get(PARAM_VERSION),
  };
}

/** Fully-specified selections resolve without sidebar data (``erd`` with no ``domain`` means "all domains"). */
export function deepLinkToSelection(link: UrlDeepLink): DiagramSelection | null {
  if (link.view === "full-graph") return { kind: "interchange_graph" };
  if (link.view === "domain-erd") return { kind: "erd", qualifier: link.domain };
  if (link.view === "use-case" && link.domain) return { kind: "use_case", domain_qualifier: link.domain };
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
    if (currentHistory.b) params.set(PARAM_VERSION, currentHistory.b);
  } else if (serviceUrl) params.set(PARAM_SOURCE, serviceUrl);
  if (selection) {
    for (const [k, v] of Object.entries(selectionToParams(selection))) params.set(k, v);
  }
  if (currentRoom) params.set(PARAM_ROOM, currentRoom);
  const qs = params.toString();
  return qs ? `${window.location.pathname}?${qs}` : window.location.pathname;
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
  window.history.replaceState(null, "", `${url.pathname}${url.search}`);
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
