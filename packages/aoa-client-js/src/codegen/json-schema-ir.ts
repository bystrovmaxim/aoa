// packages/aoa-client-js/src/codegen/json-schema-ir.ts
//
// Parses the bounded JSON Schema subset the server actually emits (plain types, lists,
// enums, in-document $refs — no recursive types, no custom formats; see chapter 3's
// "Эталонные схемы") into a small intermediate representation shared by the TS and zod
// renderers, so both target the same parse instead of each re-deriving it independently.

export interface IrProperty {
  name: string;
  required: boolean;
  description: string | undefined;
  schema: IrNode;
}

// JSON Schema has THREE states here, and collapsing them to a boolean is what
// let a bug in: an ABSENT `additionalProperties` means extras are ALLOWED, not
// forbidden. A boolean built as `schema.additionalProperties === true` folds
// "absent" in with "false", so a consumer that renders the false branch as a
// refusal starts rejecting responses the schema explicitly permits.
//
// "unspecified" also covers `additionalProperties: <sub-schema>` — a constraint
// this bounded subset does not enforce. It is reported as unspecified rather
// than as a refusal precisely so nothing claims to enforce what it does not.
export type AdditionalProperties = "allow" | "forbid" | "unspecified";

export type IrNode =
  | { kind: "string" }
  | { kind: "integer" }
  | { kind: "number" }
  | { kind: "boolean" }
  | { kind: "unknownRecord" }
  | { kind: "array"; items: IrNode }
  // `additionalProperties` is required, not optional, so both renderers have to
  // consciously decide what to do with it rather than a stale one silently ignoring a
  // node shape it wasn't updated for (audit finding 16: a schema with both declared
  // properties AND additionalProperties: true -- e.g. a Python model with extra="allow"
  // plus its own fields -- used to fall through to plain "object" with no signal that
  // extra keys are allowed at all, only handled as `unknownRecord` below when there were
  // no declared properties to begin with).
  | { kind: "object"; properties: IrProperty[]; additionalProperties: AdditionalProperties }
  | { kind: "enum"; values: string[] }
  | { kind: "nullable"; inner: IrNode }
  | { kind: "ref"; refName: string };

export interface ParsedSchema {
  description: string | undefined;
  root: IrNode;
  defs: Record<string, IrNode>;
}

export class CodegenSchemaError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CodegenSchemaError";
  }
}

const MAX_SCHEMA_DEPTH = 20;

export { isValidIdentifier } from "../identifier.ts";

/**
 * Parses a top-level `params_schema`/`result_schema`/`schemas.*.json_schema` document
 * (always `{"type": "object", ...}` for this codebase's action Params/Result and wire
 * messages) into an IR tree plus its `$defs` map, parsed once and resolved by name —
 * `$ref` nodes stay unresolved (`{kind: "ref", refName}`) so renderers decide hoisting.
 */
export function parseRootSchema(raw: unknown, context: string): ParsedSchema {
  const schema = expectRecord(raw, context);
  const rawDefs = isRecord(schema.$defs) ? schema.$defs : {};
  const defs: Record<string, IrNode> = {};
  for (const key of Object.keys(rawDefs)) {
    defs[key] = parseDefEntry(rawDefs[key], `${context} $defs.${key}`);
  }
  const root = parseNode(schema, `${context} (root)`, 0);
  if (root.kind !== "object") {
    throw new CodegenSchemaError(`${context}: expected the root schema to be an object type, got "${root.kind}"`);
  }
  return {
    description: typeof schema.description === "string" ? schema.description : undefined,
    root,
    defs,
  };
}

function parseDefEntry(raw: unknown, context: string): IrNode {
  return parseNode(raw, context, 0);
}

