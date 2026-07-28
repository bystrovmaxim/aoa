// packages/aoa-client-js/src/path-layout.ts
//
// Where each action ends up on the api object. Every one is always reachable by its full
// path, grouped by HTTP method. A short dot alias
// (api.get.orders) additionally exists only when the path is "clean" -- every segment is
// a valid identifier (no {param}, hyphen, or dot) -- and does not collide with a deeper
// path sharing the same prefix (a segment cannot be both a callable leaf and a branch
// namespace on the same generated object).
//
// Both ways of building the api use this: one renders the layout to TypeScript text, the
// other builds it as a real object at run time. Sharing it is what keeps the two from
// drifting into different shapes.

import { isValidIdentifier } from "./identifier.ts";

export interface LayoutEndpoint {
  operation: string;
  method: string; // wire form, e.g. "POST"
  path: string; // e.g. "/actions/cancel-order"
  baseName: string; // already-disambiguated per-endpoint base, e.g. "CancelOrder"
}

export interface AliasNode {
  endpoint: LayoutEndpoint | null;
  children: Record<string, AliasNode>;
}

export interface MethodLayout {
  method: string; // lowercased, e.g. "post" -- the api[method] bucket key
  bracketEntries: LayoutEndpoint[]; // every endpoint for this method, always
  aliasRoot: AliasNode; // dot-alias tree; aliasRoot itself is never a Primitive
}

export function buildLayout(endpoints: LayoutEndpoint[]): MethodLayout[] {
  const byMethod = new Map<string, LayoutEndpoint[]>();
  for (const endpoint of endpoints) {
    const method = endpoint.method.toLowerCase();
    const bucket = byMethod.get(method);
    if (bucket) bucket.push(endpoint);
    else byMethod.set(method, [endpoint]);
  }
  return [...byMethod.entries()].map(([method, bracketEntries]) => ({
    method,
    bracketEntries,
    aliasRoot: buildAliasTree(bracketEntries),
  }));
}

function buildAliasTree(endpoints: LayoutEndpoint[]): AliasNode {
  const root: AliasNode = { endpoint: null, children: {} };
  for (const endpoint of endpoints) {
    const segments = cleanPathSegments(endpoint.path);
    if (segments === null) continue; // not individually clean -- bracket form only
    let node = root;
    for (const segment of segments) {
      node.children[segment] ??= { endpoint: null, children: {} };
      node = node.children[segment];
    }
    node.endpoint = endpoint;
  }
  // Two-phase by construction: every path is inserted before any node is demoted, so
  // demotion is independent of endpoint insertion order. A node ending up both a leaf
  // and a branch is resolved by dropping just its own alias -- the branch (and any
  // deeper path through it) is unaffected; only the *shorter* colliding path falls back
  // to bracket-only.
  demoteBranchLeafCollisions(root);
  return root;
}

function demoteBranchLeafCollisions(node: AliasNode): void {
  if (node.endpoint !== null && Object.keys(node.children).length > 0) {
    node.endpoint = null;
  }
  for (const child of Object.values(node.children)) {
    demoteBranchLeafCollisions(child);
  }
}

function cleanPathSegments(path: string): string[] | null {
  const segments = path.split("/").filter((segment) => segment.length > 0);
  if (segments.length === 0 || !segments.every(isValidIdentifier)) return null;
  return segments;
}
