// src/lib/useCaseDiff.test.ts
import { describe, expect, it } from "vitest";
import type { ChangedInside, CompareResult } from "@/api/compare";
import { buildActionGlyphDataUrl, buildDomainUseCaseDotBundle, buildRoleActorDataUrl } from "@/lib/buildDomainUseCaseDotSource";
import { filterUseCaseByChanges, markUseCaseDiagram, mergeUseCaseDiagrams, unmarkedUseCase, useCaseCard, useCaseChangeKinds, useCaseChanges, useCaseCounts, useCaseIdAt, withUseCaseOneHop } from "@/lib/useCaseDiff";
import type { DomainUseCaseDiagramPayload, DomainUseCaseEdgeWire } from "@/model/domainUseCaseDiagram";

const action = (id: string, role_ids: string[] = []) => ({ id, label: id, short_label: id, domain_id: "d", domain_short_label: "d", accent_color: "#8b5cf6", role_ids });
const role = (id: string) => ({ id, label: id, short_label: id });
const link = (source_id: string, target_id: string): DomainUseCaseEdgeWire => ({ id: `${source_id}|@check_roles|${target_id}`, edge_kind: "association", source_id, target_id });
const diagram = (actions: string[], roles: string[], edges: DomainUseCaseEdgeWire[] = []): DomainUseCaseDiagramPayload => ({
  domain: { id: "d", label: "D", short_label: "D", accent_color: "#8b5cf6" },
  actions: actions.map((id) => action(id)),
  roles: roles.map(role),
  edges,
});
const compared = (nodes: CompareResult["nodes"] = {}, edges: CompareResult["edges"] = {}): CompareResult => ({ counts: { nodes: { added: 0, removed: 0, changed: 0 }, edges: { added: 0, removed: 0, changed: 0 } }, nodes, edges });
const part = (id: string): ChangedInside[string][number] => ({ kind: "node", id, label: id, type: "Field", group: "Result", status: "added", differences: [] });
const options = { roleActorImageUrl: "role.svg" };

describe("mergeUseCaseDiagrams", () => {
  it("holds every element of either version once, with B's copy", () => {
    const older = diagram(["a", "gone"], ["r"], [link("a", "r")]);
    const newer = diagram(["a", "come"], ["r"], [link("a", "r")]);
    newer.actions[0].label = "B's";
    const merged = mergeUseCaseDiagrams(older, newer);
    expect(merged.actions.map((one) => one.id)).toEqual(["a", "come", "gone"]);
    expect(merged.actions[0].label).toBe("B's");
    expect(merged.edges).toHaveLength(1);
  });

  it("gives one text whichever order the versions list things in", () => {
    const one = mergeUseCaseDiagrams(diagram(["b", "a"], []), diagram(["c"], []));
    const other = mergeUseCaseDiagrams(diagram(["a", "b"], []), diagram(["c"], []));
    expect(buildDomainUseCaseDotBundle(one, "LR", options).dot).toBe(buildDomainUseCaseDotBundle(other, "LR", options).dot);
  });

  it("takes a domain only one version has from that one", () => {
    expect(mergeUseCaseDiagrams(diagram(["a"], []), null).actions.map((one) => one.id)).toEqual(["a"]);
    expect(mergeUseCaseDiagrams(null, diagram(["b"], [])).actions.map((one) => one.id)).toEqual(["b"]);
  });

  it("keeps the roles an action had in either version", () => {
    const older = diagram([], []);
    older.actions = [action("a", ["r1"])];
    const newer = diagram([], []);
    newer.actions = [action("a", ["r2"])];
    expect(mergeUseCaseDiagrams(older, newer).actions[0].role_ids).toEqual(["r1", "r2"]);
  });
});

describe("markUseCaseDiagram", () => {
  const drawn = diagram(["a", "b", "c", "d"], ["r"], [link("a", "r"), link("b", "r")]);

  it("marks an action changed inside, with its own node unchanged", () => {
    const marked = markUseCaseDiagram(drawn, compared(), { a: [part("f")] });
    expect(marked.actions.map((one) => one.diff)).toEqual(["changed", "unchanged", "unchanged", "unchanged"]);
  });

  it("marks every action sharing a changed result", () => {
    const marked = markUseCaseDiagram(drawn, compared(), { a: [part("f")], b: [part("f")] });
    expect(marked.actions.filter((one) => one.diff === "changed").map((one) => one.id)).toEqual(["a", "b"]);
  });

  it("lets an action's own status stand over what changed inside it", () => {
    const marked = markUseCaseDiagram(drawn, compared({ a: "added", b: "removed" }), { a: [part("f")], b: [part("f")] });
    expect(marked.actions.slice(0, 2).map((one) => one.diff)).toEqual(["added", "removed"]);
  });

  it("gives a link its own status, whatever its ends'", () => {
    const marked = markUseCaseDiagram(drawn, compared({ a: "changed" }, { "b|@check_roles|r": "removed" }), {});
    expect(marked.edges.map((one) => one.diff)).toEqual(["unchanged", "removed"]);
  });
});

