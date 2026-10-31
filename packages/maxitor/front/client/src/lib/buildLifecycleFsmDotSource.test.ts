import { describe, expect, it } from "vitest";
import { buildLifecycleFsmDotSource, LIFECYCLE_FADED_CLASS } from "@/lib/buildLifecycleFsmDotSource";
import { lifecycleCounts } from "@/lib/lifecycleDiff";
import type { LifecycleFiniteAutomatonPayload } from "@/model/lifecycleFiniteAutomaton";

const one: LifecycleFiniteAutomatonPayload = {
  lifecycle_graph_node_id: "a:lifecycle:s",
  host_entity_type_qualname: "a",
  field_name: "s",
  lifecycle_class_qualname: "c",
  initial_state_keys: ["open"],
  states: [
    { id: "a:lifecycle:s:open", key: "open", display_name: "Open", state_type: "initial", transitions: ["done"] },
    { id: "a:lifecycle:s:done", key: "done", display_name: "Done", state_type: "final", transitions: [], attributes: { color: "#7c3aed" } },
  ],
  transitions: [{ id: "t", source: "open", target: "done" }],
};

// One's text as it was before Diff came to this diagram (spec 042, FR-030): a room compares layouts by it.
const ONE_TEXT = `digraph lifecycle_fsm {
  graph [rankdir=LR, bgcolor=transparent, splines=true, nodesep=0.45, ranksep=0.65, fontname="Helvetica Neue"];
  node [fontname="Helvetica Neue", fontsize=11];
  edge [color="#64748b", arrowsize=0.75];
  __gv_lifecycle_entry [label="", shape=circle, fixedsize=true, width=0.28, height=0.28, margin=0.02, style=filled, fillcolor=black, penwidth=0];
  { rank=min; __gv_lifecycle_entry; }
  __gv_lifecycle_exit [label="", shape=doublecircle, fixedsize=true, width=0.28, height=0.28, margin=0.02, style=filled, fillcolor=black, color=black, penwidth=0.9];
  { rank=max; __gv_lifecycle_exit; }
  "open" [label=<<B>Open</B>>, shape=box, style="rounded,filled", fillcolor="#ecfdf5", color="#059669", penwidth=1.15];
  "done" [label=<<B>Done</B>>, shape=box, style="rounded,filled", fillcolor="#f8fafc", color="#7c3aed", penwidth=1.15];
  __gv_lifecycle_entry -> "open";
  "open" -> "done";
  "done" -> __gv_lifecycle_exit;
}`;

const marked = (diff: "added" | "removed" | "changed" | "unchanged"): LifecycleFiniteAutomatonPayload => ({
  ...one,
  states: one.states.map((state) => ({ ...state, diff })),
  transitions: one.transitions.map((transition) => ({ ...transition, diff })),
  entries: [{ key: "open", diff }],
  exits: [{ key: "done", diff }],
});

describe("buildLifecycleFsmDotSource", () => {
  it("writes One's text byte for byte", () => {
    expect(buildLifecycleFsmDotSource(one)).toBe(ONE_TEXT);
  });

  it("gives an added state its colour, its sign and an id a step can go to", () => {
    const dot = buildLifecycleFsmDotSource(marked("added"));
    expect(dot).toContain("<B>+ Open</B>");
    expect(dot).toContain('color="#16a34a"');
    expect(dot).toContain('id="change_a_lifecycle_s_open"');
    expect(dot).not.toContain("dashed");
  });

  it("draws a removed element dashed, and a final state still final", () => {
    const dot = buildLifecycleFsmDotSource(marked("removed"));
    expect(dot).toContain('"rounded,filled,dashed"');
    expect(dot).toContain("style=dashed");
    expect(dot).toMatch(/"done" \[[^\]]*peripheries=2/);
  });

  it("makes an unchanged state grey, whatever colour it declares", () => {
    const dot = buildLifecycleFsmDotSource(marked("unchanged"));
    expect(dot).toContain(`class="${LIFECYCLE_FADED_CLASS}"`);
    expect(dot).not.toContain("#7c3aed");
    expect(dot).not.toContain('id="change_');
  });

  it("colours a dot only when all its arrows agree", () => {
    const mixed = { ...marked("added"), entries: [{ key: "open", diff: "added" as const }, { key: "done", diff: "unchanged" as const }] };
    expect(buildLifecycleFsmDotSource(mixed).split("\n").find((line) => line.includes("__gv_lifecycle_entry [label"))).toContain(LIFECYCLE_FADED_CLASS);
    expect(buildLifecycleFsmDotSource(marked("added")).split("\n").find((line) => line.includes("__gv_lifecycle_entry [label"))).toContain('fillcolor="#16a34a"');
  });

  it("gives one pair one text", () => {
    expect(buildLifecycleFsmDotSource(marked("changed"))).toBe(buildLifecycleFsmDotSource(marked("changed")));
    expect(lifecycleCounts(marked("changed"))).toEqual({ added: 0, removed: 0, changed: 3 });
  });
});
