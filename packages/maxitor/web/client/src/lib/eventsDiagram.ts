// src/lib/eventsDiagram.ts
/**
 * The events diagram (spec 053): its DOT text, and in Diff the union of A's and B's diagram, each element marked with
 * what the comparison says. An event one of whose fields changed is marked changed.
 */
import { getActiveBase } from "@/api/client";
import { compareVersions, type CompareResult, type DiffStatus } from "@/api/compare";
import { listDomains } from "@/api/erd";
import { fetchDomainEventsDiagram } from "@/api/domainEventsDiagram";
import type { DiagramCounts } from "@/lib/erdDiff";
import { MARK_LOOK, type CardTarget } from "@/lib/erdDiffCard";
import { drawnOn, type Side } from "@/lib/half";
import type { GraphvizChange } from "@/lib/useGraphvizChangeStepping";
import type { DomainEventsDiagramPayload, EventBand, EventWire } from "@/model/domainEventsDiagram";

/** A band's words on the diagram. */
export const BAND_TITLES: Record<EventBand, string> = { in_vocabulary: "In vocabulary", not_emitted: "Not emitted", emitted: "Emitted" };

/** What the frame says of a domain's vocabulary; nothing on the diagram of all domains. */
export function vocabularyLabel(domain: DomainEventsDiagramPayload["domain"]): string {
  if (domain.typed_events === null) return "";
  const now = domain.typed_events ? "Vocabulary" : "No vocabulary";
  return domain.typed_events_was === undefined ? now : `${now} (was ${domain.typed_events_was ? "Vocabulary" : "No vocabulary"})`;
}

/** Each element of two lists once, B's where both have it; sorted, so a pair has one DOT text. */
function union<T extends { id: string }>(older: readonly T[], newer: readonly T[]): T[] {
  const byId = new Map(older.map((element) => [element.id, element]));
  for (const element of newer) byId.set(element.id, element);
  return [...byId.values()].sort((one, other) => (one.id < other.id ? -1 : one.id > other.id ? 1 : 0));
}

/** The union of a diagram in A and in B; a domain only one version has comes from that one. */
export function mergeEventsDiagrams(older: DomainEventsDiagramPayload | null, newer: DomainEventsDiagramPayload | null): DomainEventsDiagramPayload {
  const domain = (newer ?? older)?.domain;
  if (!domain) throw new Error("Neither version has this domain.");
  const was = older?.domain.typed_events;
  return {
    domain: older && newer && was !== domain.typed_events && typeof was === "boolean" ? { ...domain, typed_events_was: was } : domain,
    actions: union(older?.actions ?? [], newer?.actions ?? []),
    methods: union(older?.methods ?? [], newer?.methods ?? []),
    events: union(older?.events ?? [], newer?.events ?? []),
    edges: union(older?.edges ?? [], newer?.edges ?? []),
  };
}

/** Whether a field of ``event`` changed: fields are nodes of their own, named ``<event>:<field>``. */
function fieldChanged(event: EventWire, compared: CompareResult): boolean {
  return Object.entries(compared.nodes).some(([id, status]) => id.startsWith(`${event.id}:`) && Boolean(status));
}

/** Every drawn element marked with its status. */
export function markEventsDiagram(diagram: DomainEventsDiagramPayload, compared: CompareResult): DomainEventsDiagramPayload {
  const node = (id: string): DiffStatus => compared.nodes[id] ?? "unchanged";
  return {
    ...diagram,
    actions: diagram.actions.map((action) => ({ ...action, diff: node(action.id) })),
    methods: diagram.methods.map((method) => ({ ...method, diff: node(method.id) })),
    events: diagram.events.map((event) => {
      const own = node(event.id);
      return { ...event, diff: own === "unchanged" && fieldChanged(event, compared) ? "changed" : own };
    }),
    edges: diagram.edges.map((edge) => ({ ...edge, diff: compared.edges[edge.id] ?? "unchanged" })),
  };
}

/** The marked events and links: what a comparison of events counts. */
function marked(diagram: DomainEventsDiagramPayload): { id: string; diff: Exclude<DiffStatus, "unchanged"> }[] {
  return [...diagram.events, ...diagram.edges.filter((edge) => edge.edge_kind === "emits")].flatMap((element) => (element.diff && element.diff !== "unchanged" ? [{ id: element.id, diff: element.diff }] : []));
}

