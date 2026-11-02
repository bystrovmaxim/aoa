// src/lib/lifecycleDiff.ts
/**
 * The lifecycle diagram of two versions (spec 042): the union of A's and B's diagram of one lifecycle, each state and
 * transition marked with what the comparison says. A state owns nothing the diagram does not draw, so there is no
 * "changed inside" here. A version without the lifecycle gives no read: the left panel says which versions hold it.
 */
import { getActiveBase, type GraphRead } from "@/api/client";
import { drawnOn, type Side } from "@/lib/half";
import type { ElementRef } from "@/rooms/focusStore";
import { compareVersions, type CompareResult, type DiffStatus } from "@/api/compare";
import { fetchLifecycleFiniteAutomaton } from "@/api/lifecycleFiniteAutomaton";
import { getSidebar } from "@/api/sidebar";
import { lifecycleCellId } from "@/lib/buildLifecycleFsmDotSource";
import type { DiagramCounts } from "@/lib/erdDiff";
import type { CardTarget } from "@/lib/erdDiffCard";
import { CHANGE_ORDER } from "@/lib/erdFilterPresence";
import type { GraphvizChange } from "@/lib/useGraphvizChangeStepping";
import type { LifecycleFiniteAutomatonPayload, LifecycleFsmArrow, LifecycleFsmStateWire, LifecycleFsmTransitionWire } from "@/model/lifecycleFiniteAutomaton";

/** B's elements in B's order, then those only A has: a pair with nothing changed is exactly B. */
function union<T extends { id: string }>(older: readonly T[], newer: readonly T[]): T[] {
  const now = new Set(newer.map((element) => element.id));
  return [...newer, ...older.filter((element) => !now.has(element.id))];
}

/** Each key of either list with its status: in one list only added or removed, in both unchanged. */
function arrows(older: readonly string[], newer: readonly string[]): LifecycleFsmArrow[] {
  const was = new Set(older);
  const now = new Set(newer);
  const status = (key: string): DiffStatus => (!was.has(key) ? "added" : !now.has(key) ? "removed" : "unchanged");
  return [...new Set([...newer, ...older])].map((key) => ({ key, diff: status(key) }));
}

/** The part of a merged lifecycle that one version has, with its marks (spec 044). */
export function lifecycleOfSide(diagram: LifecycleFiniteAutomatonPayload, side: Side): LifecycleFiniteAutomatonPayload {
  const drawn = <E extends { diff?: DiffStatus }>(list: readonly E[]) => list.filter((each) => drawnOn(side, each.diff ?? "unchanged"));
  const entries = diagram.entries ? drawn(diagram.entries) : undefined;
  return { ...diagram, states: drawn(diagram.states), transitions: drawn(diagram.transitions), entries, exits: diagram.exits ? drawn(diagram.exits) : undefined, initial_state_keys: entries ? entries.map((arrow) => arrow.key) : diagram.initial_state_keys };
}

/** Whether a version's part of a lifecycle holds a state, by its key, or a transition, by its title or its cell. */
export function lifecycleHolds(diagram: LifecycleFiniteAutomatonPayload, ref: ElementRef): boolean {
  if (ref.kind === "edge") return diagram.transitions.some((transition) => lifecycleCellId(transition.id) === ref.id || ref.id === `${transition.source}->${transition.target}`);
  return diagram.states.some((state) => state.key === ref.id);
}

/** The keys of the final states of a version. */
function finalKeys(states: readonly LifecycleFsmStateWire[]): string[] {
  return states.filter((state) => state.state_type === "final").map((state) => state.key);
}

/** The union of a lifecycle in A and in B; a lifecycle only one version has comes from that one. */
export function mergeLifecycles(older: LifecycleFiniteAutomatonPayload | null, newer: LifecycleFiniteAutomatonPayload | null): LifecycleFiniteAutomatonPayload {
  const shown = newer ?? older;
  if (!shown) throw new Error("Neither version has this lifecycle.");
  return {
    ...shown,
    initial_state_keys: [...new Set([...(older?.initial_state_keys ?? []), ...(newer?.initial_state_keys ?? [])])].sort(),
    states: union(older?.states ?? [], newer?.states ?? []),
    transitions: union(older?.transitions ?? [], newer?.transitions ?? []),
    entries: arrows(older?.initial_state_keys ?? [], newer?.initial_state_keys ?? []),
    exits: arrows(finalKeys(older?.states ?? []), finalKeys(newer?.states ?? [])),
  };
}