function parseNode(raw: unknown, context: string, depth: number): IrNode {
  if (depth > MAX_SCHEMA_DEPTH) {
    throw new CodegenSchemaError(`${context}: schema nesting exceeded ${MAX_SCHEMA_DEPTH} levels (possible $ref cycle)`);
  }
  const schema = expectRecord(raw, context);

  if (typeof schema.$ref === "string") {
    return { kind: "ref", refName: refNameFromPointer(schema.$ref, context) };
  }

  // A Literal[...] field (e.g. SchemaEntry.mode in the manifest's own self-schema) renders
  // inline as {type: "string", enum: [...]} with no $ref/$defs — unlike a real Enum
  // subclass, which pydantic always hoists to $defs. Must be checked before the `type`
  // switch below, or the enum constraint is silently dropped and this parses as "string".
  if (Array.isArray(schema.enum)) {
    return parseEnumNode(schema, context);
  }

  if (Array.isArray(schema.anyOf)) {
    return parseAnyOf(schema.anyOf, context, depth);
  }

  switch (schema.type) {
    case "string":
      return { kind: "string" };
    case "integer":
      return { kind: "integer" };
    case "number":
      return { kind: "number" };
    case "boolean":
      return { kind: "boolean" };
    case "array":
      return { kind: "array", items: parseNode(schema.items, `${context}.items`, depth + 1) };
    case "object":
      return parseObjectNode(schema, context, depth);
    default:
      throw new CodegenSchemaError(
        `${context}: unsupported JSON Schema construct (type=${JSON.stringify(schema.type)}); ` +
          "expected one of string/integer/number/boolean/array/object, a $ref, or an Optional anyOf-null pattern",
      );
  }
}

function parseObjectNode(schema: Record<string, unknown>, context: string, depth: number): IrNode {
  const hasProperties = isRecord(schema.properties) && Object.keys(schema.properties).length > 0;
  const additionalProperties: AdditionalProperties =
    schema.additionalProperties === true ? "allow" : schema.additionalProperties === false ? "forbid" : "unspecified";
  // Deliberately keyed on an EXPLICIT "allow", not on "not forbidden". By the
  // letter of JSON Schema a bare `{ "type": "object" }` also means "any object",
  // so "unspecified" arguably belongs here too -- but that is a separate,
  // pre-existing design choice with its own test, and flipping it would silently
  // turn every endpoint whose schema omits the key into `Record<string, unknown>`
  // instead of a closed interface. Out of scope for the fix below; see the
  // three-state note above for the part that WAS a bug.
  if (additionalProperties === "allow" && !hasProperties) {
    return { kind: "unknownRecord" };
  }
  const rawProperties = isRecord(schema.properties) ? schema.properties : {};
  const required = new Set(
    Array.isArray(schema.required) ? schema.required.filter((entry): entry is string => typeof entry === "string") : [],
  );
  const properties: IrProperty[] = Object.keys(rawProperties).map((name) => {
    const propContext = `${context}.properties.${name}`;
    const propSchema = expectRecord(rawProperties[name], propContext);
    return {
      name,
      required: required.has(name),
      description: typeof propSchema.description === "string" ? propSchema.description : undefined,
      schema: parseNode(propSchema, propContext, depth + 1),
    };
  });
  return { kind: "object", properties, additionalProperties };
}

function parseAnyOf(anyOf: unknown[], context: string, depth: number): IrNode {
  if (anyOf.length !== 2) {
    throw new CodegenSchemaError(
      `${context}: unsupported anyOf with ${anyOf.length} branches (only the 2-branch Optional[...] pattern is supported)`,
    );
  }
  const branches = anyOf.map((branch, index) => expectRecord(branch, `${context}.anyOf[${index}]`));
  const nullBranchIndex = branches.findIndex((branch) => branch.type === "null");
  if (nullBranchIndex === -1) {
    throw new CodegenSchemaError(`${context}: unsupported anyOf without a null branch (only Optional[...] is supported)`);
  }
  const valueBranch = branches[1 - nullBranchIndex];
  return { kind: "nullable", inner: parseNode(valueBranch, `${context}.anyOf`, depth + 1) };
}

function parseEnumNode(schema: Record<string, unknown>, context: string): IrNode {
  const values = schema.enum;
  if (!Array.isArray(values) || values.length === 0 || values.some((value) => typeof value !== "string")) {
    throw new CodegenSchemaError(`${context}: unsupported enum (only non-empty string enums are supported)`);
  }
  return { kind: "enum", values: values as string[] };
}

function refNameFromPointer(ref: string, context: string): string {
  const prefix = "#/$defs/";
  if (!ref.startsWith(prefix) || ref.length === prefix.length) {
    throw new CodegenSchemaError(`${context}: unsupported $ref "${ref}" (only in-document "#/$defs/<name>" refs are supported)`);
  }
  return ref.slice(prefix.length);
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function expectRecord(value: unknown, context: string): Record<string, unknown> {
  if (!isRecord(value)) {
    throw new CodegenSchemaError(`${context}: expected a JSON object, got ${JSON.stringify(value)}`);
  }
  return value;
}
