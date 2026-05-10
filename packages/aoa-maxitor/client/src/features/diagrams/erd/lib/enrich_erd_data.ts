// packages/aoa-maxitor/client/src/features/diagrams/erd/lib/enrich_erd_data.ts
/**
 * Client-side ``ERD_DATA`` enrichment (accent swatches; legend icons left to the shell / future work).
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

function domainAccentFromPayload(d: { nodes?: Array<{ color?: string }> }): string {
  for (const n of d.nodes ?? []) {
    const c = String(n.color ?? "").trim();
    if (c) return c;
  }
  return ENTITY_COLORS[0];
}

export function enrichErdDataForViewer(erdData: Record<string, unknown>): Record<string, unknown> {
  const domains = erdData.domains;
  if (!domains || typeof domains !== "object" || !Object.keys(domains as object).length) {
    return { ...erdData, domain_accent_colors: {}, domain_legend_icons: {} };
  }
  const accents: Record<string, string> = {};
  for (const [k, v] of Object.entries(domains as Record<string, { nodes?: Array<{ color?: string }> }>)) {
    accents[k] = domainAccentFromPayload(v);
  }
  return { ...erdData, domain_accent_colors: accents, domain_legend_icons: {} };
}
