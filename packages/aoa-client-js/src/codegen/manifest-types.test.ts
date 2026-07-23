// packages/aoa-client-js/src/codegen/manifest-types.test.ts
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
});
