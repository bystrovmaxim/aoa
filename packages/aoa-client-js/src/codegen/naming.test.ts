// packages/aoa-client-js/src/codegen/naming.test.ts
import { describe, expect, it } from "vitest";

import { assertValidBaseName, deriveEndpointBaseName, isReservedWord, NameRegistry } from "./naming.ts";

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

describe("isReservedWord", () => {
  it("recognizes ECMAScript reserved words", () => {
    expect(isReservedWord("delete")).toBe(true);
    expect(isReservedWord("class")).toBe(true);
    expect(isReservedWord("import")).toBe(true);
  });

  it("is case-sensitive -- a capitalized form is not reserved", () => {
    expect(isReservedWord("Delete")).toBe(false);
    expect(isReservedWord("Class")).toBe(false);
  });

  it("returns false for an ordinary identifier", () => {
    expect(isReservedWord("CancelOrder")).toBe(false);
  });
});

describe("assertValidBaseName (audit finding 3)", () => {
  const endpoint = (name: string) => ({ name, operation: `POST /${name}` });

  it("accepts an ordinary PascalCase base", () => {
    expect(() => assertValidBaseName("CancelOrder", endpoint("CancelOrderAction"))).not.toThrow();
  });

  it("rejects an empty base (e.g. an action literally named just 'Action')", () => {
    expect(() => assertValidBaseName("", endpoint("Action"))).toThrow(/empty/);
  });

  it("rejects a base containing characters invalid in a TypeScript identifier", () => {
    expect(() => assertValidBaseName("Weird.Name", endpoint("Weird.Name"))).toThrow(/invalid.*"Weird\.Name"/);
    expect(() => assertValidBaseName("Has Space", endpoint("Has Space"))).toThrow();
    expect(() => assertValidBaseName("Has-Hyphen", endpoint("Has-HyphenAction"))).toThrow();
  });

  it("rejects a base that is a bare lowercase reserved word", () => {
    expect(() => assertValidBaseName("delete", endpoint("deleteAction"))).toThrow(/reserved/);
  });

  it("names the offending operation and server action in the error message", () => {
    expect(() => assertValidBaseName("", endpoint("Action"))).toThrow(/POST \/Action/);
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

  it("also reserves the base's own derived Params/Result forms (audit finding 2)", () => {
    const registry = new NameRegistry();
    registry.claimBase("Foo", "op-1");
    // A second, unrelated operation whose OWN base happens to equal "Foo"'s derived
    // Result name must not be allowed to collide with it -- "FooResult" is already
    // reserved as op-1's own Result interface.
    expect(registry.claimBase("FooResult", "op-2")).toBe("FooResult2");
  });

  it("disambiguates a base whose derived form collides with an unrelated hoisted name claimed first", () => {
    const registry = new NameRegistry();
    // Simulates a nested $defs entry hoisted under this exact string by some earlier,
    // unrelated endpoint (see generate-client.ts's use of claimName for hoisting).
    registry.claimName("FooResult", "op-hoisted");
    // Endpoint B's own base "Foo" would derive "FooResult" as its own Result interface
    // name -- that string is already taken, so the base itself must be disambiguated,
    // not just silently produce a colliding Result interface later.
    expect(registry.claimBase("Foo", "op-b")).toBe("Foo2");
  });

  it("is idempotent for claimBase reclaiming its own already-reserved derived forms", () => {
    const registry = new NameRegistry();
    expect(registry.claimBase("Foo", "op-1")).toBe("Foo");
    // Re-claiming under the SAME operation must not treat its own reserved
    // "FooParams"/"FooResult" as a collision with itself.
    expect(registry.claimBase("Foo", "op-1")).toBe("Foo");
  });
});

describe("NameRegistry.claimName", () => {
  it("returns the name unchanged for the first claimant", () => {
    const registry = new NameRegistry();
    expect(registry.claimName("FooResultBar", "op-1")).toBe("FooResultBar");
  });

  it("disambiguates a second, different operation claiming the same exact name", () => {
    const registry = new NameRegistry();
    expect(registry.claimName("FooResultBar", "op-1")).toBe("FooResultBar");
    expect(registry.claimName("FooResultBar", "op-2")).toBe("FooResultBar2");
  });

  it("is idempotent for the same operation reclaiming its own name", () => {
    const registry = new NameRegistry();
    expect(registry.claimName("FooResultBar", "op-1")).toBe("FooResultBar");
    expect(registry.claimName("FooResultBar", "op-1")).toBe("FooResultBar");
  });

  it("does not reserve derived Params/Result forms for a claimed name (unlike claimBase)", () => {
    const registry = new NameRegistry();
    registry.claimName("Foo", "op-1");
    // "Foo" itself is taken, but "FooParams"/"FooResult" are NOT reserved by claimName
    // -- a hoisted name is always a leaf declaration, never itself further suffixed.
    expect(registry.claimBase("FooParams", "op-2")).toBe("FooParams");
  });
});