/** Every state and transition marked with its status. */
export function markLifecycle(diagram: LifecycleFiniteAutomatonPayload, compared: CompareResult): LifecycleFiniteAutomatonPayload {
  return {
    ...diagram,
    states: diagram.states.map((state) => ({ ...state, diff: compared.nodes[state.id] ?? "unchanged" })),
    transitions: diagram.transitions.map((transition) => ({ ...transition, diff: compared.edges[transition.id] ?? "unchanged" })),
  };
}

/** The drawn diagram's counts: every state and transition it marks; the entry and exit dots are not elements (spec 042, FR-009). */
export function lifecycleCounts(diagram: LifecycleFiniteAutomatonPayload): DiagramCounts {
  const counts: DiagramCounts = { added: 0, removed: 0, changed: 0 };
  for (const element of [...diagram.states, ...diagram.transitions]) {
    if (element.diff && element.diff !== "unchanged") counts[element.diff] += 1;
  }
  return counts;
}

/** The same diagram with every mark taken off, as One draws it. */
export function unmarkedLifecycle(diagram: LifecycleFiniteAutomatonPayload): LifecycleFiniteAutomatonPayload {
  const { entries: _entries, exits: _exits, ...rest } = diagram;
  return {
    ...rest,
    states: diagram.states.map(({ diff: _diff, ...state }) => state),
    transitions: diagram.transitions.map(({ diff: _diff, ...transition }) => transition),
  };
}

/** The kinds of state, as the Elements filter lists them. */
export const LIFECYCLE_KINDS = ["initial", "intermediate", "final"] as const;

/** The kinds of change the diagram holds, in the filter's order; none when nothing on it changed. */
export function lifecycleChangeKinds(diagram: LifecycleFiniteAutomatonPayload): DiffStatus[] {
  const present = new Set([...diagram.states, ...diagram.transitions].map((element) => element.diff));
  if (![...present].some((status) => status && status !== "unchanged")) return [];
  return CHANGE_ORDER.filter((status) => present.has(status));
}

/** The diagram with only these states and the transitions that pass ``keep`` between them. */
function withStates(diagram: LifecycleFiniteAutomatonPayload, states: LifecycleFsmStateWire[], keep: (transition: LifecycleFsmTransitionWire) => boolean = () => true): LifecycleFiniteAutomatonPayload {
  const keys = new Set(states.map((state) => state.key));
  return { ...diagram, states, transitions: diagram.transitions.filter((transition) => keep(transition) && keys.has(transition.source) && keys.has(transition.target)) };
}

/** Hide what is of a kind of change switched off, and every transition touching a hidden state (spec 042, FR-021). */
export function filterLifecycleByChanges(diagram: LifecycleFiniteAutomatonPayload, off: ReadonlySet<string>): LifecycleFiniteAutomatonPayload {
  if (off.size === 0) return diagram;
  const kept = (element: { diff?: DiffStatus }) => !element.diff || !off.has(element.diff);
  return withStates(diagram, diagram.states.filter(kept), kept);
}

/** Hide the states of a kind switched off, with their transitions. */
export function filterLifecycleByKinds(diagram: LifecycleFiniteAutomatonPayload, off: ReadonlySet<string>): LifecycleFiniteAutomatonPayload {
  if (off.size === 0) return diagram;
  return withStates(diagram, diagram.states.filter((state) => !off.has(state.state_type)));
}

/** 1-hop over the filters: what they left, and every state of the base one transition away from it, even what a filter hid. */
export function withLifecycleOneHop(kept: LifecycleFiniteAutomatonPayload, base: LifecycleFiniteAutomatonPayload): LifecycleFiniteAutomatonPayload {
  const keys = new Set(kept.states.map((state) => state.key));
  const reach = new Set(keys);
  for (const transition of base.transitions) {
    if (keys.has(transition.source)) reach.add(transition.target);
    if (keys.has(transition.target)) reach.add(transition.source);
  }
  return withStates(base, base.states.filter((state) => reach.has(state.key)));
}

