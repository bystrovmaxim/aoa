// src/lib/erdFilterPresence.test.ts
import { describe, expect, it } from "vitest";
import type { ErdDiff, ErdEntity, ErdGraphPayload } from "@/lib/buildDotSource";
import { changeDiskUri, changesOnDiagram, domainsOn, filterGraphByChanges, onScreen, tablesToDraw, withOneHop } from "./erdFilterPresence";

const table = (id: string, domain: string, kind: string, diff?: ErdDiff, rowDiff?: ErdDiff): ErdEntity =>
  ({ id, label: id, domain_qualname: domain, entity_kind: kind, diff, fields: [{ name: "id", type: "str", diff: rowDiff }] }) as unknown as ErdEntity;
const domainOf = (entity: ErdEntity) => entity.domain_qualname ?? null;

describe("the Changes rows of a diagram (its base)", () => {
  it("are the kinds of change the diagram has, in the filter's order", () => {
    expect(changesOnDiagram([table("a", "d", "core", "unchanged"), table("b", "d", "core", "added"), table("c", "d", "core", "unchanged", "changed")])).toEqual(["added", "changed", "unchanged"]);
  });

  it("are none when nothing on the diagram changed", () => {
    expect(changesOnDiagram([table("a", "d", "core", "unchanged"), table("b", "d", "core", "unchanged")])).toEqual([]);
  });

  it("are none when one version is drawn", () => {
    expect(changesOnDiagram([table("a", "d", "core")])).toEqual([]);
  });
});

describe("what the screen shows of each filter", () => {
  it("is every domain, kind and change of the tables shown — a 1-hop neighbour counts like any table, for its own domain", () => {
    const shown = onScreen([table("w", "inventory", "core", "added"), table("n", "catalog", "detail", "unchanged")], domainOf);
    expect([...shown.domains].sort()).toEqual(["catalog", "inventory"]);
    expect([...shown.kinds].sort()).toEqual(["core", "detail"]);
    expect([...shown.changes].sort()).toEqual(["added", "unchanged"]);
  });
});

describe("a domain switched off", () => {
  // The offers slice carries Showcase as its 1-hop neighbour; the showcases slice is switched off.
  const offersSlice = {
    entities: [table("Offer", "offers", "core"), table("Showcase", "showcases", "core")],
    relations: [{ source: "Offer", target: "Showcase" }],
  } as unknown as ErdGraphPayload;
  const base = {
    entities: [...offersSlice.entities, table("Game", "showcases", "core")],
    relations: [...offersSlice.relations!, { source: "Showcase", target: "Game" }],
  } as unknown as ErdGraphPayload;
  const tabs = { Offers: "offers", Showcases: " showcases " };
  const drawn = (tabsOn: string[], includeOneHop: boolean) =>
    tablesToDraw(offersSlice, base, domainsOn(tabs, new Set(tabsOn)), domainOf, includeOneHop);

  it("leaves none of its tables with 1-hop off, not even one another domain's slice carries as a neighbour", () => {
    const shown = drawn(["Offers"], false);
    expect(shown.entities.map((entity) => entity.id)).toEqual(["Offer"]);
    expect(shown.relations).toEqual([]);
  });

  it("is still reached by 1-hop, one line away from the tables left and no further", () => {
    const shown = drawn(["Offers"], true);
    expect(shown.entities.map((entity) => entity.id)).toEqual(["Offer", "Showcase"]);
    expect(shown.relations).toEqual([{ source: "Offer", target: "Showcase" }]);
  });

  it("shows its tables again once it is switched on", () => {
    expect(drawn(["Offers", "Showcases"], false).entities.map((entity) => entity.id)).toEqual(["Offer", "Showcase"]);
  });
});

describe("the domains switched on", () => {
  it("are the trimmed domains of the tabs switched on", () => {
    expect([...domainsOn({ Offers: "offers", Showcases: " showcases " }, new Set(["Showcases"]))]).toEqual(["showcases"]);
  });
});

describe("a kind of change switched off", () => {
  const graph = {
    entities: [table("New", "d", "core", "added"), table("Same", "d", "core", "unchanged"), table("Far", "d", "core", "unchanged")],
    relations: [{ source: "New", target: "Same" }, { source: "Same", target: "Far" }],
  } as unknown as ErdGraphPayload;

  it("hides its tables and their lines, as a domain or a kind switched off does", () => {
    const kept = filterGraphByChanges(graph, new Set(["unchanged"]));
    expect(kept.entities.map((entity) => entity.id)).toEqual(["New"]);
    expect(kept.relations).toEqual([]);
  });

  it("is brought back by 1-hop one line away from the tables left — and no further", () => {
    const shown = withOneHop(filterGraphByChanges(graph, new Set(["unchanged"])), graph);
    expect(shown.entities.map((entity) => entity.id)).toEqual(["New", "Same"]);
    expect(shown.relations).toEqual([{ source: "New", target: "Same" }]);
  });
});

describe("the disk of a status", () => {
  const svg = (uri: string) => decodeURIComponent(uri);

  it("gives unchanged its sign, whatever paints", () => {
    expect(svg(changeDiskUri("unchanged"))).toContain(">=<");
    expect(changeDiskUri("unchanged", false)).toBe(changeDiskUri("unchanged"));
  });

  it("greys a change only when something else paints, and keeps its sign", () => {
    expect(svg(changeDiskUri("added"))).toContain("#16a34a");
    expect(svg(changeDiskUri("added", false))).not.toContain("#16a34a");
    expect(svg(changeDiskUri("added", false))).toContain(">+<");
  });
});
