// packages/aoa-client-js/src/codegen/api-layout-to-ts.ts
//
// Renders a path-layout (see path-layout.ts) into the GateApi/CallableApi interface
// pair, per-endpoint descriptors, and the createGateApi/createApi factories. Every
// Primitive is built exactly once per endpoint and referenced from both its bracket key
// and any dot-alias position -- the same operation regardless of which form is used.

import { CodegenSchemaError } from "./json-schema-ir.ts";
import { isReservedWord, NameRegistry } from "./naming.ts";
import type { AliasNode, LayoutEndpoint, MethodLayout } from "../path-layout.ts";

export interface RenderedApiLayout {
  typesSource: string;
  factoriesSource: string;
}

interface DerivedNames {
  descriptorName: string;
  localVarName: string;
}

export function renderApiLayout(layouts: MethodLayout[]): RenderedApiLayout {
  const gateApiType = renderApiInterface("GateApi", layouts, (e) => `GatePrimitive<${e.baseName}Params>`);
  const callableApiType = renderApiInterface(
    "CallableApi",
    layouts,
    (e) => `CallablePrimitive<${e.baseName}Params, ${e.baseName}Result>`,
  );

  const allEndpoints = layouts.flatMap((layout) => layout.bracketEntries);
  // Params/Result/hoisted names live in the TYPE namespace (naming.ts's NameRegistry,
  // audit finding 2); the descriptor const and the local variable below live in the
  // VALUE namespace instead -- a plain `const`, so `Foo` and `foo` (case-distinct
  // endpoint base names, both structurally valid) land on the exact same
  // SCREAMING_SNAKE_CASE / lowerFirst string once case-folded, even though
  // NameRegistry's own base-name claim (case-sensitive) never saw them as colliding
  // (audit finding 4). Two independent registries, since a descriptor name and a local
  // var name never collide with each other (distinct casing conventions) but each must
  // stay unique against its own kind across every endpoint in the file.
  const names = computeDerivedNames(allEndpoints);

  const descriptors = allEndpoints.map((e) => renderDescriptorConst(e, names.get(e.operation)!)).join("\n");
  const gateFactory = renderFactory("createGateApi", "GateApi", layouts, allEndpoints, names, { withActionInvoker: false });
  const callableFactory = renderFactory("createApi", "CallableApi", layouts, allEndpoints, names, { withActionInvoker: true });

  return {
    typesSource: [gateApiType, callableApiType].join("\n\n"),
    factoriesSource: [descriptors, gateFactory, callableFactory].join("\n\n"),
  };
}

function computeDerivedNames(endpoints: LayoutEndpoint[]): Map<string, DerivedNames> {
  const descriptorRegistry = new NameRegistry();
  const localVarRegistry = new NameRegistry();
  const names = new Map<string, DerivedNames>();
  for (const endpoint of endpoints) {
    const descriptorCandidate = `${toScreamingSnakeCase(endpoint.baseName)}_DESCRIPTOR`;
    const localVarCandidate = lowerFirst(endpoint.baseName);
    // A PascalCase base ("Delete") is a fine identifier on its own -- only lowerFirst's
    // case-folded form ("delete") can accidentally land on an ECMAScript reserved word,
    // which the type-namespace validation in naming.ts's assertValidBaseName never sees
    // (audit finding 3, case 1: "const delete = ..." is a SyntaxError, not a type error).
    if (isReservedWord(localVarCandidate)) {
      throw new CodegenSchemaError(
        `Endpoint "${endpoint.operation}" derives the reserved word "${localVarCandidate}" as its local ` +
          `variable name (from base "${endpoint.baseName}") -- rename the action on the server.`,
      );
    }
    names.set(endpoint.operation, {
      descriptorName: descriptorRegistry.claimName(descriptorCandidate, endpoint.operation),
      localVarName: localVarRegistry.claimName(localVarCandidate, endpoint.operation),
    });
  }
  return names;
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

function renderDescriptorConst(endpoint: LayoutEndpoint, names: DerivedNames): string {
  return `const ${names.descriptorName} = { method: ${JSON.stringify(endpoint.method)}, path: ${JSON.stringify(endpoint.path)} };`;
}

function renderFactory(
  functionName: string,
  returnType: string,
  layouts: MethodLayout[],
  allEndpoints: LayoutEndpoint[],
  names: Map<string, DerivedNames>,
  opts: { withActionInvoker: boolean },
): string {
  const params = opts.withActionInvoker ? "engine: AoaEngine, actionInvoker: ActionInvoker" : "engine: AoaEngine";
  const varLines = allEndpoints.map(
    (e) => `  const ${names.get(e.operation)!.localVarName} = ${renderMakeCall(e, names.get(e.operation)!, opts.withActionInvoker)};`,
  );
  const bodyLines = layouts.map((layout) => `    ${layout.method}: ${renderMethodBucketValue(layout, names, 2)},`);
  return [
    `export function ${functionName}(${params}): ${returnType} {`,
    ...varLines,
    "  return {",
    ...bodyLines,
    "  };",
    "}",
  ].join("\n");
}

function renderMakeCall(endpoint: LayoutEndpoint, names: DerivedNames, withActionInvoker: boolean): string {
  const operation = JSON.stringify(endpoint.operation);
  if (!withActionInvoker) {
    return `makeGatePrimitive<${endpoint.baseName}Params>(engine, ${operation})`;
  }
  return (
    `makeCallablePrimitive<${endpoint.baseName}Params, ${endpoint.baseName}Result>(` +
    `engine, ${operation}, ${names.descriptorName}, actionInvoker)`
  );
}

function renderMethodBucketValue(layout: MethodLayout, names: Map<string, DerivedNames>, depth: number): string {
  const indent = "  ".repeat(depth);
  const innerIndent = "  ".repeat(depth + 1);
  const lines = [
    ...layout.bracketEntries.map((e) => `${innerIndent}${JSON.stringify(e.path)}: ${names.get(e.operation)!.localVarName},`),
    ...Object.entries(layout.aliasRoot.children).map(([segment, node]) => renderAliasNodeValue(segment, node, names, depth + 1)),
  ];
  return `{\n${lines.join("\n")}\n${indent}}`;
}

function renderAliasNodeValue(segment: string, node: AliasNode, names: Map<string, DerivedNames>, depth: number): string {
  const indent = "  ".repeat(depth);
  if (node.endpoint !== null) {
    return `${indent}${segment}: ${names.get(node.endpoint.operation)!.localVarName},`;
  }
  const childLines = Object.entries(node.children).map(([childSegment, childNode]) =>
    renderAliasNodeValue(childSegment, childNode, names, depth + 1),
  );
  return `${indent}${segment}: {\n${childLines.join("\n")}\n${indent}},`;
}

// ---- Naming ----

function toScreamingSnakeCase(name: string): string {
  return name.replace(/([a-z0-9])([A-Z])/g, "$1_$2").toUpperCase();
}

function lowerFirst(name: string): string {
  return name.length === 0 ? name : name.charAt(0).toLowerCase() + name.slice(1);
}
