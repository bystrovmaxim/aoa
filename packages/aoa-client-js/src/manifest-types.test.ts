// packages/aoa-client-js/src/manifest-types.test.ts
import { describe, expect, it } from "vitest";

import { assertManifestShape } from "./manifest-types.ts";

const VALID_MANIFEST = {
  manifest_version: "sha256:abc123",
  version: 1,
  manifest_schema_version: 2,
  endpoints: [],
  schemas: {},
};

describe("assertManifestShape", () => {
  it("accepts a well-formed manifest", () => {
    expect(() => assertManifestShape(VALID_MANIFEST, "http://x")).not.toThrow();
  });

  it.each([null, undefined, "a string", 42, ["array", "not", "object"]])("rejects a non-object body (%j)", (value) => {
    expect(() => assertManifestShape(value, "http://x")).toThrow(/is not a JSON object/);
  });

  it("rejects a missing/non-numeric version", () => {
    const { version: _version, ...rest } = VALID_MANIFEST;
    expect(() => assertManifestShape(rest, "http://x")).toThrow(/missing a numeric "version"/);
    expect(() => assertManifestShape({ ...VALID_MANIFEST, version: "1" }, "http://x")).toThrow(/missing a numeric "version"/);
  });

  it("rejects a missing/non-string manifest_version", () => {
    const { manifest_version: _manifestVersion, ...rest } = VALID_MANIFEST;
    expect(() => assertManifestShape(rest, "http://x")).toThrow(/missing a string "manifest_version"/);
  });

  it("rejects a missing/non-array endpoints", () => {
    expect(() => assertManifestShape({ ...VALID_MANIFEST, endpoints: {} }, "http://x")).toThrow(/missing an "endpoints" array/);
  });

  it("rejects a missing/non-object schemas", () => {
    expect(() => assertManifestShape({ ...VALID_MANIFEST, schemas: null }, "http://x")).toThrow(/missing a "schemas" object/);
    expect(() => assertManifestShape({ ...VALID_MANIFEST, schemas: [] }, "http://x")).toThrow(/missing a "schemas" object/);
  });

  it("includes the offending URL in the error message", () => {
    expect(() => assertManifestShape(null, "https://api.example.com/client-manifest.json")).toThrow(
      /https:\/\/api\.example\.com\/client-manifest\.json/,
    );
  });

  const VALID_ENDPOINT = {
    operation: "POST /actions/cancel-order",
    name: "CancelOrderAction",
    domain: "OrdersDomain",
    description: "Cancel an order",
    route: { method: "POST", path: "/actions/cancel-order" },
    params_schema: {},
    result_schema: {},
  };

  describe("endpoints[] element shape (audit finding 8)", () => {
    it("accepts a well-formed endpoint", () => {
      expect(() => assertManifestShape({ ...VALID_MANIFEST, endpoints: [VALID_ENDPOINT] }, "http://x")).not.toThrow();
    });

    it("rejects a non-object endpoint element, naming its index", () => {
      expect(() => assertManifestShape({ ...VALID_MANIFEST, endpoints: [null] }, "http://x")).toThrow(/endpoints\[0\] is not a JSON object/);
    });

    it.each(["operation", "name", "domain", "description"] as const)("rejects an endpoint missing string field %s", (field) => {
      const { [field]: _omitted, ...broken } = VALID_ENDPOINT;
      expect(() => assertManifestShape({ ...VALID_MANIFEST, endpoints: [broken] }, "http://x")).toThrow(
        new RegExp(`endpoints\\[0\\] is missing a string "${field}"`),
      );
    });

    // The exact two shapes from the audit's own repro: route missing entirely, and
    // route present but null -- both used to crash loadFrom with a raw TypeError
    // ("Cannot read properties of undefined/null (reading 'method')"), not a ProtocolError.
    it("rejects an endpoint with no route at all", () => {
      const { route: _route, ...broken } = VALID_ENDPOINT;
      expect(() => assertManifestShape({ ...VALID_MANIFEST, endpoints: [broken] }, "http://x")).toThrow(
        /endpoints\[0\] is missing a "route" object/,
      );
    });

    it("rejects an endpoint with route: null", () => {
      expect(() => assertManifestShape({ ...VALID_MANIFEST, endpoints: [{ ...VALID_ENDPOINT, route: null }] }, "http://x")).toThrow(
        /endpoints\[0\] is missing a "route" object/,
      );
    });

    it("rejects a route missing method or path", () => {
      expect(() =>
        assertManifestShape({ ...VALID_MANIFEST, endpoints: [{ ...VALID_ENDPOINT, route: { path: "/x" } }] }, "http://x"),
      ).toThrow(/endpoints\[0\] is missing a "route" object/);
    });

    it("rejects a non-object params_schema/result_schema", () => {
      expect(() =>
        assertManifestShape({ ...VALID_MANIFEST, endpoints: [{ ...VALID_ENDPOINT, params_schema: null }] }, "http://x"),
      ).toThrow(/endpoints\[0\] is missing a "params_schema" object/);
      expect(() =>
        assertManifestShape({ ...VALID_MANIFEST, endpoints: [{ ...VALID_ENDPOINT, result_schema: [] }] }, "http://x"),
      ).toThrow(/endpoints\[0\] is missing a "result_schema" object/);
    });

    it("names the correct index for the second of several endpoints", () => {
      expect(() => assertManifestShape({ ...VALID_MANIFEST, endpoints: [VALID_ENDPOINT, null] }, "http://x")).toThrow(
        /endpoints\[1\] is not a JSON object/,
      );
    });
  });

  describe("schemas{} entry shape (audit finding 8)", () => {
    it("accepts a well-formed entry", () => {
      const schemas = { ResolveResponse: { mode: "serialization", json_schema: {} } };
      expect(() => assertManifestShape({ ...VALID_MANIFEST, schemas }, "http://x")).not.toThrow();
    });

    it("rejects a non-object entry", () => {
      expect(() => assertManifestShape({ ...VALID_MANIFEST, schemas: { X: null } }, "http://x")).toThrow(
        /schemas\["X"\] is not a JSON object/,
      );
    });

    it("rejects an entry with an unrecognized mode", () => {
      expect(() =>
        assertManifestShape({ ...VALID_MANIFEST, schemas: { X: { mode: "wrong", json_schema: {} } } }, "http://x"),
      ).toThrow(/schemas\["X"\] has an unrecognized "mode"/);
    });

    it("rejects an entry with a non-object json_schema", () => {
      expect(() =>
        assertManifestShape({ ...VALID_MANIFEST, schemas: { X: { mode: "validation", json_schema: null } } }, "http://x"),
      ).toThrow(/schemas\["X"\] is missing a "json_schema" object/);
    });
  });
});