export function eventsCounts(diagram: DomainEventsDiagramPayload): DiagramCounts {
  const counts: DiagramCounts = { added: 0, removed: 0, changed: 0 };
  for (const element of marked(diagram)) counts[element.diff] += 1;
  return counts;
}

/** The same diagram's part one version has (spec 044): a link goes with its ends. */
export function eventsOfSide(diagram: DomainEventsDiagramPayload, side: Side): DomainEventsDiagramPayload {
  const drawn = <E extends { diff?: DiffStatus }>(list: readonly E[]) => list.filter((each) => drawnOn(side, each.diff ?? "unchanged"));
  const edges = drawn(diagram.edges);
  const methods = drawn(diagram.methods).filter((method) => edges.some((edge) => edge.source_id === method.id));
  const actions = drawn(diagram.actions).filter((action) => methods.some((method) => method.action_id === action.id));
  return { ...diagram, actions, methods, events: drawn(diagram.events), edges: edges.filter((edge) => edge.edge_kind === "emits" || methods.some((method) => method.id === edge.target_id)) };
}

/** Hide the domains switched off, and the kinds of change switched off, with what hangs on them. */
export function filterEvents(diagram: DomainEventsDiagramPayload, domains: ReadonlySet<string> | null, offChanges: ReadonlySet<string>): DomainEventsDiagramPayload {
  const kept = (element: { diff?: DiffStatus }) => !element.diff || !offChanges.has(element.diff);
  const actions = diagram.actions.filter((action) => kept(action) && (!domains || domains.has(action.domain_id)));
  const here = new Set(actions.map((action) => action.id));
  const methods = diagram.methods.filter((method) => kept(method) && here.has(method.action_id));
  const ids = new Set([...actions, ...methods].map((element) => element.id));
  const edges = diagram.edges.filter((edge) => kept(edge) && ids.has(edge.source_id));
  const linked = new Set(edges.map((edge) => edge.target_id));
  const all = domains === null;
  const events = diagram.events.filter((event) => kept(event) && (all || linked.has(event.id) || event.domains.some((domain) => domains.has(domain.id))));
  const shown = new Set(events.map((event) => event.id));
  return { ...diagram, actions, methods, events, edges: edges.filter((edge) => edge.edge_kind === "method" || shown.has(edge.target_id)) };
}

/** A node's id in the DOT text: a stable word, whatever the element's id holds. */
export function eventsDotId(kind: "a" | "m" | "e", id: string): string {
  return `${kind}_${[...id].map((char) => (/[A-Za-z0-9]/.test(char) ? char : `_${char.charCodeAt(0).toString(16)}_`)).join("")}`;
}

function esc(text: string): string {
  return text.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
}

/** The fill and line of a marked node. */
function look(diff: DiffStatus | undefined): string {
  return diff && diff !== "unchanged" ? ` color="${MARK_LOOK[diff].colour}" penwidth=2` : "";
}

/** The cell of a marked element, which the steps through changes centre. */
export function eventsCellId(id: string): string {
  return `ev_${eventsDotId("e", id)}`;
}

