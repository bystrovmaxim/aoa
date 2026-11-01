import { describe, expect, it } from "vitest";
import type { CompareResult } from "@/api/compare";
import { filterLifecycleByChanges, filterLifecycleByKinds, lifecycleCard, lifecycleChangeKinds, lifecycleChanges, lifecycleCounts, lifecycleHolds, lifecycleOfSide, markLifecycle, mergeLifecycles, unmarkedLifecycle, withLifecycleOneHop } from "@/lib/lifecycleDiff";
import type { LifecycleFiniteAutomatonPayload, LifecycleFsmStateWire } from "@/model/lifecycleFiniteAutomaton";

const life = "a.Offer:lifecycle:status";
const state = (key: string, state_type = "intermediate", display_name = key): LifecycleFsmStateWire => ({ id: `${life}:${key}`, key, display_name, state_type, transitions: [] });
const edge = (source: string, target: string) => ({ id: `${life}:${source}|lifecycle_transition|${life}:${target}|${source}`, source, target });
const diagram = (states: LifecycleFsmStateWire[], transitions: ReturnType<typeof edge>[]): LifecycleFiniteAutomatonPayload => ({
  lifecycle_graph_node_id: life,
  host_entity_type_qualname: "a.Offer",
  field_name: "status",
  lifecycle_class_qualname: "a.Status",
  initial_state_keys: states.filter((each) => each.state_type === "initial").map((each) => each.key),
  states,
  transitions,
});
const nothing: CompareResult = { counts: { nodes: { added: 0, removed: 0, changed: 0 }, edges: { added: 0, removed: 0, changed: 0 } }, nodes: {}, edges: {} };
const compared = (nodes: CompareResult["nodes"], edges: CompareResult["edges"]): CompareResult => ({ ...nothing, nodes, edges });

const older = diagram([state("open", "initial"), state("busy"), state("done", "final")], [edge("open", "busy"), edge("busy", "done")]);

describe("mergeLifecycles", () => {
  it("holds each element of either version once, B's wording winning", () => {
    const newer = diagram([state("open", "initial"), state("busy", "intermediate", "Working"), state("late"), state("done", "final")], [edge("open", "busy"), edge("late", "done")]);
    const merged = mergeLifecycles(older, newer);
    expect(merged.states.map((each) => each.key)).toEqual(["open", "busy", "late", "done"]);
    expect(merged.states[1].display_name).toBe("Working");
    expect(merged.transitions.map((each) => each.id)).toEqual([edge("open", "busy").id, edge("late", "done").id, edge("busy", "done").id]);
  });

  it("keeps B's order, so that a pair with nothing changed is B", () => {
    expect(unmarkedLifecycle(markLifecycle(mergeLifecycles(older, older), nothing))).toEqual(older);
  });

  it("takes a lifecycle only one version has from that one, every dot's arrow with its side", () => {
    const merged = mergeLifecycles(null, older);
    expect(merged.states).toHaveLength(3);
    expect(merged.entries).toEqual([{ key: "open", diff: "added" }]);
    expect(merged.exits).toEqual([{ key: "done", diff: "added" }]);
    expect(mergeLifecycles(older, null).exits).toEqual([{ key: "done", diff: "removed" }]);
  });

  it("refuses a lifecycle neither version has", () => {
    expect(() => mergeLifecycles(null, null)).toThrow();
  });

  it("gives a second initial state an arrow of its own and leaves the first unchanged", () => {
    const newer = diagram([state("open", "initial"), state("new", "initial"), state("busy"), state("done", "final")], older.transitions);
    expect(mergeLifecycles(older, newer).entries).toEqual([{ key: "open", diff: "unchanged" }, { key: "new", diff: "added" }]);
  });
});

describe("markLifecycle", () => {
  it("tells apart two transitions into one state from different states", () => {
    const newer = diagram([state("open", "initial"), state("busy"), state("done", "final")], [...older.transitions, edge("open", "done")]);
    const marked = markLifecycle(mergeLifecycles(older, newer), compared({}, { [edge("open", "done").id]: "added" }));
    const into = marked.transitions.filter((each) => each.target === "done");
    expect(into.map((each) => [each.source, each.diff])).toEqual([["busy", "unchanged"], ["open", "added"]]);
  });

  it("draws a transition moved to another state as a removal and an addition", () => {
    const newer = diagram(older.states, [edge("open", "done"), edge("busy", "done")]);
    const marked = markLifecycle(mergeLifecycles(older, newer), compared({}, { [edge("open", "busy").id]: "removed", [edge("open", "done").id]: "added" }));
    expect(lifecycleCounts(marked)).toEqual({ added: 1, removed: 1, changed: 0 });
  });

  it("gives a transition its own status, whatever its ends", () => {
    const marked = markLifecycle(older, compared({ [`${life}:open`]: "changed", [`${life}:busy`]: "changed" }, {}));
    expect(marked.transitions[0].diff).toBe("unchanged");
  });

  it("marks what the comparison marks, a change the drawing does not show included", () => {
    const marked = markLifecycle(older, compared({ [`${life}:done`]: "changed" }, {}));
    expect(marked.states.map((each) => each.diff)).toEqual(["unchanged", "unchanged", "changed"]);
  });
});

