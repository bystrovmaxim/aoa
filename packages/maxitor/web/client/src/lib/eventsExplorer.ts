// src/lib/eventsExplorer.ts
/**
 * The events explorer (spec 055): domains, events and actions as one graph, opened step by step through ports. A node
 * is ``<kind>:<id>``; a port is one kind of link of a node; the screen shows the first layer of the chosen mode and
 * everything an open port of a shown node leads to. Every rule of the screen lives here, so it is tested without a
 * browser; the viewer only draws what these functions give.
 */
import type { EventsExplorerPayload, ExplorerActionWire, ExplorerDomainWire, ExplorerEmitWire, ExplorerEventWire } from "@/model/eventsExplorer";

export type Kind = "domain" | "event" | "action";
export type Mode = "domains" | "events" | "actions";
export type PortKind = "events" | "actions" | "domains" | "domain";
export type Layout = "dot_lr" | "dot_tb";


export const PORTS: Record<Kind, PortKind[]> = { domain: ["events", "actions"], event: ["actions", "domains"], action: ["events", "domain"] };
/** The port a click on the node itself opens. */
export const MAIN_PORT: Record<Kind, PortKind> = { domain: "events", event: "actions", action: "events" };
export const PORT_TARGET: Record<PortKind, Kind> = { events: "event", actions: "action", domains: "domain", domain: "domain" };
export const ROOT_KIND: Record<Mode, Kind> = { domains: "domain", events: "event", actions: "action" };

export const ref = (kind: Kind, id: string) => `${kind}:${id}`;
export const kindOf = (node: string) => node.slice(0, node.indexOf(":")) as Kind;
export const idOf = (node: string) => node.slice(node.indexOf(":") + 1);
export const portKey = (node: string, port: PortKind) => `${node}>${port}`;

function add<K, V>(map: Map<K, Set<V>>, key: K, value: V) {
  const set = map.get(key) ?? new Set<V>();
  set.add(value);
  map.set(key, set);
}

export class EventsGraph {
  readonly domains = new Map<string, ExplorerDomainWire>();
  readonly actions = new Map<string, ExplorerActionWire>();
  readonly events = new Map<string, ExplorerEventWire>();
  readonly emits: ExplorerEmitWire[];
  /** A domain's vocabulary; a domain without one has no entry. */
  readonly vocabulary = new Map<string, Set<string>>();
  readonly holders = new Map<string, Set<string>>();
  readonly emitsOf = new Map<string, ExplorerEmitWire[]>();
  readonly emittersOf = new Map<string, ExplorerEmitWire[]>();
  readonly emittingActionsOf = new Map<string, Set<string>>();
  /** Every action of a domain, with events or without: what events do not cover shows too. */
  readonly actionsOf = new Map<string, Set<string>>();

  constructor(readonly payload: EventsExplorerPayload) {
    for (const domain of payload.domains) {
      this.domains.set(domain.id, domain);
      if (domain.vocabulary) this.vocabulary.set(domain.id, new Set());
    }
    for (const action of payload.actions) {
      this.actions.set(action.id, action);
      add(this.actionsOf, action.domain_id, action.id);
    }
    for (const event of payload.events) this.events.set(event.id, event);
    for (const { domain_id, event_id } of payload.holds) {
      add(this.vocabulary, domain_id, event_id);
      add(this.holders, event_id, domain_id);
    }
    this.emits = payload.emits;
    for (const emit of payload.emits) {
      this.emitsOf.set(emit.action_id, [...(this.emitsOf.get(emit.action_id) ?? []), emit]);
      this.emittersOf.set(emit.event_id, [...(this.emittersOf.get(emit.event_id) ?? []), emit]);
      add(this.emittingActionsOf, this.actions.get(emit.action_id)?.domain_id ?? "", emit.action_id);
    }
  }

  /** The events a domain's own actions emit. */
  emittedBy(domainId: string): Set<string> {
    const out = new Set<string>();
    for (const action of this.emittingActionsOf.get(domainId) ?? []) for (const emit of this.emitsOf.get(action) ?? []) out.add(emit.event_id);
    return out;
  }

  /** What a domain shows: its vocabulary, and the events its actions emit that the vocabulary does not hold. */
  domainCounts(domainId: string): { vocabulary: number | null; emittedOnly: number } {
    const held = this.vocabulary.get(domainId);
    const emitted = [...this.emittedBy(domainId)].filter((event) => !held?.has(event));
    return { vocabulary: held ? held.size : null, emittedOnly: emitted.length };
  }

