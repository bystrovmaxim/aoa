// packages/aoa-client-js/src/dynamic-api.ts
//
// Builds the same hybrid bracket/dot-alias `api` shape as the static codegen
// (api-layout-to-ts.ts), but as a real in-memory object rather than TypeScript source --
// used by AoaEngine.loadFrom (chapter 5, dynamic mode). Both consume the exact same
// path-layout.ts MethodLayout[], so the two outputs are identical in shape; this module
// only differs in what it does with a leaf: build a real GatePrimitive instead of
// rendering a type + a make call as text. No compile-time per-endpoint types are
// possible here -- the manifest's shape is only known once this code actually runs.

import type { AoaEngine } from "./engine.ts";
import { makeGatePrimitive, type GatePrimitive } from "./primitive.ts";
import type { AliasNode, LayoutEndpoint, MethodLayout } from "./path-layout.ts";

export type DynamicApiNode = GatePrimitive<unknown> | { [key: string]: DynamicApiNode };
export type DynamicGateApi = Record<string, Record<string, DynamicApiNode>>;

export function buildDynamicGateApi(layouts: MethodLayout[], engine: AoaEngine): DynamicGateApi {
  const api: DynamicGateApi = {};
  for (const layout of layouts) {
    api[layout.method] = buildMethodBucket(layout, engine);
  }
  return api;
}

function buildMethodBucket(layout: MethodLayout, engine: AoaEngine): Record<string, DynamicApiNode> {
  const primitivesByOperation = new Map<string, GatePrimitive<unknown>>();
  const primitiveFor = (endpoint: LayoutEndpoint): GatePrimitive<unknown> => {
    const existing = primitivesByOperation.get(endpoint.operation);
    if (existing) return existing;
    const created = makeGatePrimitive<unknown>(engine, endpoint.operation);
    primitivesByOperation.set(endpoint.operation, created);
    return created;
  };

  const bucket: Record<string, DynamicApiNode> = {};
  for (const endpoint of layout.bracketEntries) {
    bucket[endpoint.path] = primitiveFor(endpoint);
  }
  for (const [segment, node] of Object.entries(layout.aliasRoot.children)) {
    bucket[segment] = buildAliasNode(node, primitiveFor);
  }
  return bucket;
}

function buildAliasNode(node: AliasNode, primitiveFor: (endpoint: LayoutEndpoint) => GatePrimitive<unknown>): DynamicApiNode {
  if (node.endpoint !== null) {
    return primitiveFor(node.endpoint);
  }
  const namespace: Record<string, DynamicApiNode> = {};
  for (const [segment, child] of Object.entries(node.children)) {
    namespace[segment] = buildAliasNode(child, primitiveFor);
  }
  return namespace;
}