describe("lifecycleCounts", () => {
  it("counts states and transitions, and never the dots", () => {
    const all = markLifecycle(mergeLifecycles(null, older), compared({ [`${life}:open`]: "added", [`${life}:busy`]: "added", [`${life}:done`]: "added" }, { [edge("open", "busy").id]: "added", [edge("busy", "done").id]: "added" }));
    expect(lifecycleCounts(all)).toEqual({ added: 5, removed: 0, changed: 0 });
  });
});

describe("lifecycleCard", () => {
  const marked = markLifecycle(older, compared({ [`${life}:busy`]: "changed" }, { [edge("open", "busy").id]: "removed" }));

  it("names a transition by its two states, never by an id", () => {
    expect(lifecycleCard(marked, edge("open", "busy").id)).toEqual({ title: "open → busy", status: "removed", elements: [{ kind: "edge", id: edge("open", "busy").id }] });
  });

  it("gives a changed state its card and an unchanged element none", () => {
    expect(lifecycleCard(marked, `${life}:busy`)?.status).toBe("changed");
    expect(lifecycleCard(marked, `${life}:open`)).toBeNull();
    expect(lifecycleCard(marked, edge("busy", "done").id)).toBeNull();
  });
});

describe("lifecycleChanges", () => {
  it("lists each change once, states before transitions, in one order", () => {
    const marked = markLifecycle(older, compared({ [`${life}:open`]: "changed", [`${life}:busy`]: "changed" }, { [edge("busy", "done").id]: "added" }));
    expect(lifecycleChanges(marked).map((change) => [change.group, change.title])).toEqual([["States", "busy"], ["States", "open"], ["Transitions", "busy → done"]]);
  });
});

describe("the filters", () => {
  const marked = markLifecycle(older, compared({ [`${life}:busy`]: "added" }, { [edge("open", "busy").id]: "added" }));

  it("names the kinds of change present, and none when nothing changed", () => {
    expect(lifecycleChangeKinds(marked)).toEqual(["added", "unchanged"]);
    expect(lifecycleChangeKinds(markLifecycle(older, nothing))).toEqual([]);
  });

  it("takes a hidden state's transitions with it", () => {
    const left = filterLifecycleByChanges(marked, new Set(["added"]));
    expect(left.states.map((state) => state.key)).toEqual(["open", "done"]);
    expect(left.transitions).toEqual([]);
    expect(filterLifecycleByKinds(older, new Set(["final"])).transitions.map((each) => each.target)).toEqual(["busy"]);
  });

  it("hides a transition of a kind of change switched off between two states left", () => {
    const left = filterLifecycleByChanges(markLifecycle(older, compared({}, { [edge("open", "busy").id]: "added" })), new Set(["added"]));
    expect(left.states).toHaveLength(3);
    expect(left.transitions.map((each) => each.source)).toEqual(["busy"]);
  });

  it("brings back what stands one transition away, and changes nothing when nothing is off", () => {
    const hop = withLifecycleOneHop(filterLifecycleByKinds(older, new Set(["final", "intermediate"])), older);
    expect(hop.states.map((state) => state.key)).toEqual(["open", "busy"]);
    expect(withLifecycleOneHop(older, older)).toEqual(older);
    const back = withLifecycleOneHop(filterLifecycleByKinds(older, new Set(["initial", "intermediate"])), older);
    expect(back.states.map((state) => state.key)).toEqual(["busy", "done"]);
  });
});

describe("the part of a lifecycle one version has (spec 044)", () => {
  const diagram = {
    initial_state_keys: ["old", "new"],
    states: [{ key: "kept", diff: "unchanged" }, { key: "old", diff: "removed" }, { key: "new", diff: "added" }],
    transitions: [{ id: "t1", source: "old", target: "kept", diff: "removed" }, { id: "t2", source: "new", target: "kept", diff: "added" }],
    entries: [{ key: "old", diff: "removed" }, { key: "new", diff: "added" }],
    exits: [],
  } as unknown as LifecycleFiniteAutomatonPayload;

  it("keeps on each side its states, transitions and start", () => {
    const a = lifecycleOfSide(diagram, "a");
    expect(a.states.map((state) => state.key)).toEqual(["kept", "old"]);
    expect(a.initial_state_keys).toEqual(["old"]);
    expect(lifecycleOfSide(diagram, "b").transitions.map((transition) => transition.id)).toEqual(["t2"]);
  });

  it("knows what a side holds", () => {
    const b = lifecycleOfSide(diagram, "b");
    expect(lifecycleHolds(b, { kind: "node", id: "new" })).toBe(true);
    expect(lifecycleHolds(b, { kind: "node", id: "old" })).toBe(false);
    expect(lifecycleHolds(b, { kind: "edge", id: "new->kept" })).toBe(true);
  });
});