  /** A domain is "with events" when it keeps a vocabulary, even an empty one, or its actions emit. */
  withEvents(domainId: string): boolean {
    return this.vocabulary.has(domainId) || (this.emittingActionsOf.get(domainId)?.size ?? 0) > 0;
  }

  /** Every domain an event belongs to: those holding it, then those whose actions emit it. */
  domainsOfEvent(eventId: string): string[] {
    const held = [...(this.holders.get(eventId) ?? [])].sort();
    const emitting = [...new Set((this.emittersOf.get(eventId) ?? []).map((emit) => this.actions.get(emit.action_id)?.domain_id ?? ""))].filter((domain) => !held.includes(domain)).sort();
    return [...held, ...emitting];
  }

  /** The nodes behind a port, in a stable order. */
  neighbours(node: string, port: PortKind): string[] {
    const id = idOf(node);
    const sorted = (ids: Iterable<string>, kind: Kind) => [...new Set(ids)].sort().map((each) => ref(kind, each));
    switch (`${kindOf(node)}>${port}`) {
      case "domain>events":
        return sorted([...(this.vocabulary.get(id) ?? []), ...this.emittedBy(id)], "event");
      case "domain>actions":
        return sorted(this.actionsOf.get(id) ?? [], "action");
      case "event>actions":
        return sorted((this.emittersOf.get(id) ?? []).map((emit) => emit.action_id), "action");
      case "event>domains":
        return this.domainsOfEvent(id).map((each) => ref("domain", each));
      case "action>events":
        return sorted((this.emitsOf.get(id) ?? []).map((emit) => emit.event_id), "event");
      case "action>domain":
        return this.actions.get(id)?.domain_id ? [ref("domain", this.actions.get(id)!.domain_id)] : [];
      default:
        return [];
    }
  }

  /** The same graph without the methods of the kinds switched off: what they emit is not emitted. */
  only(offKinds: ReadonlySet<string>): EventsGraph {
    return offKinds.size === 0 ? this : new EventsGraph({ ...this.payload, emits: this.payload.emits.filter((emit) => !offKinds.has(emit.kind)) });
  }

  /** Where an event stands: in a vocabulary and emitted, emitted with no vocabulary holding it, or held and never emitted. */
  eventStatus(eventId: string): EventStatus {
    if (!this.emittersOf.has(eventId)) return "not_emitted";
    return (this.holders.get(eventId)?.size ?? 0) > 0 ? "emitted_held" : "emitted_free";
  }

  label(node: string): string {
    const id = idOf(node);
    return (kindOf(node) === "domain" ? this.domains.get(id)?.label : kindOf(node) === "event" ? this.events.get(id)?.label : this.actions.get(id)?.label) ?? id;
  }
}

export type EventStatus = "emitted_held" | "emitted_free" | "not_emitted";
export const EVENT_STATUSES: EventStatus[] = ["emitted_held", "emitted_free", "not_emitted"];
export const METHOD_KINDS = ["RegularAspect", "SummaryAspect", "Compensator", "ErrorHandler", "AccessDecide"];

/**
 * The domains switched on, and every filter row switched off, as ``<section>:<row>``: ``coverage:with`` /
 * ``coverage:without`` (domains), ``events:<status>``, ``methods:<kind>``, ``actions:with`` / ``actions:without``.
 */
export type Filters = { domains: ReadonlySet<string>; off: ReadonlySet<string> };

/**
 * Whether a node stays under the filters: a domain by itself, an action by its domain and its events, an event by its
 * standing and by any of its domains. ``graph`` is the whole graph; ``g`` the same without the methods switched off.
 */
export function passes(node: string, filters: Filters, graph: EventsGraph, g: EventsGraph = graph): boolean {
  const id = idOf(node);
  const domainOk = (domainId: string) => filters.domains.has(domainId) && !filters.off.has(`coverage:${graph.withEvents(domainId) ? "with" : "without"}`);
  switch (kindOf(node)) {
    case "domain":
      return domainOk(id);
    case "action":
      return domainOk(graph.actions.get(id)?.domain_id ?? "") && !filters.off.has(`actions:${graph.emitsOf.has(id) ? "with" : "without"}`);
    case "event":
      return !filters.off.has(`events:${graph.eventStatus(id)}`) && g.domainsOfEvent(id).some(domainOk);
  }
}

