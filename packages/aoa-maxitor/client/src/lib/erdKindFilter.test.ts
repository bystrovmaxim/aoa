// src/lib/erdKindFilter.test.ts
import { describe, expect, it } from "vitest";
import type { ErdEntity, ErdGraphPayload } from "@/lib/buildDotSource";
import { entityKindOf, filterGraphByKinds, kindsOnDiagram } from "@/lib/erdKindFilter";

const entity = (id: string, entity_kind?: string): ErdEntity => ({ id, label: id, fields: [], entity_kind }) as ErdEntity;

// Payment heads a container of two specializations; Customer links to Order; Currency is a dictionary.
const payload = (): ErdGraphPayload => ({
  entities: [
    entity("Order", "core"),
    entity("Customer", "core"),
    entity("Currency", "enum"),
    entity("Payment", "core"),
    entity("Card", "spec"),
    entity("Bank", "spec"),
    entity("Legacy"),
  ],
  relations: [
    { source: "Order", target: "Customer", relationship_kind: "association" },
    { source: "Order", target: "Currency", relationship_kind: "reference" },
    { source: "Payment", target: "Payment:kind", relationship_kind: "specialization" },
    { source: "Card", target: "Payment", relationship_kind: "generalization" },
  ],
  groups: [{ group_id: "Payment:kind", label: "kind", members: ["Card", "Bank"] }] as ErdGraphPayload["groups"],
});

describe("filterGraphByKinds", () => {
  it("hides a kind's tables and every line touching them", () => {
    const out = filterGraphByKinds(payload(), new Set(["enum"]));

    expect(out.entities.map((e) => e.id)).not.toContain("Currency");
    expect(out.relations).not.toContainEqual(expect.objectContaining({ target: "Currency" }));
    expect(out.relations).toContainEqual(expect.objectContaining({ source: "Order", target: "Customer" }));
  });

  it("drops a container left with fewer than two members, and the line into it", () => {
    const out = filterGraphByKinds(payload(), new Set(["spec"]));

    expect(out.groups).toEqual([]);
    expect(out.relations.some((r) => r.relationship_kind === "specialization")).toBe(false);
    expect(out.relations.some((r) => r.relationship_kind === "generalization")).toBe(false);
  });

  it("files a table without a kind under unknown", () => {
    expect(entityKindOf(entity("Legacy"))).toBe("unknown");
    expect(filterGraphByKinds(payload(), new Set(["unknown"])).entities.map((e) => e.id)).not.toContain("Legacy");
  });

  it("keeps a neighbour when only the table that linked it is hidden", () => {
    // Customer is on screen through Order; hiding Order's kind must not hide Customer of another kind.
    const data = { ...payload(), entities: [entity("Order", "detail"), entity("Customer", "core")] };

    const out = filterGraphByKinds(data, new Set(["detail"]));

    expect(out.entities.map((e) => e.id)).toEqual(["Customer"]);
    expect(out.relations).toEqual([]);
  });

  it("returns the same payload when every kind is on", () => {
    const data = payload();

    expect(filterGraphByKinds(data, new Set())).toBe(data);
  });
});

describe("the kinds a diagram's filter offers (spec 029, FR-044)", () => {
  const kinds = [
    { entity_kind: "core", label: "Core" },
    { entity_kind: "enum", label: "Enumeration" },
    { entity_kind: "spec", label: "Specialization" },
  ];

  it("are only the kinds of the diagram's tables, in the named order", () => {
    const entities = [{ id: "a", entity_kind: "spec" }, { id: "b", entity_kind: "core" }];
    expect(kindsOnDiagram(kinds, entities).map((k) => k.entity_kind)).toEqual(["core", "spec"]);
  });

  it("keep a kind that is switched off: it is counted before kinds are filtered", () => {
    const shownBeforeKinds = [{ id: "a", entity_kind: "core" }, { id: "b", entity_kind: "enum" }];
    const switchedOff = new Set(["enum"]);
    const onScreen = shownBeforeKinds.filter((e) => !switchedOff.has(e.entity_kind));
    expect(kindsOnDiagram(kinds, shownBeforeKinds).map((k) => k.entity_kind)).toEqual(["core", "enum"]);
    expect(kindsOnDiagram(kinds, onScreen).map((k) => k.entity_kind)).toEqual(["core"]);
  });
});
