// packages/aoa-client-js/src/codegen/json-schema-ir.test.ts
import { describe, expect, it } from "vitest";

import { CodegenSchemaError, isValidIdentifier, parseRootSchema } from "./json-schema-ir.ts";

describe("parseRootSchema", () => {
  it("parses a required integer field (real CancelOrderAction params_schema shape)", () => {
    const parsed = parseRootSchema(
      {
        additionalProperties: false,
        description: "``CancelOrderAction`` parameters — the order to cancel.",
        properties: {
          order_id: { description: "Order identifier", title: "Order Id", type: "integer" },
        },
        required: ["order_id"],
        title: "Params",
        type: "object",
      },
      "test",
    );
    expect(parsed.description).toBe("``CancelOrderAction`` parameters — the order to cancel.");
    expect(parsed.root).toEqual({
      kind: "object",
      properties: [{ name: "order_id", required: true, description: "Order identifier", schema: { kind: "integer" } }],
    });
  });

  it("parses an empty properties object with no required key (real PingAction shape)", () => {
    const parsed = parseRootSchema(
      { additionalProperties: false, description: "PingAction parameters — empty; no input required.", properties: {}, title: "Params", type: "object" },
      "test",
    );
    expect(parsed.root).toEqual({ kind: "object", properties: [] });
  });

  it("parses an untyped dict (additionalProperties: true, no properties key) as unknownRecord", () => {
    const parsed = parseRootSchema(
      {
        additionalProperties: false,
        properties: {
          params: { additionalProperties: true, description: "Raw action parameters.", title: "Params", type: "object" },
        },
        required: ["params"],
        type: "object",
      },
      "test",
    );
    expect(parsed.root.kind).toBe("object");
    if (parsed.root.kind !== "object") throw new Error("unreachable");
    expect(parsed.root.properties[0]?.schema).toEqual({ kind: "unknownRecord" });
  });

  it("parses an array of a primitive type", () => {
    const parsed = parseRootSchema(
      { type: "object", properties: { tags: { type: "array", items: { type: "string" } } }, required: ["tags"] },
      "test",
    );
    if (parsed.root.kind !== "object") throw new Error("unreachable");
    expect(parsed.root.properties[0]?.schema).toEqual({ kind: "array", items: { kind: "string" } });
  });

  it("parses Optional[str] (anyOf [type, null] + default: null) as nullable", () => {
    const parsed = parseRootSchema(
      {
        type: "object",
        properties: {
          note: { anyOf: [{ type: "string" }, { type: "null" }], default: null, description: "An optional string field", title: "Note" },
        },
      },
      "test",
    );
    if (parsed.root.kind !== "object") throw new Error("unreachable");
    const prop = parsed.root.properties[0];
    expect(prop?.required).toBe(false);
    expect(prop?.schema).toEqual({ kind: "nullable", inner: { kind: "string" } });
  });

  it("parses an inline Literal[...] enum (no $ref/$defs — real SchemaEntry.mode shape)", () => {
    const parsed = parseRootSchema(
      {
        type: "object",
        properties: {
          mode: {
            description: "Which pydantic schema mode produced json_schema.",
            enum: ["validation", "serialization"],
            title: "Mode",
            type: "string",
          },
        },
        required: ["mode"],
      },
      "test",
    );
    if (parsed.root.kind !== "object") throw new Error("unreachable");
    expect(parsed.root.properties[0]?.schema).toEqual({ kind: "enum", values: ["validation", "serialization"] });
  });

  it("parses a $ref to an enum $defs entry", () => {
    const parsed = parseRootSchema(
      {
        $defs: { Priority: { enum: ["low", "high"], title: "Priority", type: "string" } },
        type: "object",
        properties: { priority: { $ref: "#/$defs/Priority", description: "An enum field" } },
        required: ["priority"],
      },
      "test",
    );
    expect(parsed.defs.Priority).toEqual({ kind: "enum", values: ["low", "high"] });
    if (parsed.root.kind !== "object") throw new Error("unreachable");
    expect(parsed.root.properties[0]?.schema).toEqual({ kind: "ref", refName: "Priority" });
  });

  it("parses a $ref to a nested object $defs entry", () => {
    const parsed = parseRootSchema(
      {
        $defs: {
          Address: {
            properties: { city: { description: "City name", type: "string" }, zip_code: { description: "Postal code", type: "string" } },
            required: ["city", "zip_code"],
            title: "Address",
            type: "object",
          },
        },
        type: "object",
        properties: { address: { $ref: "#/$defs/Address", description: "A nested object field" } },
        required: ["address"],
      },
      "test",
    );
    expect(parsed.defs.Address).toEqual({
      kind: "object",
      properties: [
        { name: "city", required: true, description: "City name", schema: { kind: "string" } },
        { name: "zip_code", required: true, description: "Postal code", schema: { kind: "string" } },
      ],
    });
  });

  it("parses the full real DemoOptionalAction params_schema end to end", () => {
    const parsed = parseRootSchema(
      {
        $defs: {
          Address: {
            properties: { city: { description: "City name", title: "City", type: "string" }, zip_code: { description: "Postal code", title: "Zip Code", type: "string" } },
            required: ["city", "zip_code"],
            title: "Address",
            type: "object",
          },
          Priority: { enum: ["low", "high"], title: "Priority", type: "string" },
        },
        additionalProperties: false,
        properties: {
          count: { description: "A required integer field", minimum: 0, title: "Count", type: "integer" },
          label: { description: "A required string field", minLength: 1, title: "Label", type: "string" },
          note: { anyOf: [{ type: "string" }, { type: "null" }], default: null, description: "An optional string field", title: "Note" },
          priority: { $ref: "#/$defs/Priority", description: "An enum field" },
          address: { $ref: "#/$defs/Address", description: "A nested object field" },
        },
        required: ["count", "label", "priority", "address"],
        title: "Params",
        type: "object",
      },
      "test",
    );
    if (parsed.root.kind !== "object") throw new Error("unreachable");
    const byName = Object.fromEntries(parsed.root.properties.map((p) => [p.name, p]));
    expect(byName.count).toEqual({ name: "count", required: true, description: "A required integer field", schema: { kind: "integer" } });
    expect(byName.note?.required).toBe(false);
    expect(byName.note?.schema).toEqual({ kind: "nullable", inner: { kind: "string" } });
    expect(byName.priority?.schema).toEqual({ kind: "ref", refName: "Priority" });
    expect(byName.address?.schema).toEqual({ kind: "ref", refName: "Address" });
    expect(parsed.defs.Priority).toEqual({ kind: "enum", values: ["low", "high"] });
  });

  it("parses an object schema with no properties key at all (not additionalProperties:true) as empty, not unknownRecord", () => {
    const parsed = parseRootSchema({ type: "object" }, "test");
    expect(parsed.root).toEqual({ kind: "object", properties: [] });
  });

  it("throws a clear error when the root schema is not an object", () => {
    expect(() => parseRootSchema(null, "test")).toThrow(CodegenSchemaError);
    expect(() => parseRootSchema("nope", "test")).toThrow(/expected a JSON object/);
  });

  it("throws when the root type is not object", () => {
    expect(() => parseRootSchema({ type: "string" }, "test")).toThrow(/expected the root schema to be an object type/);
  });

  it("throws on an unsupported construct (allOf)", () => {
    expect(() => parseRootSchema({ type: "object", properties: { x: { allOf: [{ type: "string" }] } } }, "test")).toThrow(
      /unsupported JSON Schema construct/,
    );
  });

  it("throws on anyOf with more than 2 branches", () => {
    expect(() =>
      parseRootSchema({ type: "object", properties: { x: { anyOf: [{ type: "string" }, { type: "null" }, { type: "integer" }] } } }, "test"),
    ).toThrow(/unsupported anyOf with 3 branches/);
  });

  it("throws on anyOf without a null branch", () => {
    expect(() => parseRootSchema({ type: "object", properties: { x: { anyOf: [{ type: "string" }, { type: "integer" }] } } }, "test")).toThrow(
      /anyOf without a null branch/,
    );
  });

  it("throws on a $ref outside #/$defs/", () => {
    expect(() => parseRootSchema({ type: "object", properties: { x: { $ref: "https://example.com/Other" } } }, "test")).toThrow(
      /only in-document "#\/\$defs\/<name>" refs are supported/,
    );
  });

  it("throws on a $ref to a name missing from $defs at render time (parse itself succeeds, the ref stays unresolved)", () => {
    const parsed = parseRootSchema({ type: "object", properties: { x: { $ref: "#/$defs/Missing" } } }, "test");
    if (parsed.root.kind !== "object") throw new Error("unreachable");
    expect(parsed.root.properties[0]?.schema).toEqual({ kind: "ref", refName: "Missing" });
    expect(parsed.defs.Missing).toBeUndefined();
  });

  it("throws on an enum with non-string values", () => {
    expect(() => parseRootSchema({ $defs: { Bad: { enum: [1, 2] } }, type: "object", properties: { x: { $ref: "#/$defs/Bad" } } }, "test")).toThrow(
      /unsupported enum/,
    );
  });

  it("throws once schema nesting exceeds the depth guard", () => {
    let schema: Record<string, unknown> = { type: "string" };
    for (let i = 0; i < 25; i += 1) {
      schema = { type: "array", items: schema };
    }
    expect(() => parseRootSchema({ type: "object", properties: { x: schema } }, "test")).toThrow(/nesting exceeded/);
  });
});

describe("isValidIdentifier", () => {
  it("accepts plain snake_case and camelCase names", () => {
    expect(isValidIdentifier("order_id")).toBe(true);
    expect(isValidIdentifier("orderId")).toBe(true);
    expect(isValidIdentifier("_private")).toBe(true);
    expect(isValidIdentifier("$special")).toBe(true);
  });

  it("rejects names that are not valid JS identifiers", () => {
    expect(isValidIdentifier("has-hyphen")).toBe(false);
    expect(isValidIdentifier("has space")).toBe(false);
    expect(isValidIdentifier("1leading-digit")).toBe(false);
    expect(isValidIdentifier("")).toBe(false);
  });
});