/** The DOT text of a diagram; ``icon`` gives a node type's picture, which the caller hands Graphviz too. */
export function buildEventsDot(diagram: DomainEventsDiagramPayload, rankdir: "LR" | "TB", boundary: boolean, icon: (kind: string) => string): string {
  const lines = ["digraph events {", `  graph [rankdir=${rankdir}, bgcolor=transparent, nodesep=0.22, ranksep=0.8, fontname="Inter, Helvetica, sans-serif"];`, '  node [fontname="Inter, Helvetica, sans-serif", fontsize=11];', '  edge [color="#94a3b8", arrowsize=0.7];'];
  const row = (kind: string, text: string) => `<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="4" CELLPADDING="0"><TR><TD FIXEDSIZE="TRUE" WIDTH="16" HEIGHT="16"><IMG SRC="${icon(kind)}"/></TD><TD>${esc(text)}</TD></TR></TABLE>>`;
  const body: string[] = [];
  for (const action of diagram.actions) {
    body.push(`${eventsDotId("a", action.id)} [id="${eventsCellId(action.id)}" shape=box style="rounded,filled" fillcolor="#ffffff" color="${action.accent_color}" label=${row("Action", action.short_label || action.label)}${look(action.diff)}];`);
  }
  for (const method of diagram.methods) {
    body.push(`${eventsDotId("m", method.id)} [id="${eventsCellId(method.id)}" shape=box style="rounded,filled" fillcolor="#f8fafc" color="#cbd5e1" label=${row(method.kind, method.label)}${look(method.diff)}];`);
  }
  for (const band of Object.keys(BAND_TITLES) as EventBand[]) {
    const events = diagram.events.filter((event) => event.band === band);
    if (events.length === 0) continue;
    body.push(`subgraph cluster_${band} {`, `label="${BAND_TITLES[band]}"; fontsize=11; fontcolor="#64748b"; style="rounded,dashed"; color="#cbd5e1";`);
    for (const event of events) body.push(`${eventsDotId("e", event.id)} [id="${eventsCellId(event.id)}" shape=box style="rounded,filled" fillcolor="#fffbeb" color="#d97706" label=${row("Event", event.label)}${look(event.diff)}];`);
    body.push("}");
  }
  if (boundary) {
    const label = [diagram.domain.short_label, vocabularyLabel(diagram.domain)].filter(Boolean).join(" · ");
    lines.push("  subgraph cluster_scope {", `label="${esc(label)}"; labeljust=l; fontsize=13; style=rounded; color="#64748b";`, ...body, "}");
  } else lines.push(...body);
  for (const edge of diagram.edges) {
    const [from, to] = edge.edge_kind === "method" ? [eventsDotId("a", edge.source_id), eventsDotId("m", edge.target_id)] : [eventsDotId("m", edge.source_id), eventsDotId("e", edge.target_id)];
    const style = edge.edge_kind === "method" ? " style=dashed arrowhead=none" : "";
    lines.push(`  ${from} -> ${to} [id="${eventsCellId(edge.id)}"${style}${look(edge.diff)}];`);
  }
  lines.push("}");
  return lines.join("\n");
}

/** The node under a Graphviz title, as a kind and an element. */
export function eventAtTitle(diagram: DomainEventsDiagramPayload, title: string): EventWire | null {
  return diagram.events.find((event) => eventsDotId("e", event.id) === title) ?? null;
}

/** The card of a marked event or link, or ``null``. */
export function eventsCard(diagram: DomainEventsDiagramPayload, id: string): CardTarget | null {
  const event = diagram.events.find((each) => each.id === id);
  if (event?.diff && event.diff !== "unchanged") return { title: event.label, status: event.diff, elements: [{ kind: "node", id }] };
  const edge = diagram.edges.find((each) => each.id === id);
  if (edge?.diff && edge.diff !== "unchanged") return { title: `${edge.source_id.split(/[.:]/).pop()} → ${edge.target_id.split(".").pop()}`, status: edge.diff, elements: [{ kind: "edge", id }] };
  return null;
}

/** Every change the steps walk: events, then links. */
export function eventsChanges(diagram: DomainEventsDiagramPayload): GraphvizChange[] {
  return marked(diagram).flatMap(({ id, diff }) => {
    const card = eventsCard(diagram, id);
    const event = diagram.events.some((each) => each.id === id);
    return card ? [{ key: id, title: card.title, detail: event ? "Event" : "Emits", status: diff, group: event ? "Events" : "Links", cell: eventsCellId(id), card }] : [];
  });
}

/** A domain's events, or all of them, in the pair being compared, read from each version that has the domain. */
export async function loadEventsDiff(domainId: string | null): Promise<DomainEventsDiagramPayload> {
  const base = getActiveBase();
  if (!base) throw new Error("No two versions to compare.");
  const [newerListing, olderListing, compared] = await Promise.all([listDomains(), listDomains(base), compareVersions()]);
  const has = (listing: typeof newerListing) => domainId === null || listing.list_domains.some((row) => row.qualname === domainId);
  const [newer, older] = await Promise.all([has(newerListing) ? fetchDomainEventsDiagram(domainId) : null, has(olderListing) ? fetchDomainEventsDiagram(domainId, base) : null]);
  return markEventsDiagram(mergeEventsDiagrams(older, newer), compared);
}
