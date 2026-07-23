// packages/aoa-client-js/src/codegen/generate-client.test.ts
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import ts from "typescript";
import { afterEach, describe, expect, it, vi } from "vitest";

import { generateClient } from "./generate-client.ts";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const tscBinary = path.join(packageRoot, "node_modules", ".bin", "tsc");

/**
 * Real, end-to-end validity check: writes the generated file to disk inside this
 * package (so plain node_modules resolution finds the real, installed `zod`), maps the
 * package's own name back to its real `src/index.ts` via `paths` (proving the
 * `export type {...} from "aoa-client-js"` re-export line genuinely resolves and
 * typechecks against the real runtime types, not just that it looks textually
 * plausible), and runs the real, already-installed `tsc` against it.
 */
function assertGeneratedFileTypechecks(source: string): void {
  const dir = mkdtempSync(path.join(packageRoot, ".codegen-tsc-check-"));
  try {
    writeFileSync(path.join(dir, "generated.ts"), source, "utf8");
    writeFileSync(
      path.join(dir, "tsconfig.json"),
      JSON.stringify({
        compilerOptions: {
          target: "ES2022",
          lib: ["ES2022", "DOM"],
          module: "ESNext",
          moduleResolution: "bundler",
          allowImportingTsExtensions: true,
          isolatedModules: true,
          moduleDetection: "force",
          noEmit: true,
          strict: true,
          skipLibCheck: true,
          baseUrl: ".",
          paths: { "aoa-client-js": ["../src/index.ts"] },
        },
        include: ["generated.ts"],
      }),
    );
    execFileSync(tscBinary, ["--noEmit", "-p", dir], { cwd: packageRoot, stdio: "pipe" });
  } catch (error) {
    const stdout = (error as { stdout?: Buffer }).stdout?.toString() ?? "";
    throw new Error(`Generated file failed to typecheck:\n${stdout}\n---\n${source}`);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function assertSyntacticallyValid(source: string): void {
  const result = ts.transpileModule(source, {
    reportDiagnostics: true,
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  });
  const errors = (result.diagnostics ?? []).filter((d) => d.category === ts.DiagnosticCategory.Error);
  expect(errors, errors.map((d) => ts.flattenDiagnosticMessageText(d.messageText, "\n")).join("\n")).toHaveLength(0);
}

const CANCEL_ORDER_ENDPOINT = {
  operation: "POST /actions/cancel-order",
  name: "CancelOrderAction",
  domain: "OrdersDomain",
  description: "Cancel an order (manager only)",
  route: { method: "POST", path: "/actions/cancel-order" },
  params_schema: {
    additionalProperties: false,
    description: "``CancelOrderAction`` parameters — the order to cancel.",
    properties: { order_id: { description: "Order identifier", title: "Order Id", type: "integer" } },
    required: ["order_id"],
    title: "Params",
    type: "object",
  },
  result_schema: {
    additionalProperties: false,
    description: "``CancelOrderAction`` result — the new order status.",
    properties: { status: { description: "New order status", title: "Status", type: "string" } },
    required: ["status"],
    title: "Result",
    type: "object",
  },
};

const PING_ENDPOINT = {
  operation: "GET /actions/ping",
  name: "PingAction",
  domain: "SystemDomain",
  description: "Service health check",
  route: { method: "GET", path: "/actions/ping" },
  params_schema: {
    additionalProperties: false,
    description: "PingAction parameters — empty; no input required.",
    properties: {},
    title: "Params",
    type: "object",
  },
  result_schema: {
    additionalProperties: false,
    description: "PingAction result — pong message.",
    properties: { message: { description: "Service response message", title: "Message", type: "string" } },
    required: ["message"],
    title: "Result",
    type: "object",
  },
};

const DEMO_OPTIONAL_ENDPOINT = {
  operation: "POST /actions/demo-optional",
  name: "DemoOptionalAction",
  domain: "TestDomain",
  description: "Demo action exercising int/str/Optional/enum/nested fields",
  route: { method: "POST", path: "/actions/demo-optional" },
  params_schema: {
    $defs: {
      Address: {
        properties: {
          city: { description: "City name", title: "City", type: "string" },
          zip_code: { description: "Postal code", title: "Zip Code", type: "string" },
        },
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
  result_schema: {
    additionalProperties: false,
    properties: {
      ok: { description: "Whether it worked", title: "Ok", type: "boolean" },
      echoed_note: { anyOf: [{ type: "string" }, { type: "null" }], default: null, description: "Echoes note back", title: "Echoed Note" },
    },
    required: ["ok"],
    title: "Result",
    type: "object",
  },
};

const RESOLVE_RESPONSE_SCHEMA_ENTRY = {
  mode: "serialization",
  json_schema: {
    $defs: {
      BaseVerdict: {
        additionalProperties: false,
        description: "Abstract root of every access-check outcome.",
        properties: { kind: { default: "", title: "Kind", type: "string" } },
        title: "BaseVerdict",
        type: "object",
      },
    },
    additionalProperties: false,
    description: "Body of the POST /permissions/resolve response.",
    properties: {
      version: { description: "Echoes the request's wire-language version.", title: "Version", type: "integer" },
      results: { description: "One result per request item.", items: { $ref: "#/$defs/BaseVerdict" }, title: "Results", type: "array" },
    },
    required: ["version", "results"],
    title: "ResolveResponse",
    type: "object",
    $schema: "https://json-schema.org/draft/2020-12/schema",
  },
};

function fakeManifest(endpoints: unknown[]) {
  return {
    manifest_version: "sha256:e445a95f284a1181e2ca9d72d935eac2fb50a377244807a9a8601ef6ed77963b",
    version: 1,
    manifest_schema_version: 2,
    endpoints,
    schemas: { ResolveResponse: RESOLVE_RESPONSE_SCHEMA_ENTRY },
  };
}

function stubFetchJson(body: unknown, init?: { ok?: boolean; status?: number; statusText?: string }): void {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({
      ok: init?.ok ?? true,
      status: init?.status ?? 200,
      statusText: init?.statusText ?? "OK",
      json: async () => body,
    })),
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("generateClient", () => {
  it("calls fetch with exactly the given url", async () => {
    stubFetchJson(fakeManifest([]));
    await generateClient("https://api.example.com/client-manifest.json");
    expect(fetch).toHaveBeenCalledWith("https://api.example.com/client-manifest.json");
  });

  it("throws a clear error on a non-ok HTTP response", async () => {
    stubFetchJson({}, { ok: false, status: 500, statusText: "Internal Server Error" });
    await expect(generateClient("https://x/client-manifest.json")).rejects.toThrow(/HTTP 500 Internal Server Error/);
  });

  it("throws a clear error when the manifest is missing schemas.ResolveResponse", async () => {
    stubFetchJson({ manifest_version: "sha256:x", version: 1, manifest_schema_version: 2, endpoints: [], schemas: {} });
    await expect(generateClient("https://x/client-manifest.json")).rejects.toThrow(/missing the required "schemas.ResolveResponse"/);
  });

  it("throws a clear error when the manifest body is malformed", async () => {
    stubFetchJson(null);
    await expect(generateClient("https://x/client-manifest.json")).rejects.toThrow(/is not a JSON object/);
  });

  it("generates a complete, valid client for zero endpoints", async () => {
    stubFetchJson(fakeManifest([]));
    const source = await generateClient("https://x/client-manifest.json");
    expect(source).toContain("AUTO-GENERATED by aoa-client-js/codegen");
    expect(source).toContain('import { z } from "zod";');
    expect(source).toContain('export type { AllowedVerdict, FailErrorVerdict, FailSecurityVerdict, Verdict } from "aoa-client-js";');
    expect(source).toContain("export const ResolveResponseSchema =");
    assertSyntacticallyValid(source);
    assertGeneratedFileTypechecks(source);
  });

  it("generates real, valid, typechecking Params/Result interfaces for a mix of real endpoint shapes", async () => {
    stubFetchJson(fakeManifest([CANCEL_ORDER_ENDPOINT, PING_ENDPOINT, DEMO_OPTIONAL_ENDPOINT]));
    const source = await generateClient("https://x/client-manifest.json");

    expect(source).toContain(`// Manifest version: ${fakeManifest([]).manifest_version}`);
    expect(source).toContain("export interface CancelOrderParams {");
    expect(source).toContain("order_id: number;");
    expect(source).toContain("export interface CancelOrderResult {");
    expect(source).toContain("status: string;");
    expect(source).toContain("export interface PingParams {");
    expect(source).toContain("export interface PingResult {");
    expect(source).toContain("message: string;");
    expect(source).toContain("export interface DemoOptionalParams {");
    expect(source).toContain("count: number;");
    expect(source).toContain("note?: string | null;");
    expect(source).toContain("priority: DemoOptionalParamsPriority;");
    expect(source).toContain("address: DemoOptionalParamsAddress;");
    expect(source).toContain('export type DemoOptionalParamsPriority = "low" | "high";');
    expect(source).toContain("export interface DemoOptionalParamsAddress {");
    expect(source).toContain("export interface DemoOptionalResult {");
    expect(source).toContain("echoed_note?: string | null;");

    assertSyntacticallyValid(source);
    assertGeneratedFileTypechecks(source);
  });

  it("disambiguates two endpoints whose action class name collides", async () => {
    const duplicate = { ...CANCEL_ORDER_ENDPOINT, operation: "POST /admin/cancel-order", route: { method: "POST", path: "/admin/cancel-order" } };
    stubFetchJson(fakeManifest([CANCEL_ORDER_ENDPOINT, duplicate]));
    const source = await generateClient("https://x/client-manifest.json");
    expect(source).toContain("export interface CancelOrderParams {");
    expect(source).toContain("export interface CancelOrder2Params {");
    expect(source).toContain("export interface CancelOrder2Result {");
    assertSyntacticallyValid(source);
    assertGeneratedFileTypechecks(source);
  });

  it("generates a ResolveResponseSchema that actually validates a real-shaped ResolveResponse at runtime", async () => {
    stubFetchJson(fakeManifest([]));
    const source = await generateClient("https://x/client-manifest.json");
    const match = /export const ResolveResponseSchema = ([\s\S]+);\n$/.exec(source);
    expect(match).not.toBeNull();
    const { z } = await import("zod");
    // eslint-disable-next-line @typescript-eslint/no-implied-eval
    const schema = new Function("z", `return (${match![1]});`)(z);
    const parsed = schema.parse({
      version: 1,
      results: [{ kind: "AllowedVerdict" }, { kind: "FailSecurityVerdict", reason: "only the order owner can cancel" }],
    });
    expect(parsed.results[1]).toEqual({ kind: "FailSecurityVerdict", reason: "only the order owner can cancel" });
    expect(() => schema.parse({ version: 1, results: [{ kind: "FailSecurityVerdict" }] })).toThrow();
  });
});