/** A state's name, as its card and its row in a list say it. */
function stateName(state: LifecycleFsmStateWire | undefined, key: string): string {
  return state?.display_name.trim() || key;
}

/** A transition's name: the names of the state it leaves and the state it enters, never an id. */
function transitionName(diagram: LifecycleFiniteAutomatonPayload, source: string, target: string): string {
  const named = (key: string) => stateName(diagram.states.find((state) => state.key === key), key);
  return `${named(source)} → ${named(target)}`;
}

/** The card of a marked state or transition by its id, or ``null`` when it is unchanged or no longer drawn. */
export function lifecycleCard(diagram: LifecycleFiniteAutomatonPayload, id: string): CardTarget | null {
  const transition = diagram.transitions.find((each) => each.id === id);
  if (transition) {
    if (!transition.diff || transition.diff === "unchanged") return null;
    return { title: transitionName(diagram, transition.source, transition.target), status: transition.diff, elements: [{ kind: "edge", id }] };
  }
  const state = diagram.states.find((each) => each.id === id);
  if (!state?.diff || state.diff === "unchanged") return null;
  return { title: stateName(state, state.key), status: state.diff, elements: [{ kind: "node", id }] };
}

/** Sorts by a text, then by id, so a list has one order. */
function byName<T extends { id: string }>(elements: readonly T[], name: (element: T) => string): T[] {
  return [...elements].sort((one, other) => name(one).localeCompare(name(other)) || (one.id < other.id ? -1 : 1));
}

/** Every change the drawn diagram marks, once each: its states, then its transitions (spec 042, FR-017). */
export function lifecycleChanges(diagram: LifecycleFiniteAutomatonPayload): GraphvizChange[] {
  const change = (id: string, group: string, detail: string): GraphvizChange[] => {
    const card = lifecycleCard(diagram, id);
    return card ? [{ key: id, title: card.title, detail, status: card.status, group, cell: lifecycleCellId(id), card }] : [];
  };
  return [
    ...byName(diagram.states, (state) => stateName(state, state.key)).flatMap((state) => change(state.id, "States", "State")),
    ...byName(diagram.transitions, (transition) => transitionName(diagram, transition.source, transition.target)).flatMap((transition) => change(transition.id, "Transitions", "Transition")),
  ];
}

/** The id of the marked state or transition a click landed on, by what Graphviz wrote for it. */
export function lifecycleIdAt(target: Element | null, diagram: LifecycleFiniteAutomatonPayload): string | null {
  const drawn = target?.closest?.("g.node, g.edge");
  if (!drawn) return null;
  if (drawn.classList.contains("edge")) return diagram.transitions.find((each) => each.diff !== "unchanged" && lifecycleCellId(each.id) === drawn.id)?.id ?? null;
  const key = drawn.querySelector("title")?.textContent;
  const state = diagram.states.find((each) => each.key === key);
  return state?.diff && state.diff !== "unchanged" ? state.id : null;
}

/** Whether a version's left panel lists this lifecycle. */
async function holds(lifecycleId: string, read?: GraphRead): Promise<boolean> {
  return (await getSidebar(read)).level3_diagrams.some((row) => row.id === lifecycleId);
}

/** A lifecycle of the open version, or ``null`` when that version does not hold it. */
export async function loadLifecycle(lifecycleId: string): Promise<LifecycleFiniteAutomatonPayload | null> {
  return (await holds(lifecycleId)) ? fetchLifecycleFiniteAutomaton(lifecycleId) : null;
}

/** A lifecycle in the pair being compared, read from each version that holds it, merged and marked; ``null`` when neither does. */
export async function loadLifecycleDiff(lifecycleId: string): Promise<LifecycleFiniteAutomatonPayload | null> {
  const base = getActiveBase();
  if (!base) throw new Error("No two versions to compare.");
  const [inNewer, inOlder, compared] = await Promise.all([holds(lifecycleId), holds(lifecycleId, base), compareVersions()]);
  if (!inNewer && !inOlder) return null;
  const [newer, older] = await Promise.all([
    inNewer ? fetchLifecycleFiniteAutomaton(lifecycleId) : null,
    inOlder ? fetchLifecycleFiniteAutomaton(lifecycleId, base) : null,
  ]);
  return markLifecycle(mergeLifecycles(older, newer), compared);
}
