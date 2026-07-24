// packages/aoa-client-js/src/codegen/json-schema-to-zod.test.ts
import { z } from "zod";
import { describe, expect, it } from "vitest";

import { parseRootSchema, type ParsedSchema } from "./json-schema-ir.ts";
import { renderResolveResponseZodSchema } from "./json-schema-to-zod.ts";

/**
 * `renderResolveResponseZodSchema` always wraps its output as
 * `export const ResolveResponseSchema = <expr>;` — strip that wrapper and evaluate the
 * expression against a REAL, installed zod, so these tests prove the generated code
 * actually behaves correctly at runtime, not just that it looks plausible as text.
 *
 * Returns `any`, not `z.ZodTypeAny`: the schema's shape is only known once the
 * generated text is evaluated, so there is nothing honest to statically type here — in
 * zod v4, `ZodTypeAny`'s `Output` defaults to `unknown` (unlike v3's `any`), which would
 * just force an `as any` at every call site instead of at this one, deliberate boundary.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function evalZodSchema(source: string): any {
  const match = /^export const ResolveResponseSchema = ([\s\S]+);\n?$/.exec(source);
  if (!match) throw new Error(`Unexpected rendered shape: ${source}`);
  // eslint-disable-next-line @typescript-eslint/no-implied-eval
  return new Function("z", `return (${match[1]});`)(z);
}

describe("renderResolveResponseZodSchema", () => {
  it("renders and executes the real schemas.ResolveResponse wrapper shape", () => {
    const parsed = parseRootSchema(
      {
        $defs: { BaseVerdict: { additionalProperties: false, properties: { kind: { default: "", type: "string" } }, type: "object" } },
        additionalProperties: false,
        properties: {
          version: { type: "integer" },
          results: { items: { $ref: "#/$defs/BaseVerdict" }, type: "array" },
        },
        required: ["version", "results"],
        type: "object",
      },
      "test",
    );
    const source = renderResolveResponseZodSchema(parsed);
    expect(source.startsWith("export const ResolveResponseSchema = ")).toBe(true);

    const schema = evalZodSchema(source);
    const allowed = schema.parse({ version: 1, results: [{ kind: "AllowedVerdict" }] });
    expect(allowed).toEqual({ version: 1, results: [{ kind: "AllowedVerdict" }] });

    const withFailure = schema.parse({
      version: 1,
      results: [{ kind: "AllowedVerdict" }, { kind: "FailSecurityVerdict", reason: "only the order owner can cancel" }],
    });
    expect(withFailure.results[1]).toEqual({ kind: "FailSecurityVerdict", reason: "only the order owner can cancel" });
  });

  it("substitutes the fixed discriminated Verdict union for $ref: BaseVerdict — not a mechanical (kind-only) translation", () => {
    const parsed = parseRootSchema(
      {
        $defs: { BaseVerdict: { additionalProperties: false, properties: { kind: { default: "", type: "string" } }, type: "object" } },
        properties: { version: { type: "integer" }, results: { items: { $ref: "#/$defs/BaseVerdict" }, type: "array" } },
        required: ["version", "results"],
        type: "object",
      },
      "test",
    );
    const source = renderResolveResponseZodSchema(parsed);
    expect(source).toContain("z.discriminatedUnion");
    const schema = evalZodSchema(source);

    // A mechanical translation of $defs.BaseVerdict ({kind: string} only) would accept
    // this — the fixed Verdict union must not, since FailSecurityVerdict requires reason.
    expect(() => schema.parse({ version: 1, results: [{ kind: "FailSecurityVerdict" }] })).toThrow();
    expect(() => schema.parse({ version: 1, results: [{ kind: "FailErrorVerdict" }] })).toThrow();
    expect(() => schema.parse({ version: 1, results: [{ kind: "FailSecurityVerdict", reason: "" }] })).toThrow();
    // An unrecognized kind must also be rejected — the union is closed, not a passthrough.
    expect(() => schema.parse({ version: 1, results: [{ kind: "SomethingElse" }] })).toThrow();
  });

  it("rejects a non-integer version and a cardinality/shape mismatch", () => {
    const parsed = parseRootSchema(
      {
        $defs: { BaseVerdict: { properties: { kind: { type: "string" } }, type: "object" } },
        properties: { version: { type: "integer" }, results: { items: { $ref: "#/$defs/BaseVerdict" }, type: "array" } },
        required: ["version", "results"],
        type: "object",
      },
      "test",
    );
    const schema = evalZodSchema(renderResolveResponseZodSchema(parsed));
    expect(() => schema.parse({ version: 1.5, results: [] })).toThrow();
    expect(() => schema.parse({ version: 1 })).toThrow();
    expect(() => schema.parse({ version: 1, results: "not-an-array" })).toThrow();
  });

  it("exercises every other IR kind through a kitchen-sink object (string/number/boolean/nullable/enum/nested/unknownRecord)", () => {
    const parsed = parseRootSchema(
      {
        $defs: {
          Priority: { enum: ["low", "high"], type: "string" },
          Address: { properties: { city: { type: "string" } }, required: ["city"], type: "object" },
        },
        properties: {
          name: { type: "string" },
          count: { type: "number" },
          active: { type: "boolean" },
          note: { anyOf: [{ type: "string" }, { type: "null" }] },
          priority: { $ref: "#/$defs/Priority" },
          address: { $ref: "#/$defs/Address" },
          extra: { additionalProperties: true, type: "object" },
        },
        required: ["name", "count", "active", "priority", "address", "extra"],
        type: "object",
      },
      "test",
    );
    const source = renderResolveResponseZodSchema(parsed);
    const schema = evalZodSchema(source);

    const valid = schema.parse({
      name: "x",
      count: 3.5,
      active: true,
      priority: "low",
      address: { city: "Metropolis" },
      extra: { anything: "goes", n: 1 },
    });
    expect(valid.note).toBeUndefined();
    expect(valid.priority).toBe("low");
    expect(valid.address).toEqual({ city: "Metropolis" });
    expect(valid.extra).toEqual({ anything: "goes", n: 1 });

    const withNullNote = schema.parse({
      name: "x",
      count: 1,
      active: false,
      note: null,
      priority: "high",
      address: { city: "Gotham" },
      extra: {},
    });
    expect(withNullNote.note).toBeNull();

    expect(() => schema.parse({ name: "x", count: 1, active: true, priority: "medium", address: { city: "X" }, extra: {} })).toThrow();
  });

  it("renders an object with zero properties as z.object({})", () => {
    const parsed = parseRootSchema(
      {
        properties: { empty: { properties: {}, type: "object" }, version: { type: "integer" } },
        required: ["empty", "version"],
        type: "object",
      },
      "test",
    );
    const schema = evalZodSchema(renderResolveResponseZodSchema(parsed));
    expect(schema.parse({ empty: {}, version: 1 })).toEqual({ empty: {}, version: 1 });
  });

  // Audit finding 6: `required` (can the key be absent) and nullable (can the value be
  // null) are orthogonal, and the buggy renderer conflated them in two OPPOSITE
  // directions. Both are exercised here independently of the other, unlike the
  // kitchen-sink test above, whose one nullable field ("note") is also not required --
  // so it can't distinguish which of the two mechanisms actually made it optional.
  it("makes a non-required, non-nullable field optional -- renderZodObject must not ignore `required`", () => {
    const parsed = parseRootSchema(
      { properties: { label: { type: "string" } }, required: [], type: "object" },
      "test",
    );
    const schema = evalZodSchema(renderResolveResponseZodSchema(parsed));
    // Before the fix: renderZodObject never looked at `required` at all, so a plain,
    // non-nullable, non-required field was rendered as mandatory -- {} failed to parse.
    expect(schema.parse({})).toEqual({});
    expect(schema.parse({ label: "x" })).toEqual({ label: "x" });
  });

  it("keeps a required-but-nullable field mandatory -- the key must be present even though its value may be null", () => {
    const parsed = parseRootSchema(
      { properties: { x: { anyOf: [{ type: "string" }, { type: "null" }] } }, required: ["x"], type: "object" },
      "test",
    );
    const schema = evalZodSchema(renderResolveResponseZodSchema(parsed));
    // Before the fix: the `nullable` branch unconditionally appended `.optional()`,
    // so a required-but-nullable field silently accepted a missing key too.
    expect(() => schema.parse({})).toThrow();
    expect(schema.parse({ x: null })).toEqual({ x: null });
    expect(schema.parse({ x: "y" })).toEqual({ x: "y" });
  });

  it("throws a clear error rendering a $ref to a name missing from $defs (and not a well-known name like BaseVerdict)", () => {
    const parsed: ParsedSchema = {
      description: undefined,
      root: { kind: "object", properties: [{ name: "x", required: true, description: undefined, schema: { kind: "ref", refName: "Missing" } }] },
      defs: {},
    };
    expect(() => renderResolveResponseZodSchema(parsed)).toThrow(/Unknown \$ref "Missing"/);
  });
});
