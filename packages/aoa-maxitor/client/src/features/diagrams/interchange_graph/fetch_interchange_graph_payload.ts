// packages/aoa-maxitor/client/src/features/diagrams/interchange_graph/fetch_interchange_graph_payload.ts
import { apiUrl } from "../../../shared/config/api";
import type { InterchangeGraphG6Payload } from "./types";

type InterchangeGraphApiBody = {
  payload?: InterchangeGraphG6Payload;
};

function edgePropagatesDomain(data: Record<string, unknown>): boolean {
  const rel = data.relationshipName != null ? String(data.relationshipName).trim() : "";
  if (rel.toLowerCase() === "composition" || rel.toLowerCase() === "aggregation") return true;
  const slot = data.label != null ? String(data.label).trim() : "";
  return (
    rel === "" &&
    [
      "@regular_aspect",
      "@summary_aspect",
      "@result_checker",
      "@compensate",
      "@on_error",
      "@required_context",
      "lifecycle",
      "lifecycle_contains_state",
      "lifecycle_transition",
      "generic:params",
      "generic:result",
      "field",
      "property",
    ].includes(slot)
  );
}

function buildDomainBubblePlugins(
  payload: InterchangeGraphG6Payload,
  domainColors: Record<string, string>,
): Array<Record<string, unknown>> {
  const nodeTypeMap = payload.node_type_map ?? {};
  const domainIds = Object.entries(nodeTypeMap)
    .filter(([, nodeType]) => nodeType === "Domain")
    .map(([nodeId]) => nodeId)
    .sort();
  if (domainIds.length === 0) return [];

  const domainMembers = Object.fromEntries(domainIds.map((domainId) => [domainId, new Set<string>([domainId])]));
  const containmentChildren: Record<string, string[]> = {};
  for (const edge of payload.edges) {
    const source = String(edge.source);
    const target = String(edge.target);
    const data = (edge.data ?? {}) as Record<string, unknown>;
    const edgeType = data.edge_type != null ? String(data.edge_type).trim() : "";
    if (edgeType === "domain_edges" && nodeTypeMap[target] === "Domain") {
      domainMembers[target]?.add(source);
      continue;
    }
    if (edgePropagatesDomain(data)) {
      (containmentChildren[source] ??= []).push(target);
    }
  }

  for (const domainId of domainIds) {
    const members = domainMembers[domainId];
    if (!members) continue;
    const queue = [...members];
    for (let i = 0; i < queue.length; i += 1) {
      for (const child of containmentChildren[queue[i]] ?? []) {
        if (members.has(child)) continue;
        members.add(child);
        queue.push(child);
      }
    }
  }

  const nodeById = new Map(payload.nodes.map((node) => [String(node.id), node]));
  return domainIds.flatMap((domainId, index) => {
    const members = [...(domainMembers[domainId] ?? new Set<string>())]
      .filter((nodeId) => nodeTypeMap[nodeId] !== "Application")
      .sort();
    if (members.length === 0) return [];
    const domainData = (nodeById.get(domainId)?.data ?? {}) as Record<string, unknown>;
    const labelText =
      domainData.title != null && String(domainData.title).trim() !== ""
        ? String(domainData.title)
        : domainData.label != null && String(domainData.label).trim() !== ""
          ? String(domainData.label)
          : domainId;
    const color = domainColors[domainId] ?? "#377EB8";
    return [
      {
        key: `bubble-domain-${index}`,
        type: "bubble-sets",
        members,
        labelText,
        fill: color,
        stroke: color,
        pointerEvents: "none",
        fillOpacity: 0.14,
        strokeOpacity: 0.55,
        labelFill: "#fff",
        labelPadding: 2,
        labelBackgroundFill: color,
        labelBackgroundRadius: 5,
      },
    ];
  });
}

/** Load interchange topology JSON for the AntV G6 workspace. */
export async function fetchInterchangeGraphPayload(): Promise<InterchangeGraphG6Payload> {
  const response = await fetch(apiUrl("/api/v1/full-graph"));
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Interchange graph request failed (${response.status}): ${text || response.statusText}`);
  }
  const body = (await response.json()) as InterchangeGraphApiBody;
  if (!body.payload || typeof body.payload !== "object") {
    throw new Error("Interchange graph response missing payload");
  }
  const domainColors = body.payload.domain_color_map ?? {};
  return { ...body.payload, bubble_plugins: buildDomainBubblePlugins(body.payload, domainColors) };
}