/** The first layer of a mode: every domain; every event; every action that emits. */
export function roots(mode: Mode, filters: Filters, graph: EventsGraph, g: EventsGraph = graph): string[] {
  const kind = ROOT_KIND[mode];
  const ids = kind === "domain" ? [...g.domains.keys()] : kind === "event" ? [...g.events.keys()] : [...g.emitsOf.keys()];
  return ids
    .map((id) => ref(kind, id))
    .filter((node) => passes(node, filters, graph, g))
    .sort((one, other) => {
      if (kind === "domain") {
        const quiet = Number(!graph.withEvents(idOf(one))) - Number(!graph.withEvents(idOf(other)));
        if (quiet !== 0) return quiet;
      }
      return graph.label(one).localeCompare(graph.label(other));
    });
}

/** A port; one that joins (``join``) adds no node, it draws its links to the nodes already on screen. */
export type Port = { kind: PortKind; total: number; hidden: number; open: boolean; join: boolean };
export type Shown = { depth: Map<string, number>; ports: Map<string, Port[]> };

/**
 * The ports that lead on: a path passes each kind once. The first layer leads on to both other kinds, the second only
 * to the kind not yet on the path. The third leads nowhere: its one port, toward the kind the path started from, joins it to
 * what is already on screen.
 */
export function allowedPorts(node: string, depth: number, rootKind: Kind): PortKind[] {
  if (depth === 0) return PORTS[kindOf(node)];
  if (depth === 1) return PORTS[kindOf(node)].filter((port) => PORT_TARGET[port] !== rootKind);
  return [];
}

/** The nodes on screen a third-layer port can join to: those its links reach that no line joins it to yet. */
function joinable(node: string, port: PortKind, depth: ReadonlyMap<string, number>, filters: Filters, graph: EventsGraph, g: EventsGraph): string[] {
  return g.neighbours(node, port).filter((next) => passes(next, filters, graph, g) && depth.has(next) && Math.abs(depth.get(next)! - depth.get(node)!) !== 1);
}

/** What is on screen: the roots, and from each shown node what its open ports lead to, breadth first. */
export function explore(first: readonly string[], opened: ReadonlySet<string>, filters: Filters, rootKind: Kind, graph: EventsGraph, g: EventsGraph = graph): Shown {
  const depth = new Map(first.map((node) => [node, 0]));
  const queue = [...first];
  while (queue.length > 0) {
    const node = queue.shift()!;
    for (const port of allowedPorts(node, depth.get(node)!, rootKind)) {
      if (!opened.has(portKey(node, port))) continue;
      for (const next of g.neighbours(node, port)) {
        if (depth.has(next) || !passes(next, filters, graph, g)) continue;
        depth.set(next, depth.get(node)! + 1);
        queue.push(next);
      }
    }
  }
  const ports = new Map<string, Port[]>();
  for (const node of depth.keys()) {
    const level = depth.get(node)!;
    if (level >= 2) {
      // One port, toward the kind the path started from: the other leads back where the node came from.
      ports.set(
        node,
        PORTS[kindOf(node)].filter((kind) => PORT_TARGET[kind] === rootKind).map((kind) => {
          const reach = joinable(node, kind, depth, filters, graph, g).length;
          return { kind, total: reach, hidden: reach, open: reach > 0 && opened.has(portKey(node, kind)), join: true };
        }),
      );
      continue;
    }
    ports.set(
      node,
      allowedPorts(node, level, rootKind).map((kind) => {
        const behind = g.neighbours(node, kind).filter((next) => passes(next, filters, graph, g));
        // An empty port is shown too, with its zero: every node of a kind has the same ports, in the same places.
        return { kind, total: behind.length, hidden: behind.filter((next) => !depth.has(next)).length, open: behind.length > 0 && opened.has(portKey(node, kind)), join: false };
      }),
    );
  }
  return { depth, ports };
}

export type LinkKind = "holds" | "emits" | "domain_emits" | "belongs";
export type Link = { id: string; kind: LinkKind; a: string; b: string; methods: { method: string; kind: string }[] };

/**
 * Every link between two neighbouring layers, and every link an open joining port of the third layer asks for. Any
 * other link is not drawn: an action's domain is told by its colour.
 */
