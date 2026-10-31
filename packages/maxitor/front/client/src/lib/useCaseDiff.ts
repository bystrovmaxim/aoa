// src/lib/useCaseDiff.ts
/**
 * The use-case diagram of two versions (spec 041): the union of A's and B's diagram of a domain, each action, role
 * and link marked with what the comparison says. A use-case diagram does not draw an action's parts, so an action
 * the server says changed inside is marked changed; its own added or removed status stands.
 */
import { getActiveBase } from "@/api/client";
import { compareChangedInside, compareVersions, type ChangedInside, type CompareResult } from "@/api/compare";
import { fetchDomainUseCaseDiagram } from "@/api/domainUseCaseDiagram";
import { listDomains } from "@/api/erd";
import { domainUseCaseDotNodeId, useCaseCellId } from "@/lib/buildDomainUseCaseDotSource";
import type { DiagramCounts } from "@/lib/erdDiff";
import type { CardTarget } from "@/lib/erdDiffCard";
import type { GraphvizChange } from "@/lib/useGraphvizChangeStepping";
import type { DomainUseCaseDiagramPayload } from "@/model/domainUseCaseDiagram";

/** Every element of two lists, each once by id: B's where both have it; sorted, so a pair has one DOT text. */
function union<T extends { id: string }>(older: readonly T[], newer: readonly T[]): T[] {
  const byId = new Map(older.map((element) => [element.id, element]));
  for (const element of newer) byId.set(element.id, element);
  return [...byId.values()].sort((one, other) => (one.id < other.id ? -1 : one.id > other.id ? 1 : 0));
}

/** The union of a domain's diagram in A and in B; a domain only one version has comes from that one. */
export function mergeUseCaseDiagrams(older: DomainUseCaseDiagramPayload | null, newer: DomainUseCaseDiagramPayload | null): DomainUseCaseDiagramPayload {
  const domain = (newer ?? older)?.domain;
  if (!domain) throw new Error("Neither version has this domain.");
  const was = new Map((older?.actions ?? []).map((action) => [action.id, action]));
  return {
    domain,
    actions: union(older?.actions ?? [], newer?.actions ?? []).map((action) => ({ ...action, role_ids: [...new Set([...(was.get(action.id)?.role_ids ?? []), ...action.role_ids])].sort() })),
    roles: union(older?.roles ?? [], newer?.roles ?? []),
    edges: union(older?.edges ?? [], newer?.edges ?? []),
  };
}

/** Every drawn element marked with its status, an action changed inside as changed. */
export function markUseCaseDiagram(diagram: DomainUseCaseDiagramPayload, compared: CompareResult, inside: ChangedInside): DomainUseCaseDiagramPayload {
  return {
    ...diagram,
    actions: diagram.actions.map((action) => {
      const diff = compared.nodes[action.id] ?? (inside[action.id]?.length ? "changed" : "unchanged");
      return { ...action, diff, parts: diff === "changed" ? inside[action.id] : undefined };
    }),
    roles: diagram.roles.map((role) => ({ ...role, diff: compared.nodes[role.id] ?? "unchanged" })),
    edges: diagram.edges.map((edge) => ({ ...edge, diff: compared.edges[edge.id] ?? "unchanged" })),
  };
}

/** The drawn diagram's counts: every action, role and link it marks (spec 041, FR-010). */
export function useCaseCounts(diagram: DomainUseCaseDiagramPayload): DiagramCounts {
  const counts: DiagramCounts = { added: 0, removed: 0, changed: 0 };
  for (const element of [...diagram.actions, ...diagram.roles, ...diagram.edges]) {
    if (element.diff && element.diff !== "unchanged") counts[element.diff] += 1;
  }
  return counts;
}

/** The same diagram with every mark taken off, as One draws it. */
export function unmarkedUseCase(diagram: DomainUseCaseDiagramPayload): DomainUseCaseDiagramPayload {
  return {
    ...diagram,
    actions: diagram.actions.map(({ diff: _diff, parts: _parts, ...action }) => action),
    roles: diagram.roles.map(({ diff: _diff, ...role }) => role),
    edges: diagram.edges.map(({ diff: _diff, ...edge }) => edge),
  };
}

