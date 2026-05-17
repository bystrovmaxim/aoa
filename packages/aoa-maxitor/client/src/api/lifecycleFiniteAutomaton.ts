// src/api/lifecycleFiniteAutomaton.ts
import { apiUrl } from "@/api/client";
import type { LifecycleFiniteAutomatonPayload } from "@/model/lifecycleFiniteAutomaton";

/** ``GET /api/v1/lifecycle-finite-automaton`` — template FSM for one interchange Lifecycle vertex id. */
export async function fetchLifecycleFiniteAutomaton(lifecycleGraphNodeId: string): Promise<LifecycleFiniteAutomatonPayload> {
  const q = new URLSearchParams({ lifecycle_graph_node_id: lifecycleGraphNodeId });
  const response = await fetch(`${apiUrl("/api/v1/lifecycle-finite-automaton")}?${q.toString()}`);
  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`Lifecycle FSM request failed (${response.status}): ${text || response.statusText}`);
  }
  const body = (await response.json()) as { lifecycle_finite_automaton?: LifecycleFiniteAutomatonPayload };
  const payload = body.lifecycle_finite_automaton;
  if (!payload || typeof payload !== "object") {
    throw new Error("Lifecycle FSM response missing lifecycle_finite_automaton");
  }
  return payload;
}
