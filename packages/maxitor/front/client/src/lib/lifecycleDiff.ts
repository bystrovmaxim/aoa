// src/lib/lifecycleDiff.ts
/**
 * The lifecycle diagram of two versions (spec 042): the union of A's and B's diagram of one lifecycle, each state and
 * transition marked with what the comparison says. A state owns nothing the diagram does not draw, so there is no
 * "changed inside" here. A version without the lifecycle gives no read: the left panel says which versions hold it.
 */
import { getActiveBase, type GraphRead } from "@/api/client";
import { compareVersions, type CompareResult, type DiffStatus } from "@/api/compare";
import { fetchLifecycleFiniteAutomaton } from "@/api/lifecycleFiniteAutomaton";
import { getSidebar } from "@/api/sidebar";
import type { DiagramCounts } from "@/lib/erdDiff";
import type { LifecycleFiniteAutomatonPayload, LifecycleFsmArrow, LifecycleFsmStateWire } from "@/model/lifecycleFiniteAutomaton";

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