describe("useCaseCounts", () => {
  it("counts every marked action, role and link, and nothing else", () => {
    const marked = markUseCaseDiagram(diagram(["a", "b", "c"], ["r"], [link("a", "r")]), compared({ a: "added", r: "changed" }, { "a|@check_roles|r": "added" }), { b: [part("f")] });
    expect(useCaseCounts(marked)).toEqual({ added: 2, removed: 0, changed: 2 });
  });

  it("gives one changed for one action with only a new result field", () => {
    expect(useCaseCounts(markUseCaseDiagram(diagram(["a"], []), compared(), { a: [part("f"), part("g")] }))).toEqual({ added: 0, removed: 0, changed: 1 });
  });
});

describe("a marked role", () => {
  const actor = (data: string | null) => atob((data ?? "").split(",")[1]);

  it("is its own figure in its status's colour, dashed only when removed, and carries no frame", () => {
    expect(buildRoleActorDataUrl(undefined)).toBeNull();
    expect(buildRoleActorDataUrl("unchanged")).toBeNull();
    expect(actor(buildRoleActorDataUrl("added"))).toContain("#16a34a");
    expect(actor(buildRoleActorDataUrl("added"))).not.toContain("dasharray");
    expect(actor(buildRoleActorDataUrl("removed"))).toContain("#dc2626");
    expect(actor(buildRoleActorDataUrl("removed"))).toContain("dasharray");
    const bundle = buildDomainUseCaseDotBundle(markUseCaseDiagram(diagram([], ["r"]), compared({ r: "removed" }), {}), "LR", options);
    expect(bundle.dot).toContain('TABLE BORDER="0"');
    expect(bundle.dot).toContain('COLOR="#dc2626"');
    expect(bundle.actionImages.map((image) => image.path)).toEqual([buildRoleActorDataUrl("removed")]);
  });
});

