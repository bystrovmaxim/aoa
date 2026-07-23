// packages/aoa-client-js/src/codegen/json-schema-to-ts.ts
//
// Renders a parsed IR tree (see json-schema-ir.ts) into TypeScript interface/type-alias
// source text. Every named declaration is `export`ed; nested $defs objects/enums are
// hoisted into their own named declaration the first time a $ref reaches them, named by
// the caller-supplied `resolveRefName` so nesting stays collision-free across endpoints.

import { CodegenSchemaError, isValidIdentifier, type IrNode, type ParsedSchema } from "./json-schema-ir.ts";

export function renderParamsOrResultInterface(
  name: string,
  parsed: ParsedSchema,
  resolveRefName: (refName: string) => string,
): string {
  const hoisted = new Map<string, string>();
  const main = renderInterfaceBody(name, parsed.root, parsed.description, parsed.defs, resolveRefName, hoisted);
  return [main, ...hoisted.values()].join("\n\n");
}

function renderInterfaceBody(
  name: string,
  node: IrNode,
  description: string | undefined,
  defs: Record<string, IrNode>,
  resolveRefName: (refName: string) => string,
  hoisted: Map<string, string>,
): string {
  if (node.kind !== "object") {
    throw new CodegenSchemaError(`Cannot render "${name}" as an interface: underlying schema is "${node.kind}", not an object`);
  }
  const lines: string[] = [];
  if (description) lines.push(...docComment(description));
  lines.push(`export interface ${name} {`);
  for (const prop of node.properties) {
    if (prop.description) lines.push(...indent(docComment(prop.description)));
    const optional = prop.required ? "" : "?";
    const type = typeText(prop.schema, defs, resolveRefName, hoisted);
    lines.push(`  ${propKey(prop.name)}${optional}: ${type};`);
  }
  lines.push("}");
  return lines.join("\n");
}

function typeText(
  node: IrNode,
  defs: Record<string, IrNode>,
  resolveRefName: (refName: string) => string,
  hoisted: Map<string, string>,
): string {
  switch (node.kind) {
    case "string":
      return "string";
    case "integer":
    case "number":
      return "number";
    case "boolean":
      return "boolean";
    case "unknownRecord":
      return "Record<string, unknown>";
    case "array":
      return `${wrapIfUnion(typeText(node.items, defs, resolveRefName, hoisted))}[]`;
    case "nullable":
      return `${typeText(node.inner, defs, resolveRefName, hoisted)} | null`;
    case "enum":
      return node.values.map((value) => JSON.stringify(value)).join(" | ");
    case "object": {
      const fields = node.properties
        .map((prop) => `${propKey(prop.name)}${prop.required ? "" : "?"}: ${typeText(prop.schema, defs, resolveRefName, hoisted)}`)
        .join("; ");
      return `{ ${fields} }`;
    }
    case "ref": {
      const target = defs[node.refName];
      if (!target) {
        throw new CodegenSchemaError(`Unknown $ref "${node.refName}" (not present in $defs)`);
      }
      const finalName = resolveRefName(node.refName);
      if (!hoisted.has(finalName)) {
        hoisted.set(finalName, "");
        hoisted.set(finalName, renderNamedDeclaration(finalName, target, defs, resolveRefName, hoisted));
      }
      return finalName;
    }
  }
}

function renderNamedDeclaration(
  name: string,
  node: IrNode,
  defs: Record<string, IrNode>,
  resolveRefName: (refName: string) => string,
  hoisted: Map<string, string>,
): string {
  if (node.kind === "enum") {
    return `export type ${name} = ${node.values.map((value) => JSON.stringify(value)).join(" | ")};`;
  }
  if (node.kind === "object") {
    return renderInterfaceBody(name, node, undefined, defs, resolveRefName, hoisted);
  }
  throw new CodegenSchemaError(`Unsupported $defs entry kind for a named declaration: "${node.kind}"`);
}

function wrapIfUnion(text: string): string {
  return text.includes(" | ") ? `(${text})` : text;
}

function propKey(name: string): string {
  return isValidIdentifier(name) ? name : JSON.stringify(name);
}

function docComment(text: string): string[] {
  const safe = text.replace(/\*\//g, "*\\/");
  const lines = safe.split("\n");
  if (lines.length === 1) return [`/** ${lines[0]} */`];
  return ["/**", ...lines.map((line) => ` * ${line}`), " */"];
}

function indent(lines: string[]): string[] {
  return lines.map((line) => `  ${line}`);
}
