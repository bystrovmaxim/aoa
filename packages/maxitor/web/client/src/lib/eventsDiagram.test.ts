// src/lib/eventsDiagram.test.ts
import { describe, expect, it } from "vitest";
import type { CompareResult } from "@/api/compare";
import { buildEventsDot, eventsCounts, eventsChanges, eventsOfSide, filterEvents, markEventsDiagram, mergeEventsDiagrams, vocabularyLabel } from "@/lib/eventsDiagram";
import type { DomainEventsDiagramPayload, EventWire } from "@/model/domainEventsDiagram";

const event = (id: string, band: EventWire["band"] = "emitted"): EventWire => ({ id, label: id, band, fields: [], methods: [], domains: [] });

function diagram(events: EventWire[], typed: boolean | null = false): DomainEventsDiagramPayload {
  return {
    domain: { id: "d", label: "D", short_label: "d", accent_color: "#000000", typed_events: typed },
    actions: [{ id: "a", label: "A", short_label: "A", domain_id: "d", domain_short_label: "d", accent_color: "#000000" }],
    methods: [{ id: "a:m", label: "m", kind: "Compensator", action_id: "a" }],
    events,
    edges: [{ id: "a|@compensate|a:m", edge_kind: "method", source_id: "a", target_id: "a:m" }, ...events.map((each) => ({ id: `a:m|@emits|${each.id}`, edge_kind: "emits" as const, source_id: "a:m", target_id: each.id }))],
  };
}

const icon = () => "x.svg";

describe("the DOT text", () => {
  it("says the vocabulary in the frame and draws a band per kind", () => {
    const dot = buildEventsDot(diagram([event("e1", "in_vocabulary"), event("e2", "not_emitted")], true), "LR", true, icon);
    expect(dot).toContain('label="d · Vocabulary"');
    expect(dot).toContain('label="In vocabulary"');
    expect(dot).toContain('label="Not emitted"');
    expect(dot).not.toContain('label="Emitted"');
  });

  it("has no frame label without a boundary, and one band without a vocabulary", () => {
    const text = buildEventsDot(diagram([event("e1")]), "TB", false, icon);
    expect(text).toContain("rankdir=TB");
    expect(text).not.toContain("cluster_scope");
    expect(text).toContain('label="Emitted"');
  });

  it("has a stable text for one diagram", () => {
    expect(buildEventsDot(diagram([event("e1")]), "LR", true, icon)).toBe(buildEventsDot(diagram([event("e1")]), "LR", true, icon));
  });
});

describe("a comparison", () => {
  const older = diagram([event("gone")]);
  const newer = diagram([event("new")]);
  const compared: CompareResult = { nodes: { gone: "removed", new: "added" }, edges: { "a:m|@emits|gone": "removed", "a:m|@emits|new": "added" } } as unknown as CompareResult;
  const pair = markEventsDiagram(mergeEventsDiagrams(older, newer), compared);

  it("counts one event and one link each way", () => {
    expect(eventsCounts(pair)).toEqual({ added: 2, removed: 2, changed: 0 });
    expect(eventsChanges(pair).map((change) => change.group)).toEqual(expect.arrayContaining(["Events", "Links"]));
  });

  it("marks an event changed when a field of it changed", () => {
    const one = markEventsDiagram(diagram([event("e")]), { nodes: { "e:total": "changed" }, edges: {} } as unknown as CompareResult);
    expect(one.events[0]?.diff).toBe("changed");
  });

  it("gives each side only what it has", () => {
    expect(eventsOfSide(pair, "a").events.map((each) => each.id)).toEqual(["gone"]);
    expect(eventsOfSide(pair, "b").events.map((each) => each.id)).toEqual(["new"]);
  });

  it("says a vocabulary gained", () => {
    const merged = mergeEventsDiagrams(diagram([], false), diagram([], true));
    expect(vocabularyLabel(merged.domain)).toBe("Vocabulary (was No vocabulary)");
  });

  it("opens a version with no events beside one that has them", () => {
    const merged = markEventsDiagram(mergeEventsDiagrams(diagram([]), diagram([event("new")])), compared);
    expect(eventsCounts(merged).added).toBe(2);
  });

  it("hides a kind of change switched off", () => {
    expect(filterEvents(pair, null, new Set(["removed"])).events.map((each) => each.id)).toEqual(["new"]);
  });
});
