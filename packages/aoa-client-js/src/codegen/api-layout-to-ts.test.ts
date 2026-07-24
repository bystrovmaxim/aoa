// packages/aoa-client-js/src/codegen/api-layout-to-ts.test.ts
import ts from "typescript";
import { describe, expect, it } from "vitest";

import { renderApiLayout } from "./api-layout-to-ts.ts";
import { buildLayout, type LayoutEndpoint } from "../path-layout.ts";

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

  // Audit finding 3: a PascalCase base is a perfectly fine TypeScript identifier and not
  // itself a reserved word, but lowerFirst's case-folded local-variable form can land on
  // one -- "Delete" -> "delete" is a SyntaxError as `const delete = ...`, invisible to
  // naming.ts's own base-name validation (a type-namespace check, never sees the
  // lowerFirst transformation at all).
  it("rejects a base whose lowerFirst local variable name is an ECMAScript reserved word", () => {
    const layout = buildLayout([ep("POST", "/actions/delete", "Delete")]);
    expect(() => renderApiLayout(layout)).toThrow(/reserved word "delete"/);
  });

  it("does not reject a base that merely CONTAINS a reserved word as a substring", () => {
    const layout = buildLayout([ep("POST", "/actions/deleted-order", "DeletedOrder")]);
    expect(() => renderApiLayout(layout)).not.toThrow();
  });

  // Audit finding 4: NameRegistry's own base-name claim is case-sensitive, so "Widget"
  // and "widget" pass it as two distinct, non-colliding bases -- but BOTH case-fold to
  // the same descriptor ("WIDGET_DESCRIPTOR") and local variable ("widget") once
  // api-layout-to-ts.ts's lowerFirst/toScreamingSnakeCase are applied, a collision
  // NameRegistry alone can't see.
  it("disambiguates a descriptor const and local variable that only collide after case-folding", () => {
    const layout = buildLayout([ep("POST", "/w1", "Widget"), ep("POST", "/w2", "widget")]);
    const { factoriesSource } = renderApiLayout(layout);

    // claimName disambiguates the whole candidate string it's given -- since the
    // descriptor candidate already has "_DESCRIPTOR" appended before claiming, the
    // numeric suffix lands at the very end ("WIDGET_DESCRIPTOR2"), not "WIDGET2_DESCRIPTOR".
    expect(factoriesSource).toContain("const WIDGET_DESCRIPTOR =");
    expect(factoriesSource).toContain("const WIDGET_DESCRIPTOR2 =");
    expect(factoriesSource.match(/const WIDGET_DESCRIPTOR =/g)).toHaveLength(1);
    expect(factoriesSource.match(/const WIDGET_DESCRIPTOR2 =/g)).toHaveLength(1);

    expect(factoriesSource).toContain("const widget = makeGatePrimitive<WidgetParams>");
    expect(factoriesSource).toContain("const widget2 = makeGatePrimitive<widgetParams>");
    // Once per factory (createGateApi + createApi each declare their own local "widget"
    // in their own function body -- different scopes, not a second collision).
    expect(factoriesSource.match(/const widget = /g)).toHaveLength(2);
    expect(factoriesSource.match(/const widget2 = /g)).toHaveLength(2);

    assertSyntacticallyValid(
      [
        "interface GatePrimitive<P> { verdict(p: P): unknown; can(p: P): unknown; }",
        "declare function makeGatePrimitive<P>(engine: unknown, op: string): GatePrimitive<P>;",
        "declare const engine: unknown;",
        "interface WidgetParams {}",
        "interface widgetParams {}",
        factoriesSource,
      ].join("\n"),
    );
  });
});
