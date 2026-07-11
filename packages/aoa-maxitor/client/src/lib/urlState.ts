// src/lib/urlState.ts
import type { DiagramSelection } from "@/model/diagramSelection";

const PARAM_SOURCE = "source";
const PARAM_VIEW = "view";
const PARAM_DOMAIN = "domain";
const PARAM_NODE = "node";
const PARAM_HOST = "host";

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
};

export function readUrlDeepLink(): UrlDeepLink {
  const params = new URLSearchParams(window.location.search);
  return {
    source: params.get(PARAM_SOURCE),
    view: params.get(PARAM_VIEW),
    domain: params.get(PARAM_DOMAIN),
    node: params.get(PARAM_NODE),
    host: params.get(PARAM_HOST),
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

function selectionToParams(sel: DiagramSelection): Record<string, string> {
  const view = VIEW_SLUG_BY_KIND[sel.kind];
  if (sel.kind === "erd") return sel.qualifier ? { view, domain: sel.qualifier } : { view };
  if (sel.kind === "use_case") return { view, domain: sel.domain_qualifier };
  if (sel.kind === "lifecycle_fsm") return { view, node: sel.lifecycle_graph_node_id, host: sel.host_entity_interchange_id };
  return { view };
}

function buildUrl(serviceUrl: string | null, selection: DiagramSelection | null): string {
  const params = new URLSearchParams();
  if (serviceUrl) params.set(PARAM_SOURCE, serviceUrl);
  if (selection) {
    for (const [k, v] of Object.entries(selectionToParams(selection))) params.set(k, v);
  }
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
export function pushUrlState(serviceUrl: string | null, selection: DiagramSelection | null): void {
  window.history.pushState(null, "", buildUrl(serviceUrl, selection));
}
