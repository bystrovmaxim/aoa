// packages/aoa-maxitor/client/src/features/diagrams/erd/lib/enrich_erd_data.ts
/**
 * Client-side ``ERD_DATA`` enrichment: inject per-node ``color`` for renderers from
 * ``domain_qualifier_colors`` (from ``ListDomainsAction`` / ``domain_info``), then derive
 * ``domain_accent_colors`` for the domain legend.
 */
const ENTITY_COLORS = [
  "#3b82f6",
  "#8b5cf6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#06b6d4",
  "#ec4899",
  "#64748b",
] as const;

export function enrichErdDataForViewer(erdData: Record<string, unknown>): Record<string, unknown> {
  const domainsRaw = erdData.domains;
  if (!domainsRaw || typeof domainsRaw !== "object" || !Object.keys(domainsRaw as object).length) {
    return { ...erdData, domain_accent_colors: {}, domain_legend_icons: {} };
  }

  const qualifiers = (erdData.domain_qualifiers ?? {}) as Record<string, string>;
  const qualToColor = (erdData.domain_qualifier_colors ?? {}) as Record<string, string>;

  const domainsIn = domainsRaw as Record<string, { nodes?: Array<Record<string, unknown>>; edges?: unknown[] }>;
  const domains: Record<string, { nodes: Array<Record<string, unknown>>; edges?: unknown[] }> = {};
  const accents: Record<string, string> = {};

  for (const [tabKey, payload] of Object.entries(domainsIn)) {
    const tabQual = (qualifiers[tabKey] ?? "").trim();
    const tabColor =
      tabQual && qualToColor[tabQual] ? qualToColor[tabQual]! : ENTITY_COLORS[0];
    accents[tabKey] = tabColor;

    const nodes = (payload.nodes ?? []).map((raw) => {
      const n = { ...raw };
      const nodeQual = String(n.domain_qualifier ?? tabQual ?? "").trim();
      const hex = (nodeQual && qualToColor[nodeQual]) || tabColor;
      n.color = hex;
      return n;
    });
    domains[tabKey] = { ...payload, nodes };
  }

  return { ...erdData, domains, domain_accent_colors: accents, domain_legend_icons: {} };
}
