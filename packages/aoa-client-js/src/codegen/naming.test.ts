// packages/aoa-client-js/src/codegen/naming.test.ts
import { describe, expect, it } from "vitest";

import { deriveEndpointBaseName, NameRegistry } from "./naming.ts";

describe("deriveEndpointBaseName", () => {
  it("strips a trailing Action suffix", () => {
    expect(deriveEndpointBaseName("CancelOrderAction")).toBe("CancelOrder");
    expect(deriveEndpointBaseName("PingAction")).toBe("Ping");
  });

  it("leaves a name without the Action suffix unchanged", () => {
    expect(deriveEndpointBaseName("CancelOrder")).toBe("CancelOrder");
  });

  it("leaves the bare name 'Action' unchanged (suffix must not consume the whole name)", () => {
    expect(deriveEndpointBaseName("Action")).toBe("Action");
  });
});

describe("NameRegistry", () => {
  it("returns the base name unchanged for the first claimant", () => {
    const registry = new NameRegistry();
    expect(registry.claimBase("CancelOrder", "POST /actions/cancel-order")).toBe("CancelOrder");
  });

  it("is idempotent for the same operation reclaiming its own base", () => {
    const registry = new NameRegistry();
    expect(registry.claimBase("CancelOrder", "POST /actions/cancel-order")).toBe("CancelOrder");
    expect(registry.claimBase("CancelOrder", "POST /actions/cancel-order")).toBe("CancelOrder");
  });

  it("disambiguates a second, different operation claiming the same base name", () => {
    const registry = new NameRegistry();
    expect(registry.claimBase("CancelOrder", "POST /actions/cancel-order")).toBe("CancelOrder");
    expect(registry.claimBase("CancelOrder", "POST /admin/cancel-order")).toBe("CancelOrder2");
  });

  it("disambiguates sequentially across more than two collisions", () => {
    const registry = new NameRegistry();
    expect(registry.claimBase("Widget", "op-1")).toBe("Widget");
    expect(registry.claimBase("Widget", "op-2")).toBe("Widget2");
    expect(registry.claimBase("Widget", "op-3")).toBe("Widget3");
  });

  it("skips a disambiguated name that a later-unrelated claim already owns", () => {
    const registry = new NameRegistry();
    expect(registry.claimBase("Widget2", "op-preexisting")).toBe("Widget2");
    expect(registry.claimBase("Widget", "op-1")).toBe("Widget");
    // "Widget2" is already taken by an unrelated operation, so the second Widget claimant must skip past it.
    expect(registry.claimBase("Widget", "op-2")).toBe("Widget3");
  });

  it("does not disambiguate names that are already distinct", () => {
    const registry = new NameRegistry();
    expect(registry.claimBase("CancelOrder", "op-1")).toBe("CancelOrder");
    expect(registry.claimBase("Ping", "op-2")).toBe("Ping");
  });
});