describe("the drawing", () => {
  const dot = (data: DomainUseCaseDiagramPayload) => buildDomainUseCaseDotBundle(data, "LR", options).dot;
  const one = diagram(["a", "b"], ["r"], [link("a", "r"), link("b", "r")]);

  it("in One carries no mark", () => {
    expect(dot(one)).not.toMatch(/class=|tooltip=|color="#16a34a"/);
  });

  it("with the marks taken off is One's text", () => {
    const marked = markUseCaseDiagram(one, compared({ a: "added" }, { "b|@check_roles|r": "removed" }), {});
    expect(dot(unmarkedUseCase(marked))).toBe(dot(one));
  });

  it("fades the unchanged, colours a link and dashes a removed one, and signs on hover", () => {
    const text = dot(markUseCaseDiagram(one, compared({ a: "changed" }, { "a|@check_roles|r": "added", "b|@check_roles|r": "removed" }), {}));
    expect(text).toContain('tooltip="~ a"');
    expect(text).toMatch(/a_b \[[^\n]*class="use-case-faded"/);
    expect(text).toMatch(/r_r -> a_a \[[^\n]*color="#16a34a"/);
    expect(text).toMatch(/r_r -> a_b \[[^\n]*color="#dc2626"[^\n]*style=dashed/);
  });
});

describe("the card", () => {
  const marked = markUseCaseDiagram(diagram(["a", "b", "c"], ["r"]), compared({ b: "added", r: "changed" }), { a: [part("f")], b: [part("f")] });

  it("of an action changed inside carries its parts", () => {
    expect(useCaseCard(marked, "a")).toMatchObject({ title: "a", status: "changed", elements: [{ kind: "node", id: "a" }], parts: [{ id: "f" }] });
  });

  it("of an added action carries no parts", () => {
    expect(useCaseCard(marked, "b")?.parts).toBeUndefined();
  });

  it("is there for a changed role, and not for an unchanged or undrawn element", () => {
    expect(useCaseCard(marked, "r")?.status).toBe("changed");
    expect(useCaseCard(marked, "c")).toBeNull();
    expect(useCaseCard(marked, "gone")).toBeNull();
  });

  it("is found from a click inside a marked node, not on an unchanged one or the canvas", () => {
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.innerHTML = '<g class="node"><title>a_a</title><image/></g><g class="node"><title>a_c</title><image/></g><rect/>';
    expect(useCaseIdAt(svg.querySelectorAll("image")[0], marked)).toBe("a");
    expect(useCaseIdAt(svg.querySelectorAll("image")[1], marked)).toBeNull();
    expect(useCaseIdAt(svg.querySelector("rect"), marked)).toBeNull();
  });

  it("is found from a click on a marked link, not on an unchanged one", () => {
    const withLinks = markUseCaseDiagram(diagram(["a", "b"], ["r"], [link("a", "r"), link("b", "r")]), compared({}, { "a|@check_roles|r": "added" }), {});
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.innerHTML = '<g class="edge" id="change_a__check_roles_r"><path/></g><g class="edge" id="edge2"><path/></g>';
    expect(useCaseIdAt(svg.querySelectorAll("path")[0], withLinks)).toBe("a|@check_roles|r");
    expect(useCaseIdAt(svg.querySelectorAll("path")[1], withLinks)).toBeNull();
    expect(useCaseCard(withLinks, "b|@check_roles|r")).toBeNull();
  });
});

describe("the steps", () => {
  const marked = markUseCaseDiagram(diagram(["z", "b", "c"], ["r"], [link("c", "r"), link("b", "r")]), compared({ z: "added", r: "changed" }, { "c|@check_roles|r": "removed" }), { b: [part("f")] });
  const changes = useCaseChanges(marked);

  it("hold every mark once, actions, then roles, then links, as the counts do", () => {
    expect(changes.map((change) => [change.group, change.title, change.status])).toEqual([
      ["Actions", "b", "changed"],
      ["Actions", "z", "added"],
      ["Roles", "r", "changed"],
      ["Links", "c → r", "removed"],
    ]);
    const counts = useCaseCounts(marked);
    expect(changes).toHaveLength(counts.added + counts.removed + counts.changed);
  });

  it("say an action changed inside, and give a node and a link each its card", () => {
    expect(changes[0].detail).toBe("Changed inside");
    expect(changes[0].card?.parts).toHaveLength(1);
    expect(changes[3].card).toEqual({ title: "c → r", status: "removed", elements: [{ kind: "edge", id: "c|@check_roles|r" }] });
  });

  it("each name an element the drawing carries", () => {
    const text = buildDomainUseCaseDotBundle(marked, "LR", options).dot;
    for (const change of changes) expect(text).toContain(`id="${change.cell}"`);
  });
});

describe("the Changes filter", () => {
  const marked = markUseCaseDiagram(diagram(["a", "b", "c"], ["r"], [link("a", "r"), link("b", "r"), link("c", "r")]), compared({ a: "added", b: "removed" }, { "a|@check_roles|r": "added", "b|@check_roles|r": "removed" }), { c: [part("f")] });

  it("lists the kinds the diagram holds, in the filter's order, none when nothing changed", () => {
    expect(useCaseChangeKinds(marked)).toEqual(["added", "removed", "changed", "unchanged"]);
    expect(useCaseChangeKinds(markUseCaseDiagram(diagram(["a"], []), compared(), {}))).toEqual([]);
  });

  it("hides a kind with the links touching it, and the counts and steps follow", () => {
    const left = filterUseCaseByChanges(marked, new Set(["removed"]));
    expect(left.actions.map((one) => one.id)).toEqual(["a", "c"]);
    expect(left.edges.map((one) => one.source_id)).toEqual(["a", "c"]);
    expect(useCaseCounts(left)).toEqual({ added: 2, removed: 0, changed: 1 });
    expect(useCaseChanges(left).map((change) => change.key)).not.toContain("b");
  });

  it("hides a link of a kind switched off even when both its ends stay", () => {
    const drawn = markUseCaseDiagram(diagram(["a"], ["r"], [link("a", "r")]), compared({}, { "a|@check_roles|r": "removed" }), {});
    const left = filterUseCaseByChanges(drawn, new Set(["removed"]));
    expect(left.actions).toHaveLength(1);
    expect(left.edges).toEqual([]);
  });

  it("leaves nothing to say when only the unchanged are left", () => {
    const left = filterUseCaseByChanges(marked, new Set(["added", "removed", "changed"]));
    expect(useCaseCounts(left)).toEqual({ added: 0, removed: 0, changed: 0 });
    expect(useCaseChangeKinds(left)).toEqual([]);
  });

  it("does nothing with nothing off", () => {
    expect(filterUseCaseByChanges(marked, new Set())).toBe(marked);
  });
});

describe("painting by domains", () => {
  it("keeps the action's own colour and its status in the outline", () => {
    const glyph = (paintChanges: boolean) => atob(buildActionGlyphDataUrl("a", "#8b5cf6", "removed", paintChanges).split(",")[1]);
    expect(glyph(true)).toContain('stroke="#dc2626"');
    expect(glyph(false)).toContain('stroke="#8b5cf6"');
    expect(glyph(false)).toContain("stroke-dasharray");
  });
});

describe("1-hop", () => {
  const base = markUseCaseDiagram(diagram(["a", "b", "far"], ["r", "lonely"], [link("a", "r"), link("b", "r"), link("far", "lonely")]), compared({ a: "added" }), {});

  it("brings back what is one link away from what the filters left, and no further", () => {
    const kept = filterUseCaseByChanges(base, new Set(["unchanged"]));
    expect(kept.actions.map((one) => one.id)).toEqual(["a"]);
    const hop = withUseCaseOneHop(kept, base);
    expect(hop.actions.map((one) => one.id)).toEqual(["a"]);
    expect(hop.roles.map((one) => one.id)).toEqual(["r"]);
    expect(hop.edges.map((one) => one.source_id)).toEqual(["a"]);
  });

  it("from a role reaches every action it serves", () => {
    const kept = { ...base, actions: [], roles: base.roles.filter((one) => one.id === "r"), edges: [] };
    expect(withUseCaseOneHop(kept, base).actions.map((one) => one.id)).toEqual(["a", "b"]);
  });
});
