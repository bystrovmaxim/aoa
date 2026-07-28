// packages/aoa-client-js/src/dynamic-api.ts
//
// Builds the same api object the code generator writes out, but as a real object at run
// time instead of as text. Both read the same layout, so the two have the same shape and
// differ only at the leaves. No per-action types are possible here: nothing knows the
// shape until the server answers.

import { makeGatePrimitive, type GatePrimitive } from "./primitive.ts";
import type { AliasNode, LayoutEndpoint, MethodLayout } from "./path-layout.ts";
import type { ResolveEngine } from "./types.ts";

export type DynamicApiNode = GatePrimitive<unknown> | { [key: string]: DynamicApiNode };
export type DynamicGateApi = Record<string, Record<string, DynamicApiNode>>;

export function buildDynamicGateApi(layouts: MethodLayout[], engine: ResolveEngine): DynamicGateApi {
  const api: DynamicGateApi = {};
  for (const layout of layouts) {
    api[layout.method] = buildMethodBucket(layout, engine);
  }
  return api;
}

function buildMethodBucket(layout: MethodLayout, engine: ResolveEngine): Record<string, DynamicApiNode> {
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
