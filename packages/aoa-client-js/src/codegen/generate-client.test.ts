// packages/aoa-client-js/src/codegen/generate-client.test.ts
import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import ts from "typescript";
import { afterEach, describe, expect, it, vi } from "vitest";

import { generateClient } from "./generate-client.ts";

const packageRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..", "..");
const tscBinary = path.join(packageRoot, "node_modules", ".bin", "tsc");

/**
 * Writes the generated source to a real temp file and dynamically imports it, actually
 * *running* the generated createGateApi/createApi against a real AoaEngine -- proof the
 * layout renderer produces code that works, not just code that parses. The self-import
 * `from "aoa-client-js"` is rewritten to a relative path to the real src/index.ts (same
 * package, just repointed for this in-repo test) so plain Node/vite module resolution
 * -- no mocking, no alias config -- finds it.
 */
async function loadGeneratedModule(source: string): Promise<{ module: Record<string, unknown>; cleanup: () => void }> {
  const dir = mkdtempSync(path.join(packageRoot, ".codegen-runtime-check-"));
  const filePath = path.join(dir, "generated.ts");
  const relativeRuntimePath = path.relative(dir, path.join(packageRoot, "src", "index.ts"));
  const importPath = relativeRuntimePath.startsWith(".") ? relativeRuntimePath : `./${relativeRuntimePath}`;
  const rewritten = source.replaceAll('"aoa-client-js"', JSON.stringify(importPath));
  writeFileSync(filePath, rewritten, "utf8");
  const module = (await import(pathToFileURL(filePath).href)) as Record<string, unknown>;
  return { module, cleanup: () => rmSync(dir, { recursive: true, force: true }) };
}

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

    // GateApi/CallableApi layout: full-path bracket entries always; a nested dot alias
    // for the clean multi-segment /actions/ping (no hyphen), none at all for
    // /actions/cancel-order (hyphenated) or /actions/demo-optional (ditto).
    expect(source).toContain("export interface GateApi {");
    expect(source).toContain("export interface CallableApi {");
    expect(source).toContain('"/actions/cancel-order": GatePrimitive<CancelOrderParams>;');
    expect(source).toContain('"/actions/cancel-order": CallablePrimitive<CancelOrderParams, CancelOrderResult>;');
    expect(source).toContain('"/actions/ping": GatePrimitive<PingParams>;');
    expect(source).toMatch(/actions: \{\n\s*ping: GatePrimitive<PingParams>;\n\s*\};/);
    expect(source).not.toContain("cancel-order: ");
    expect(source).not.toContain("demo-optional: ");
    expect(source).toContain("export function createGateApi(engine: AoaEngine): GateApi {");
    expect(source).toContain("export function createApi(engine: AoaEngine, actionInvoker: ActionInvoker): CallableApi {");
    expect(source).toContain('const CANCEL_ORDER_DESCRIPTOR = { method: "POST", path: "/actions/cancel-order" };');

    assertSyntacticallyValid(source);
    assertGeneratedFileTypechecks(source);
  });

  it("disambiguates an endpoint's own Params name from an unrelated endpoint's hoisted $defs name (audit finding 2)", async () => {
    // Endpoint A's RESULT schema hoists a nested $defs entry named "XParams" -- the
    // hoisted name becomes "AResult" + "XParams" = "AResultXParams" (see
    // generate-client.ts's resolveRefName callback). Endpoint B's own base, "AResultX",
    // independently derives the EXACT SAME string as its own Params interface name
    // ("AResultX" + "Params"). Before the fix, NameRegistry never saw hoisted names at
    // all, so this collision went undetected and one declaration silently won (via
    // TypeScript's own interface declaration merging) at the other's expense.
    const endpointA = {
      operation: "POST /a",
      name: "AAction",
      domain: "TestDomain",
      description: "Endpoint A",
      route: { method: "POST", path: "/a" },
      params_schema: { additionalProperties: false, properties: {}, title: "Params", type: "object" },
      result_schema: {
        $defs: { XParams: { properties: { z: { title: "Z", type: "string" } }, required: ["z"], title: "XParams", type: "object" } },
        additionalProperties: false,
        properties: { x_ref: { $ref: "#/$defs/XParams" } },
        required: ["x_ref"],
        title: "Result",
        type: "object",
      },
    };
    const endpointB = {
      operation: "POST /a-result-x",
      name: "AResultXAction",
      domain: "TestDomain",
      description: "Endpoint B -- unrelated to A, but its own base textually collides with A's hoisted name",
      route: { method: "POST", path: "/a-result-x" },
      params_schema: {
        additionalProperties: false,
        properties: { own_field: { title: "Own Field", type: "boolean" } },
        required: ["own_field"],
        title: "Params",
        type: "object",
      },
      result_schema: { additionalProperties: false, properties: {}, title: "Result", type: "object" },
    };
    stubFetchJson(fakeManifest([endpointA, endpointB]));
    const source = await generateClient("https://x/client-manifest.json");

    // A's hoisted interface keeps the clean name and its own field.
    expect(source).toContain("export interface AResultXParams {");
    expect(source).toContain("z: string;");
    // B's base was disambiguated to avoid colliding with A's hoisted name -- its own
    // Params interface is NOT "AResultXParams" (that would silently merge with A's),
    // it's the next free name, carrying B's own, distinct field.
    expect(source).not.toMatch(/export interface AResultXParams \{\s*own_field/);
    expect(source).toContain("export interface AResultX2Params {");
    expect(source).toContain("own_field: boolean;");

    // Exactly one declaration of each name -- neither silently overwrote the other.
    expect(source.match(/export interface AResultXParams \{/g)).toHaveLength(1);
    expect(source.match(/export interface AResultX2Params \{/g)).toHaveLength(1);

    assertSyntacticallyValid(source);
    assertGeneratedFileTypechecks(source);
  });

  it("rejects a server action whose name would derive a reserved-word local variable (audit finding 3, case 1)", async () => {
    const endpoint = { ...CANCEL_ORDER_ENDPOINT, operation: "POST /actions/delete", name: "DeleteAction", route: { method: "POST", path: "/actions/delete" } };
    stubFetchJson(fakeManifest([endpoint]));
    await expect(generateClient("https://x/client-manifest.json")).rejects.toThrow(/reserved word "delete"/);
  });

  it("rejects a server action whose name contains characters invalid in a TypeScript identifier (audit finding 3, case 2)", async () => {
    const endpoint = { ...CANCEL_ORDER_ENDPOINT, operation: "POST /actions/weird", name: "Weird.Name", route: { method: "POST", path: "/actions/weird" } };
    stubFetchJson(fakeManifest([endpoint]));
    await expect(generateClient("https://x/client-manifest.json")).rejects.toThrow(/invalid.*"Weird\.Name"/);
  });

  it("rejects a server action with a literally empty name, which derives an empty base (audit finding 3, case 3)", async () => {
    // deriveEndpointBaseName("Action") is explicitly preserved as "Action" (the suffix
    // strip requires more than just the suffix itself) -- only a literally empty
    // ManifestEndpoint.name (a valid, if degenerate, `str` -- the field has no format
    // constraint) derives an empty base.
    const endpoint = { ...CANCEL_ORDER_ENDPOINT, operation: "POST /actions/bare", name: "", route: { method: "POST", path: "/actions/bare" } };
    stubFetchJson(fakeManifest([endpoint]));
    await expect(generateClient("https://x/client-manifest.json")).rejects.toThrow(/empty/);
  });

  it("disambiguates two endpoints whose base names only collide after case-folding, end to end (audit finding 4)", async () => {
    const widget = { ...PING_ENDPOINT, operation: "POST /w1", name: "WidgetAction", route: { method: "POST", path: "/w1" } };
    const widgetLower = { ...PING_ENDPOINT, operation: "POST /w2", name: "widgetAction", route: { method: "POST", path: "/w2" } };
    stubFetchJson(fakeManifest([widget, widgetLower]));
    const source = await generateClient("https://x/client-manifest.json");

    expect(source).toContain("export interface WidgetParams {");
    expect(source).toContain("export interface widgetParams {");
    expect(source).toContain("const WIDGET_DESCRIPTOR =");
    expect(source).toContain("const WIDGET_DESCRIPTOR2 =");
    expect(source).toContain("const widget = makeGatePrimitive<WidgetParams>");
    expect(source).toContain("const widget2 = makeGatePrimitive<widgetParams>");

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
    expect(source).toContain('const CANCEL_ORDER2_DESCRIPTOR');
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

  it("createGateApi and createApi actually work end to end against a real AoaEngine, both bracket and dot-alias forms", async () => {
    stubFetchJson(fakeManifest([CANCEL_ORDER_ENDPOINT, PING_ENDPOINT]));
    const source = await generateClient("https://x/client-manifest.json");
    const { module, cleanup } = await loadGeneratedModule(source);
    try {
      const { AoaEngine } = await import("../index.ts");
      let capturedBody: { items: Array<{ operation: string; params: unknown }> } | undefined;
      const fetchImpl = (async (_url: string, init: RequestInit) => {
        capturedBody = JSON.parse(init.body as string);
        return new Response(JSON.stringify({ version: 1, results: [{ kind: "AllowedVerdict" }] }), {
          status: 200,
          headers: { "content-type": "application/json" },
        });
      }) as typeof fetch;
      const engine = new AoaEngine({ transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:1" } });

      const createGateApi = module.createGateApi as (engine: unknown) => Record<string, any>;
      const gate = createGateApi(engine);
      await expect(gate.post["/actions/cancel-order"].can({ order_id: 7 })).resolves.toBe(true);
      expect(capturedBody?.items[0]).toEqual({ operation: "POST /actions/cancel-order", params: { order_id: 7 } });

      // The dot alias and the bracket key reference the exact same Primitive instance.
      expect(gate.get.actions.ping).toBe(gate.get["/actions/ping"]);

      const createApi = module.createApi as (engine: unknown, actionInvoker: unknown) => Record<string, any>;
      let capturedInvocation: unknown;
      const actionInvoker = async (invocation: unknown) => {
        capturedInvocation = invocation;
        return { status: "cancelled" };
      };
      const callable = createApi(engine, actionInvoker);
      const result = await callable.post["/actions/cancel-order"].run({ order_id: 7 });
      expect(result).toEqual({ status: "cancelled" });
      expect(capturedInvocation).toEqual({ method: "POST", path: "/actions/cancel-order", body: { order_id: 7 } });
    } finally {
      cleanup();
    }
  });

  it("GateApi's Primitive genuinely lacks .run at the type level, not merely unused at runtime", async () => {
    stubFetchJson(fakeManifest([CANCEL_ORDER_ENDPOINT]));
    const source = await generateClient("https://x/client-manifest.json");
    const dir = mkdtempSync(path.join(packageRoot, ".codegen-tsc-check-"));
    try {
      writeFileSync(path.join(dir, "generated.ts"), source, "utf8");
      writeFileSync(
        path.join(dir, "probe.ts"),
        [
          'import type { GateApi } from "./generated.ts";',
          "declare const gate: GateApi;",
          "// @ts-expect-error GateApi's Primitive has no .run at the type level -- if this",
          "// directive becomes unused, .run leaked into GateApi and tsc will fail below.",
          'gate.post["/actions/cancel-order"].run;',
          "",
        ].join("\n"),
      );
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
          include: ["generated.ts", "probe.ts"],
        }),
      );
      expect(() => execFileSync(tscBinary, ["--noEmit", "-p", dir], { cwd: packageRoot, stdio: "pipe" })).not.toThrow();
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
