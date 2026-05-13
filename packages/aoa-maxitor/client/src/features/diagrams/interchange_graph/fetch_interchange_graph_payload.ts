// packages/aoa-maxitor/client/src/features/diagrams/interchange_graph/fetch_interchange_graph_payload.ts
import { apiUrl } from "../../../shared/config/api";
import type { InterchangeGraphG6Payload } from "./types";

type InterchangeGraphApiBody = {
  payload?: InterchangeGraphG6Payload;
};

const CONTAINMENT_EDGE_TYPES = new Set([
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
]);

function buildDomainBubblePlugins(
  payload: InterchangeGraphG6Payload,
  domainColors: Record<string, string>,
): Array<Record<string, unknown>> {
  const nodeTypeMap = payload.node_type_map ?? {};
  const domainIds: string[] = [];
  const domainNodeById = new Map<string, (typeof payload.nodes)[number]>();
  for (const node of payload.nodes) {
    const nodeId = String(node.id);
    if (nodeTypeMap[nodeId] !== "Domain") continue;
    domainIds.push(nodeId);
    domainNodeById.set(nodeId, node);
  }
  if (domainIds.length === 0) return [];

  const domainMembers = new Map<string, Set<string>>();
  const containmentChildren = new Map<string, Set<string>>();
  for (const domainId of domainIds) {
    domainMembers.set(domainId, new Set([domainId]));
  }

  for (const edge of payload.edges) {
    const source = String(edge.source);
    const target = String(edge.target);
    const data = (edge.data ?? {}) as Record<string, unknown>;
    const edgeType = data.edge_type != null ? String(data.edge_type).trim() : "";
    if (edgeType === "domain_edges" && nodeTypeMap[target] === "Domain") {
      domainMembers.get(target)?.add(source);
      continue;
    }
    const rel = data.relationshipName != null ? String(data.relationshipName).trim() : "";
    const relLower = rel.toLowerCase();
    const isContainment =
      relLower === "composition" ||
      relLower === "aggregation" ||
      (rel === "" && CONTAINMENT_EDGE_TYPES.has(edgeType));
    if (isContainment) {
      let children = containmentChildren.get(source);
      if (children === undefined) {
        children = new Set();
        containmentChildren.set(source, children);
      }
      children.add(target);
    }
  }

  for (const domainId of domainIds) {
    const members = domainMembers.get(domainId);
    if (members === undefined) continue;
    const queue: string[] = [...members];
    let head = 0;
    while (head < queue.length) {
      const nodeId = queue[head++];
      const children = containmentChildren.get(nodeId);
      if (children === undefined) continue;
      for (const child of children) {
        if (members.has(child)) continue;
        members.add(child);
        queue.push(child);
      }
    }
  }

  const result: Array<Record<string, unknown>> = [];
  for (let index = 0; index < domainIds.length; index += 1) {
    const domainId = domainIds[index];
    const members: string[] = [];
    for (const nodeId of domainMembers.get(domainId) ?? []) {
      if (nodeTypeMap[nodeId] !== "Application") members.push(nodeId);
    }
    if (members.length === 0) continue;
    const domainData = (domainNodeById.get(domainId)?.data ?? {}) as Record<string, unknown>;
    const labelText =
      domainData.title != null && String(domainData.title).trim() !== ""
        ? String(domainData.title)
        : domainData.label != null && String(domainData.label).trim() !== ""
          ? String(domainData.label)
          : domainId;
    const color = domainColors[domainId] ?? "#377EB8";
    result.push({
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
    });
  }
  return result;
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
