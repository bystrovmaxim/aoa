// packages/maxitor/front/client/scripts/generate-large-graph.ts
/**
 * generate-large-graph — a graph 30 times the stand's, for measuring the map (spec 040).
 *
 * Copies a graph file, every id prefixed by its copy, shares the application node, links each action to its namesake
 * in the next copy so that links cross domains, and writes a second version changing one domain.
 *
 *   node scripts/generate-large-graph.ts <graph.json> <output folder> [copies]
 */

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";

type GraphNode = { id: string; type: string; label: string; properties: Record<string, unknown> };
type GraphEdge = { id: string; source_id: string; target_id: string; type: string; relationship: string; properties: Record<string, unknown> };
type GraphFile = { nodes: GraphNode[]; edges: GraphEdge[] };

const [input, output, copiesText] = process.argv.slice(2);
const copies = Number(copiesText ?? 30);
const graph = JSON.parse(readFileSync(input, "utf8")) as GraphFile;
const shared = new Set(graph.nodes.filter((node) => node.type === "Application").map((node) => node.id));
const inCopy = (copy: number, id: string) => (shared.has(id) ? id : `s${copy}.${id}`);

/** An edge's id in a copy: every id it names is prefixed, a field's name is not. */
function copiedId(edge: GraphEdge, copy: number): string {
  const parts = edge.id.split("|");
  parts[0] = inCopy(copy, parts[0]);
  if (edge.type !== "entity_relation" && parts[2]) parts[2] = inCopy(copy, parts[2]);
  return parts.join("|");
}

const nodes = graph.nodes.filter((node) => shared.has(node.id));
const edges: GraphEdge[] = [];
const dependency = graph.edges.find((edge) => edge.type === "@depends")!;
const actions = graph.nodes.filter((node) => node.type === "Action").map((node) => node.id);
for (let copy = 0; copy < copies; copy += 1) {
  for (const node of graph.nodes) {
    if (shared.has(node.id)) continue;
    nodes.push({ ...node, id: inCopy(copy, node.id), label: node.type === "Domain" ? `${node.label}${copy}` : node.label });
  }
  for (const edge of graph.edges) edges.push({ ...edge, id: copiedId(edge, copy), source_id: inCopy(copy, edge.source_id), target_id: inCopy(copy, edge.target_id) });
  for (const action of actions) {
    const source = inCopy(copy, action);
    const target = inCopy((copy + 1) % copies, action);
    edges.push({ ...dependency, id: `${source}|@depends|${target}`, source_id: source, target_id: target });
  }
}
mkdirSync(output, { recursive: true });
writeFileSync(join(output, "a.json"), JSON.stringify({ ...graph, nodes, edges }));

// The next version: one field gone and one entity described anew, in one copy.
const gone = nodes.find((node) => node.type === "EntityField" && node.id.startsWith("s7."))!;
const entity = nodes.find((node) => node.type === "Entity" && node.id.startsWith("s7."))!;
writeFileSync(
  join(output, "b.json"),
  JSON.stringify({
    ...graph,
    nodes: nodes.filter((node) => node !== gone).map((node) => (node === entity ? { ...node, properties: { ...node.properties, description: "Changed in this version" } } : node)),
    edges: edges.filter((edge) => edge.source_id !== gone.id && edge.target_id !== gone.id),
  }),
);
console.log(`${nodes.length} nodes, ${edges.length} edges`);
