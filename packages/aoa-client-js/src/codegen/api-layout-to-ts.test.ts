// packages/aoa-client-js/src/codegen/api-layout-to-ts.test.ts
import ts from "typescript";
import { describe, expect, it } from "vitest";

import { renderApiLayout } from "./api-layout-to-ts.ts";
import { buildLayout, type LayoutEndpoint } from "./path-layout.ts";

function ep(method: string, path: string, baseName: string): LayoutEndpoint {
  return { operation: `${method} ${path}`, method, path, baseName };
}

function assertSyntacticallyValid(source: string): void {
  const result = ts.transpileModule(source, {
    reportDiagnostics: true,
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext },
  });
  const errors = (result.diagnostics ?? []).filter((d) => d.category === ts.DiagnosticCategory.Error);
  if (errors.length > 0) {
    throw new Error(
      `Not valid TypeScript:\n${errors.map((d) => ts.flattenDiagnosticMessageText(d.messageText, "\n")).join("\n")}\n---\n${source}`,
    );
  }
}

describe("renderApiLayout -- types", () => {
  it("renders a bracket-only entry with no alias", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder")]);
    const { typesSource } = renderApiLayout(layout);
    expect(typesSource).toContain("export interface GateApi {");
    expect(typesSource).toContain('"/actions/cancel-order": GatePrimitive<CancelOrderParams>;');
    expect(typesSource).toContain("export interface CallableApi {");
    expect(typesSource).toContain('"/actions/cancel-order": CallablePrimitive<CancelOrderParams, CancelOrderResult>;');
    assertSyntacticallyValid(`interface GatePrimitive<P> {}\ninterface CallablePrimitive<P,R> {}\n${typesSource}`);
  });

  it("renders a single-segment dot alias alongside the bracket entry", () => {
    const layout = buildLayout([ep("GET", "/orders", "Orders")]);
    const { typesSource } = renderApiLayout(layout);
    expect(typesSource).toContain('"/orders": GatePrimitive<OrdersParams>;');
    expect(typesSource).toContain("orders: GatePrimitive<OrdersParams>;");
  });

  it("renders a nested multi-segment dot alias", () => {
    const layout = buildLayout([ep("GET", "/actions/ping", "Ping")]);
    const { typesSource } = renderApiLayout(layout);
    expect(typesSource).toContain("actions: {\n      ping: GatePrimitive<PingParams>;\n    };");
    assertSyntacticallyValid(`interface GatePrimitive<P> {}\ninterface CallablePrimitive<P,R> {}\n${typesSource}`);
  });

  it("omits the dot alias entirely for a demoted branch/leaf collision, while keeping the deeper path", () => {
    const layout = buildLayout([ep("GET", "/admin", "AdminRoot"), ep("GET", "/admin/settings", "AdminSettings")]);
    const { typesSource } = renderApiLayout(layout);
    // "/admin" itself is only reachable via the bracket key -- no bare `admin: GatePrimitive<AdminRootParams>` leaf.
    expect(typesSource).not.toMatch(/\n\s*admin: GatePrimitive<AdminRootParams>;/);
    expect(typesSource).toContain('"/admin": GatePrimitive<AdminRootParams>;');
    expect(typesSource).toContain('"/admin/settings": GatePrimitive<AdminSettingsParams>;');
    expect(typesSource).toContain("admin: {\n      settings: GatePrimitive<AdminSettingsParams>;\n    };");
  });

  it("omits a method bucket key entirely for a method with zero endpoints (not present at all, not an empty object)", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder")]);
    const { typesSource } = renderApiLayout(layout);
    expect(typesSource).not.toContain("get:");
    expect(typesSource).not.toContain("delete:");
  });
});

describe("renderApiLayout -- descriptors + factories", () => {
  it("names the descriptor constant from a SCREAMING_SNAKE_CASE of the base name", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder")]);
    const { factoriesSource } = renderApiLayout(layout);
    expect(factoriesSource).toContain('const CANCEL_ORDER_DESCRIPTOR = { method: "POST", path: "/actions/cancel-order" };');
  });

  it("disambiguates the descriptor name for a disambiguated base name (…2 suffix from NameRegistry)", () => {
    const layout = buildLayout([ep("POST", "/admin/cancel-order", "CancelOrder2")]);
    const { factoriesSource } = renderApiLayout(layout);
    expect(factoriesSource).toContain('const CANCEL_ORDER2_DESCRIPTOR');
  });

  it("createGateApi builds one makeGatePrimitive call per endpoint, keyed by operation", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder")]);
    const { factoriesSource } = renderApiLayout(layout);
    expect(factoriesSource).toContain("export function createGateApi(engine: AoaEngine): GateApi {");
    expect(factoriesSource).toContain('const cancelOrder = makeGatePrimitive<CancelOrderParams>(engine, "POST /actions/cancel-order");');
    expect(factoriesSource).toContain('"/actions/cancel-order": cancelOrder,');
  });

  it("createApi builds one makeCallablePrimitive call per endpoint, referencing its descriptor and actionInvoker", () => {
    const layout = buildLayout([ep("POST", "/actions/cancel-order", "CancelOrder")]);
    const { factoriesSource } = renderApiLayout(layout);
    expect(factoriesSource).toContain(
      "export function createApi(engine: AoaEngine, actionInvoker: ActionInvoker): CallableApi {",
    );
    expect(factoriesSource).toContain(
      'const cancelOrder = makeCallablePrimitive<CancelOrderParams, CancelOrderResult>(engine, "POST /actions/cancel-order", CANCEL_ORDER_DESCRIPTOR, actionInvoker);',
    );
  });

  it("shares exactly one Primitive instance between its bracket key and its dot-alias position", () => {
    const layout = buildLayout([ep("GET", "/actions/ping", "Ping")]);
    const { factoriesSource } = renderApiLayout(layout);
    // Both the bracket entry and the nested alias reference the same local variable "ping".
    expect(factoriesSource).toContain('"/actions/ping": ping,');
    expect(factoriesSource).toMatch(/actions: \{\n\s*ping: ping,\n\s*\}/);
    expect(factoriesSource.match(/const ping = makeGatePrimitive/g)).toHaveLength(1);
  });
});
