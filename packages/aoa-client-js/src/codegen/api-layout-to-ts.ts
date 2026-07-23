// packages/aoa-client-js/src/codegen/api-layout-to-ts.ts
//
// Renders a path-layout (see path-layout.ts) into the GateApi/CallableApi interface
// pair, per-endpoint descriptors, and the createGateApi/createApi factories. Every
// Primitive is built exactly once per endpoint and referenced from both its bracket key
// and any dot-alias position -- the same operation regardless of which form is used.

import type { AliasNode, LayoutEndpoint, MethodLayout } from "../path-layout.ts";

export interface RenderedApiLayout {
  typesSource: string;
  factoriesSource: string;
}

export function renderApiLayout(layouts: MethodLayout[]): RenderedApiLayout {
  const gateApiType = renderApiInterface("GateApi", layouts, (e) => `GatePrimitive<${e.baseName}Params>`);
  const callableApiType = renderApiInterface(
    "CallableApi",
    layouts,
    (e) => `CallablePrimitive<${e.baseName}Params, ${e.baseName}Result>`,
  );

  const allEndpoints = layouts.flatMap((layout) => layout.bracketEntries);
  const descriptors = allEndpoints.map(renderDescriptorConst).join("\n");
  const gateFactory = renderFactory("createGateApi", "GateApi", layouts, allEndpoints, { withActionInvoker: false });
  const callableFactory = renderFactory("createApi", "CallableApi", layouts, allEndpoints, { withActionInvoker: true });

  return {
    typesSource: [gateApiType, callableApiType].join("\n\n"),
    factoriesSource: [descriptors, gateFactory, callableFactory].join("\n\n"),
  };
}

// ---- Types: GateApi / CallableApi ----

function renderApiInterface(name: string, layouts: MethodLayout[], primitiveTypeFor: (e: LayoutEndpoint) => string): string {
  const lines = layouts.map((layout) => `  ${layout.method}: ${renderMethodBucketType(layout, primitiveTypeFor, 1)};`);
  return `export interface ${name} {\n${lines.join("\n")}\n}`;
}

function renderMethodBucketType(layout: MethodLayout, primitiveTypeFor: (e: LayoutEndpoint) => string, depth: number): string {
  const indent = "  ".repeat(depth);
  const innerIndent = "  ".repeat(depth + 1);
  const lines = [
    ...layout.bracketEntries.map((e) => `${innerIndent}${JSON.stringify(e.path)}: ${primitiveTypeFor(e)};`),
    ...Object.entries(layout.aliasRoot.children).map(([segment, node]) =>
      renderAliasNodeType(segment, node, primitiveTypeFor, depth + 1),
    ),
  ];
  return `{\n${lines.join("\n")}\n${indent}}`;
}

function renderAliasNodeType(
  segment: string,
  node: AliasNode,
  primitiveTypeFor: (e: LayoutEndpoint) => string,
  depth: number,
): string {
  const indent = "  ".repeat(depth);
  if (node.endpoint !== null) {
    return `${indent}${segment}: ${primitiveTypeFor(node.endpoint)};`;
  }
  const childLines = Object.entries(node.children).map(([childSegment, childNode]) =>
    renderAliasNodeType(childSegment, childNode, primitiveTypeFor, depth + 1),
  );
  return `${indent}${segment}: {\n${childLines.join("\n")}\n${indent}};`;
}

// ---- Descriptors + factories ----

function renderDescriptorConst(endpoint: LayoutEndpoint): string {
  return `const ${descriptorName(endpoint)} = { method: ${JSON.stringify(endpoint.method)}, path: ${JSON.stringify(endpoint.path)} };`;
}

function renderFactory(
  functionName: string,
  returnType: string,
  layouts: MethodLayout[],
  allEndpoints: LayoutEndpoint[],
  opts: { withActionInvoker: boolean },
): string {
  const params = opts.withActionInvoker ? "engine: AoaEngine, actionInvoker: ActionInvoker" : "engine: AoaEngine";
  const varLines = allEndpoints.map((e) => `  const ${localVarName(e)} = ${renderMakeCall(e, opts.withActionInvoker)};`);
  const bodyLines = layouts.map((layout) => `    ${layout.method}: ${renderMethodBucketValue(layout, 2)},`);
  return [
    `export function ${functionName}(${params}): ${returnType} {`,
    ...varLines,
    "  return {",
    ...bodyLines,
    "  };",
    "}",
  ].join("\n");
}

function renderMakeCall(endpoint: LayoutEndpoint, withActionInvoker: boolean): string {
  const operation = JSON.stringify(endpoint.operation);
  if (!withActionInvoker) {
    return `makeGatePrimitive<${endpoint.baseName}Params>(engine, ${operation})`;
  }
  return (
    `makeCallablePrimitive<${endpoint.baseName}Params, ${endpoint.baseName}Result>(` +
    `engine, ${operation}, ${descriptorName(endpoint)}, actionInvoker)`
  );
}

function renderMethodBucketValue(layout: MethodLayout, depth: number): string {
  const indent = "  ".repeat(depth);
  const innerIndent = "  ".repeat(depth + 1);
  const lines = [
    ...layout.bracketEntries.map((e) => `${innerIndent}${JSON.stringify(e.path)}: ${localVarName(e)},`),
    ...Object.entries(layout.aliasRoot.children).map(([segment, node]) => renderAliasNodeValue(segment, node, depth + 1)),
  ];
  return `{\n${lines.join("\n")}\n${indent}}`;
}

function renderAliasNodeValue(segment: string, node: AliasNode, depth: number): string {
  const indent = "  ".repeat(depth);
  if (node.endpoint !== null) {
    return `${indent}${segment}: ${localVarName(node.endpoint)},`;
  }
  const childLines = Object.entries(node.children).map(([childSegment, childNode]) =>
    renderAliasNodeValue(childSegment, childNode, depth + 1),
  );
  return `${indent}${segment}: {\n${childLines.join("\n")}\n${indent}},`;
}

// ---- Naming ----

function descriptorName(endpoint: LayoutEndpoint): string {
  return `${toScreamingSnakeCase(endpoint.baseName)}_DESCRIPTOR`;
}

function localVarName(endpoint: LayoutEndpoint): string {
  return lowerFirst(endpoint.baseName);
}

function toScreamingSnakeCase(name: string): string {
  return name.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toUpperCase();
}

function lowerFirst(name: string): string {
  return name.length === 0 ? name : name.charAt(0).toLowerCase() + name.slice(1);
}
