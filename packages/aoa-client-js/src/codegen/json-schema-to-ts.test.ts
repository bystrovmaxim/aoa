// packages/aoa-client-js/src/codegen/json-schema-to-ts.test.ts
import ts from "typescript";
import { describe, expect, it } from "vitest";

import { parseRootSchema } from "./json-schema-ir.ts";
import { renderParamsOrResultInterface } from "./json-schema-to-ts.ts";

function assertSyntacticallyValidTypeScript(source: string): void {
  const result = ts.transpileModule(source, {
    reportDiagnostics: true,
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  });
  const errors = (result.diagnostics ?? []).filter((d) => d.category === ts.DiagnosticCategory.Error);
  if (errors.length > 0) {
    const messages = errors.map((d) => ts.flattenDiagnosticMessageText(d.messageText, "\n")).join("\n");
    throw new Error(`Generated source is not valid TypeScript:\n${messages}\n---\n${source}`);
  }
}

describe("renderParamsOrResultInterface", () => {
  it("renders a required integer field as a non-optional number", () => {
    const parsed = parseRootSchema(
      {
        description: "CancelOrderAction parameters.",
        properties: { order_id: { description: "Order identifier", type: "integer" } },
        required: ["order_id"],
        type: "object",
      },
      "test",
    );
    const source = renderParamsOrResultInterface("CancelOrderParams", parsed, (ref) => `CancelOrderParams${ref}`);
    expect(source).toContain("export interface CancelOrderParams {");
    expect(source).toContain("/** Order identifier */");
    expect(source).toContain("order_id: number;");
    expect(source).not.toContain("order_id?:");
    assertSyntacticallyValidTypeScript(source);
  });

  it("renders an empty object as an empty interface", () => {
    const parsed = parseRootSchema({ properties: {}, type: "object" }, "test");
    const source = renderParamsOrResultInterface("PingParams", parsed, (ref) => `PingParams${ref}`);
    expect(source.replace(/\s+/g, " ").trim()).toBe("export interface PingParams { }");
    assertSyntacticallyValidTypeScript(source);
  });

  // Audit finding 16: a schema with declared properties AND additionalProperties: true
  // (a Python model with extra="allow" plus its own fields) used to render as a plain,
  // closed interface -- silently losing the "extra keys are allowed" signal entirely.
  it("renders an index signature alongside declared properties when additionalProperties is true", () => {
    const parsed = parseRootSchema(
      { properties: { known: { type: "string" } }, required: ["known"], additionalProperties: true, type: "object" },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("known: string;");
    expect(source).toContain("[key: string]: unknown;");
    assertSyntacticallyValidTypeScript(source);
  });

  it("renders no index signature when additionalProperties is false", () => {
    const parsed = parseRootSchema(
      { properties: { known: { type: "string" } }, required: ["known"], additionalProperties: false, type: "object" },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).not.toContain("[key: string]");
  });

  it("renders an index signature in an INLINE nested object too, not only a named interface (typeText's own object case)", () => {
    const parsed = parseRootSchema(
      {
        properties: { nested: { properties: { known: { type: "string" } }, required: ["known"], additionalProperties: true, type: "object" } },
        required: ["nested"],
        type: "object",
      },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("nested: { known: string; [key: string]: unknown };");
    assertSyntacticallyValidTypeScript(source);
  });

  it("renders an optional+nullable field as `field?: T | null`", () => {
    const parsed = parseRootSchema(
      { type: "object", properties: { note: { anyOf: [{ type: "string" }, { type: "null" }], description: "Optional note" } } },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("note?: string | null;");
    assertSyntacticallyValidTypeScript(source);
  });

  it("renders an untyped dict (additionalProperties: true) as Record<string, unknown>", () => {
    const parsed = parseRootSchema(
      { type: "object", properties: { extra: { additionalProperties: true, type: "object" } }, required: ["extra"] },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("extra: Record<string, unknown>;");
    assertSyntacticallyValidTypeScript(source);
  });

  it("renders an inline (non-$ref) nested object as an anonymous inline type literal, with both required and optional fields", () => {
    const parsed = parseRootSchema(
      {
        type: "object",
        properties: {
          point: {
            type: "object",
            properties: { x: { type: "number" }, label: { type: "string" } },
            required: ["x"],
          },
        },
        required: ["point"],
      },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("point: { x: number; label?: string };");
    assertSyntacticallyValidTypeScript(source);
  });

  it("throws a clear error referencing a $ref whose name is entirely absent from $defs", () => {
    const parsed = parseRootSchema({ type: "object", properties: { x: { type: "string" } } }, "test");
    const brokenRoot = {
      kind: "object" as const,
      properties: [{ name: "x", required: true, description: undefined, schema: { kind: "ref" as const, refName: "Ghost" } }],
      additionalProperties: false,
    };
    expect(() => renderParamsOrResultInterface("X", { ...parsed, root: brokenRoot }, (ref) => `X${ref}`)).toThrow(
      /Unknown \$ref "Ghost" \(not present in \$defs\)/,
    );
  });

  it("renders an array of a primitive as T[]", () => {
    const parsed = parseRootSchema({ type: "object", properties: { tags: { type: "array", items: { type: "string" } } }, required: ["tags"] }, "test");
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("tags: string[];");
    assertSyntacticallyValidTypeScript(source);
  });

  it("does not wrap a $ref'd (named) array item type in parens — it's a plain identifier, not an inline union", () => {
    const parsed = parseRootSchema(
      {
        $defs: { Priority: { enum: ["low", "high"], type: "string" } },
        type: "object",
        properties: { priorities: { type: "array", items: { $ref: "#/$defs/Priority" } } },
        required: ["priorities"],
      },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("priorities: XPriority[];");
    assertSyntacticallyValidTypeScript(source);
  });

  it("wraps an inline Literal[...] union item type in parens before appending [] (real SchemaEntry.mode-style shape, no $ref)", () => {
    const parsed = parseRootSchema(
      {
        type: "object",
        properties: { modes: { type: "array", items: { type: "string", enum: ["validation", "serialization"] } } },
        required: ["modes"],
      },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain('modes: ("validation" | "serialization")[];');
    assertSyntacticallyValidTypeScript(source);
  });

  it("hoists a $ref'd enum as a named union type alias, scoped by the caller's naming function", () => {
    const parsed = parseRootSchema(
      {
        $defs: { Priority: { enum: ["low", "high"], type: "string" } },
        type: "object",
        properties: { priority: { $ref: "#/$defs/Priority", description: "An enum field" } },
        required: ["priority"],
      },
      "test",
    );
    const source = renderParamsOrResultInterface("DemoOptionalParams", parsed, (ref) => `DemoOptionalParams${ref}`);
    expect(source).toContain("priority: DemoOptionalParamsPriority;");
    expect(source).toContain('export type DemoOptionalParamsPriority = "low" | "high";');
    assertSyntacticallyValidTypeScript(source);
  });

  it("hoists a $ref'd nested object as a named interface, scoped by the caller's naming function", () => {
    const parsed = parseRootSchema(
      {
        $defs: {
          Address: {
            properties: { city: { type: "string" }, zip_code: { type: "string" } },
            required: ["city", "zip_code"],
            type: "object",
          },
        },
        type: "object",
        properties: { address: { $ref: "#/$defs/Address", description: "A nested object field" } },
        required: ["address"],
      },
      "test",
    );
    const source = renderParamsOrResultInterface("DemoOptionalParams", parsed, (ref) => `DemoOptionalParams${ref}`);
    expect(source).toContain("address: DemoOptionalParamsAddress;");
    expect(source).toContain("export interface DemoOptionalParamsAddress {");
    expect(source).toContain("city: string;");
    expect(source).toContain("zip_code: string;");
    assertSyntacticallyValidTypeScript(source);
  });

  it("hoists a $ref only once even when two properties reference the same $defs entry", () => {
    const parsed = parseRootSchema(
      {
        $defs: { Priority: { enum: ["low", "high"], type: "string" } },
        type: "object",
        properties: {
          a: { $ref: "#/$defs/Priority" },
          b: { $ref: "#/$defs/Priority" },
        },
        required: ["a", "b"],
      },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    const occurrences = source.split("export type XPriority").length - 1;
    expect(occurrences).toBe(1);
    assertSyntacticallyValidTypeScript(source);
  });

  it("quotes a property key that is not a valid JS identifier", () => {
    const parsed = parseRootSchema({ type: "object", properties: { "weird-name": { type: "string" } }, required: ["weird-name"] }, "test");
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain('"weird-name": string;');
    assertSyntacticallyValidTypeScript(source);
  });

  it("escapes a stray */ inside a description so it cannot break out of the doc comment", () => {
    const parsed = parseRootSchema({ type: "object", description: "weird */ text", properties: {} }, "test");
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    assertSyntacticallyValidTypeScript(source);
  });

  it("renders a real full DemoOptionalAction-shaped params_schema as one valid file", () => {
    const parsed = parseRootSchema(
      {
        $defs: {
          Address: {
            properties: { city: { description: "City name", type: "string" }, zip_code: { description: "Postal code", type: "string" } },
            required: ["city", "zip_code"],
            type: "object",
          },
          Priority: { enum: ["low", "high"], type: "string" },
        },
        additionalProperties: false,
        description: "Demo action exercising int/str/Optional/enum/nested fields",
        properties: {
          count: { description: "A required integer field", title: "Count", type: "integer" },
          label: { description: "A required string field", title: "Label", type: "string" },
          note: { anyOf: [{ type: "string" }, { type: "null" }], default: null, description: "An optional string field", title: "Note" },
          priority: { $ref: "#/$defs/Priority", description: "An enum field" },
          address: { $ref: "#/$defs/Address", description: "A nested object field" },
        },
        required: ["count", "label", "priority", "address"],
        type: "object",
      },
      "test",
    );
    const source = renderParamsOrResultInterface("DemoOptionalParams", parsed, (ref) => `DemoOptionalParams${ref}`);
    expect(source).toContain("export interface DemoOptionalParams {");
    expect(source).toContain("count: number;");
    expect(source).toContain("label: string;");
    expect(source).toContain("note?: string | null;");
    expect(source).toContain("priority: DemoOptionalParamsPriority;");
    expect(source).toContain("address: DemoOptionalParamsAddress;");
    expect(source).toContain('export type DemoOptionalParamsPriority = "low" | "high";');
    expect(source).toContain("export interface DemoOptionalParamsAddress {");
    assertSyntacticallyValidTypeScript(source);
  });

  it("does not infinite-loop on a mutually-referential $defs cycle, and produces valid (mutually-referencing) TS", () => {
    const parsed = parseRootSchema(
      {
        $defs: {
          A: { properties: { b: { $ref: "#/$defs/B" } }, required: ["b"], type: "object" },
          B: { properties: { a: { $ref: "#/$defs/A" } }, type: "object" },
        },
        type: "object",
        properties: { a: { $ref: "#/$defs/A" } },
        required: ["a"],
      },
      "test",
    );
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("export interface XA {");
    expect(source).toContain("export interface XB {");
    assertSyntacticallyValidTypeScript(source);
  });

  it("renders a multi-line description as a proper multi-line TSDoc block", () => {
    const parsed = parseRootSchema({ type: "object", description: "Line one.\nLine two.", properties: {} }, "test");
    const source = renderParamsOrResultInterface("X", parsed, (ref) => `X${ref}`);
    expect(source).toContain("/**\n * Line one.\n * Line two.\n */");
    assertSyntacticallyValidTypeScript(source);
  });

  it("throws a clear error hoisting a $defs entry that is neither an object nor an enum", () => {
    const parsed = parseRootSchema({ type: "object", properties: { x: { type: "string" } } }, "test");
    const broken = { ...parsed, defs: { Weird: { kind: "string" as const } } };
    const brokenRoot = {
      kind: "object" as const,
      properties: [{ name: "x", required: true, description: undefined, schema: { kind: "ref" as const, refName: "Weird" } }],
      additionalProperties: false,
    };
    expect(() => renderParamsOrResultInterface("X", { ...broken, root: brokenRoot }, (ref) => `X${ref}`)).toThrow(
      /Unsupported \$defs entry kind for a named declaration: "string"/,
    );
  });

  it("rejects rendering a non-object root as an interface", () => {
    const parsed = parseRootSchema({ type: "object", properties: { x: { type: "string" } } }, "test");
    // Force a non-object node into the renderer's public entry to prove the guard fires.
    const broken = { ...parsed, root: { kind: "string" as const } };
    expect(() => renderParamsOrResultInterface("X", broken, (ref) => ref)).toThrow(/underlying schema is "string", not an object/);
  });
});
