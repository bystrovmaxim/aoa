// src/lib/filterUseCaseDiagramByDomains.ts
import type { DomainUseCaseDiagramPayload } from "@/model/domainUseCaseDiagram";

/**
 * Keep actions whose ``domain_id`` is enabled, then drop edges / roles that no longer apply.
 * Roles: seed from ``association`` targets of visible actions, then undirected closure over
 * ``role_generalization`` so superclass/subclass chains stay coherent.
 */
export function filterUseCaseDiagramByDomains(
  data: DomainUseCaseDiagramPayload,
  enabledDomainIds: Set<string>,
): DomainUseCaseDiagramPayload {
  const actions = data.actions.filter((a) => enabledDomainIds.has(a.domain_id));
  const visibleActionIds = new Set(actions.map((a) => a.id));

  const seedRoles = new Set<string>();
  for (const e of data.edges) {
    if (e.edge_kind === "association" && visibleActionIds.has(e.source_id)) {
      seedRoles.add(e.target_id);
    }
  }

  const roleAdj = new Map<string, Set<string>>();
  for (const e of data.edges) {
    if (e.edge_kind !== "role_generalization") continue;
    const a = e.source_id;
    const b = e.target_id;
    if (!roleAdj.has(a)) roleAdj.set(a, new Set());
    if (!roleAdj.has(b)) roleAdj.set(b, new Set());
    roleAdj.get(a)!.add(b);
    roleAdj.get(b)!.add(a);
  }

  const roleIds = new Set<string>();
  const stack = [...seedRoles];
  while (stack.length) {
    const r = stack.pop()!;
    if (roleIds.has(r)) continue;
    roleIds.add(r);
    for (const n of roleAdj.get(r) ?? []) {
      if (!roleIds.has(n)) stack.push(n);
    }
  }

  const roles = data.roles.filter((r) => roleIds.has(r.id));

  const edges = data.edges.filter((e) => {
    if (
      e.edge_kind === "action_generalization" ||
      e.edge_kind === "include" ||
      e.edge_kind === "extend" ||
      e.edge_kind === "depends"
    ) {
      return visibleActionIds.has(e.source_id) && visibleActionIds.has(e.target_id);
    }
    if (e.edge_kind === "association") {
      return visibleActionIds.has(e.source_id) && roleIds.has(e.target_id);
    }
    if (e.edge_kind === "role_generalization") {
      return roleIds.has(e.source_id) && roleIds.has(e.target_id);
    }
    return false;
  });

  return {
    ...data,
    actions,
    roles,
    edges,
  };
}