/** The card of a marked action or role by its id, or ``null`` when it is unchanged or no longer drawn. */
export function useCaseCard(diagram: DomainUseCaseDiagramPayload, id: string): CardTarget | null {
  const action = diagram.actions.find((each) => each.id === id);
  const element = action ?? diagram.roles.find((each) => each.id === id);
  const status = element?.diff;
  if (!element || !status || status === "unchanged") return null;
  return { title: element.short_label || element.label, status, elements: [{ kind: "node", id }], parts: action?.parts };
}

/** The last part of a dotted id: what a link's ends are called on its row in a list. */
function shortName(id: string): string {
  return id.split(".").pop() ?? id;
}

/** Sorts by a text, then by id, so a list has one order. */
function byName<T extends { id: string }>(elements: readonly T[], name: (element: T) => string): T[] {
  return [...elements].sort((one, other) => name(one).localeCompare(name(other)) || (one.id < other.id ? -1 : 1));
}

/** Every change the drawn diagram marks, once each: its actions, its roles, then its links, which have no card (spec 041, FR-017). */
export function useCaseChanges(diagram: DomainUseCaseDiagramPayload): GraphvizChange[] {
  const name = (element: { short_label: string; label: string }) => element.short_label || element.label;
  const node = (element: DomainUseCaseDiagramPayload["actions" | "roles"][number], group: string, detail: string): GraphvizChange[] => {
    const card = useCaseCard(diagram, element.id);
    return card ? [{ key: element.id, title: card.title, detail, status: card.status, group, cell: useCaseCellId(element.id), card }] : [];
  };
  return [
    ...byName(diagram.actions, name).flatMap((action) => node(action, "Actions", action.parts?.length ? "Changed inside" : "Action")),
    ...byName(diagram.roles, name).flatMap((role) => node(role, "Roles", "Role")),
    ...byName(diagram.edges, (edge) => `${edge.edge_kind}|${edge.source_id}|${edge.target_id}`).flatMap((edge) =>
      edge.diff && edge.diff !== "unchanged"
        ? [{ key: edge.id, title: `${shortName(edge.source_id)} → ${shortName(edge.target_id)}`, detail: edge.stereotype ?? edge.edge_kind, status: edge.diff, group: "Links", cell: useCaseCellId(edge.id), card: null }]
        : [],
    ),
  ];
}

/** The id of the marked action or role a click landed on, by the node Graphviz wrote for it. */
export function useCaseIdAt(target: Element | null, diagram: DomainUseCaseDiagramPayload): string | null {
  const name = target?.closest?.("g.node")?.querySelector("title")?.textContent;
  if (!name) return null;
  const action = diagram.actions.find((each) => domainUseCaseDotNodeId("a", each.id) === name);
  const role = diagram.roles.find((each) => domainUseCaseDotNodeId("r", each.id) === name);
  const element = action ?? role;
  return element?.diff && element.diff !== "unchanged" ? element.id : null;
}

/** A domain's use cases in the pair being compared, read from each version that has the domain, merged and marked. */
export async function loadUseCaseDiff(domainId: string): Promise<DomainUseCaseDiagramPayload> {
  const base = getActiveBase();
  if (!base) throw new Error("No two versions to compare.");
  const [newerListing, olderListing, compared, inside] = await Promise.all([listDomains(), listDomains(base), compareVersions(), compareChangedInside()]);
  const has = (listing: typeof newerListing) => listing.list_domains.some((row) => row.qualname === domainId);
  const [newer, older] = await Promise.all([
    has(newerListing) ? fetchDomainUseCaseDiagram(domainId) : null,
    has(olderListing) ? fetchDomainUseCaseDiagram(domainId, base) : null,
  ]);
  return markUseCaseDiagram(mergeUseCaseDiagrams(older, newer), compared, inside);
}