export function links(shown: Shown, opened: ReadonlySet<string>, graph: EventsGraph): Link[] {
  const on = (node: string) => shown.depth.has(node);
  const near = (one: string, other: string) => Math.abs(shown.depth.get(one)! - shown.depth.get(other)!) === 1;
  const joins = (from: string, to: string) => shown.depth.get(from)! >= 2 && opened.has(portKey(from, portToward(from, to)));
  const out: Link[] = [];
  for (const node of shown.depth.keys()) {
    const id = idOf(node);
    if (kindOf(node) === "domain") {
      const held = graph.vocabulary.get(id) ?? new Set<string>();
      for (const event of held) if (on(ref("event", event))) out.push({ id: `h|${id}|${event}`, kind: "holds", a: node, b: ref("event", event), methods: [] });
      for (const event of graph.emittedBy(id)) {
        if (held.has(event) || !on(ref("event", event))) continue;
        out.push({ id: `d|${id}|${event}`, kind: "domain_emits", a: node, b: ref("event", event), methods: [] });
      }
    }
    if (kindOf(node) === "action") {
      const byEvent = new Map<string, ExplorerEmitWire[]>();
      for (const emit of graph.emitsOf.get(id) ?? []) byEvent.set(emit.event_id, [...(byEvent.get(emit.event_id) ?? []), emit]);
      for (const [event, emits] of byEvent) if (on(ref("event", event))) out.push({ id: `e|${id}|${event}`, kind: "emits", a: node, b: ref("event", event), methods: emits.map((emit) => ({ method: emit.method, kind: emit.kind })) });
      const domain = ref("domain", graph.actions.get(id)?.domain_id ?? "");
      if (on(domain)) out.push({ id: `b|${id}`, kind: "belongs", a: node, b: domain, methods: [] });
    }
  }
  return out.filter((link) => near(link.a, link.b) || joins(link.a, link.b) || joins(link.b, link.a)).sort((one, other) => (one.id < other.id ? -1 : 1));
}

/** The port a link leaves ``from`` by, toward ``to``. */
export function portToward(from: string, to: string): PortKind {
  const target = kindOf(to);
  if (kindOf(from) === "action" && target === "domain") return "domain";
  return target === "event" ? "events" : target === "action" ? "actions" : "domains";
}

// --- Geometry shared by the DOT text and the drawing, in points (one point is one pixel on screen).

export const BODY_W = 236;
export const BODY_H: Record<Kind, number> = { domain: 56, event: 40, action: 50 };
export const PORT_W = 66;
export const PORT_ROW_H = 26;

export function nodeSize(node: string, ports: readonly Port[], layout: Layout): { w: number; h: number } {
  // Every node keeps the room of its ports, so nodes of one layer line up whether they have ports or not.
  const body = BODY_H[kindOf(node)];
  return layout === "dot_tb" ? { w: BODY_W, h: body + PORT_ROW_H } : { w: BODY_W + PORT_W, h: Math.max(body, ports.length * 22) };
}

const dotId = (node: string) => `n${[...node].map((char) => (/[A-Za-z0-9]/.test(char) ? char : `_${char.charCodeAt(0).toString(16)}`)).join("")}`;

/** The DOT text: each node a table of the size the drawing gives it, with a cell per port, so lines leave from the ports. */
export function buildDot(shown: Shown, drawnLinks: readonly Link[], layout: Layout): { dot: string; engine: string; byDotId: Map<string, string> } {
  const engine = "dot";
  const tb = layout === "dot_tb";
  // Wide gaps across the flow: many lines fan out of one port, and they need room to part before they arrive.
  const graphAttrs = tb ? "rankdir=TB, nodesep=0.7, ranksep=1.6, splines=spline" : "rankdir=LR, nodesep=0.28, ranksep=2.8, splines=spline";
  const lines = [`digraph explore {`, `  graph [${graphAttrs}];`, '  node [shape=plaintext, margin=0, label=""];', "  edge [arrowhead=none, arrowtail=none];"];
  const byDotId = new Map<string, string>();
  const nodes = [...shown.depth.keys()];
  for (const node of nodes) {
    const id = dotId(node);
    byDotId.set(id, node);
    const ports = shown.ports.get(node) ?? [];
    const body = BODY_H[kindOf(node)];
    const { w, h } = nodeSize(node, ports, layout);
    let table: string;
    if (ports.length === 0) table = tb ? `<TR><TD PORT="in" FIXEDSIZE="TRUE" WIDTH="${w}" HEIGHT="${h}"></TD></TR>` : `<TR><TD PORT="in" FIXEDSIZE="TRUE" WIDTH="${BODY_W}" HEIGHT="${h}"></TD><TD FIXEDSIZE="TRUE" WIDTH="${PORT_W}" HEIGHT="${h}"></TD></TR>`;
    else if (tb) table = `<TR><TD PORT="in" COLSPAN="${ports.length}" FIXEDSIZE="TRUE" WIDTH="${BODY_W}" HEIGHT="${body}"></TD></TR><TR>${ports.map((port) => `<TD PORT="${port.kind}" FIXEDSIZE="TRUE" WIDTH="${BODY_W / ports.length}" HEIGHT="${PORT_ROW_H}"></TD>`).join("")}</TR>`;
    else table = ports.map((port, index) => `<TR>${index === 0 ? `<TD PORT="in" ROWSPAN="${ports.length}" FIXEDSIZE="TRUE" WIDTH="${BODY_W}" HEIGHT="${h}"></TD>` : ""}<TD PORT="${port.kind}" FIXEDSIZE="TRUE" WIDTH="${PORT_W}" HEIGHT="${h / ports.length}"></TD></TR>`).join("");
    lines.push(`  ${id} [label=<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="0">${table}</TABLE>>];`);
  }
  // The first layer keeps its order however the layers after it are drawn: one rank, joined in order by unseen lines.
  const first = nodes.filter((node) => shown.depth.get(node) === 0).map(dotId);
  if (first.length > 1) lines.push(`  { rank=same; ${first.join(" -> ")} [style=invis]; }`);
  for (const link of drawnLinks) {
    // The line leaves the end nearer the first layer, by its port, and enters the other end's body.
    const [da, db] = [shown.depth.get(link.a)!, shown.depth.get(link.b)!];
    const [tail, head] = da < db || (da === db && link.a < link.b) ? [link.a, link.b] : [link.b, link.a];
    const tailPort = (shown.ports.get(tail) ?? []).some((port) => port.kind === portToward(tail, head)) ? portToward(tail, head) : "in";
    const out = tb ? ":s" : ":e";
    const into = tb ? ":n" : ":w";
    const constraint = da === db ? " constraint=false" : "";
    lines.push(`  ${dotId(tail)}:${tailPort}${out} -> ${dotId(head)}:in${into} [id="${link.id}"${constraint}];`);
  }
  lines.push("}");
  return { dot: lines.join("\n"), engine, byDotId };
}

export type Placed = { nodes: Map<string, { x: number; y: number; w: number; h: number }>; edges: Map<string, { d: string; start: { x: number; y: number }; tail: string }>; width: number; height: number };

type GvJson = {
  bb: string;
  objects?: { _gvid: number; name: string; pos?: string; width?: string; height?: string }[];
  edges?: { _gvid: number; tail: number; head: number; id?: string; _draw_?: { op: string; points?: [number, number][] }[] }[];
};

/** Positions and lines out of Graphviz's ``json``: y turned to point down, every line a cubic path. */
export function readLayout(json: string, byDotId: Map<string, string>): Placed {
  const parsed = JSON.parse(json) as GvJson;
  const [, , width, height] = parsed.bb.split(",").map(Number);
  const nodes: Placed["nodes"] = new Map();
  const names = new Map<number, string>();
  for (const object of parsed.objects ?? []) {
    const node = byDotId.get(object.name);
    if (!node || !object.pos) continue;
    names.set(object._gvid, node);
    const [x, y] = object.pos.split(",").map(Number);
    const w = Number(object.width) * 72;
    const h = Number(object.height) * 72;
    nodes.set(node, { x: x - w / 2, y: height - y - h / 2, w, h });
  }
  const edges: Placed["edges"] = new Map();
  for (const edge of parsed.edges ?? []) {
    const points = edge._draw_?.find((op) => op.op === "b" || op.op === "B")?.points;
    if (!edge.id || !points || points.length < 4) continue;
    const flipped = points.map(([x, y]) => [x, height - y] as const);
    const d = `M${flipped[0][0].toFixed(1)},${flipped[0][1].toFixed(1)} ` + flipped.slice(1).map(([x, y], index) => `${index % 3 === 0 ? "C" : ""}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    // A name stands where the line leaves its port: lines are still apart there, wherever they meet later.
    edges.set(edge.id, { d, start: { x: flipped[0][0], y: flipped[0][1] }, tail: names.get(edge.tail) ?? "" });
  }
  return { nodes, edges, width, height };
}

/** The section that paints the screen: every section of the filter panel can (FR-018). */
export type Paint = "domains" | "coverage" | "events" | "methods" | "actions";

/** The kinds of method behind a node, in the Methods section's order: those an action has that emit, those that emit an event. */
export function methodKindsOf(node: string, g: EventsGraph): string[] {
  const emits = kindOf(node) === "action" ? g.emitsOf.get(idOf(node)) : kindOf(node) === "event" ? g.emittersOf.get(idOf(node)) : undefined;
  const kinds = new Set((emits ?? []).map((emit) => emit.kind));
  return METHOD_KINDS.filter((kind) => kinds.has(kind));
}
