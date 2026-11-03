// src/model/lifecycleFiniteAutomaton.ts
import type { DiffStatus } from "@/api/compare";

/** Wire shape for ``GET /api/v1/lifecycle-finite-automaton`` (``GetLifecycleFiniteAutomatonAction.Result``). */
export type LifecycleFsmStateWire = {
  /** The graph node's id: what two versions match a state by. */
  id: string;
  key: string;
  display_name: string;
  state_type: string;
  transitions: string[];
  attributes?: Record<string, unknown>;
  /** In Diff: what the comparison says of this state. */
  diff?: DiffStatus;
};

export type LifecycleFsmTransitionWire = {
  /** The graph edge's id: its source, its target and the state it leaves. */
  id: string;
  source: string;
  target: string;
  /** In Diff: what the comparison says of this transition. */
  diff?: DiffStatus;
};

/** In Diff: an arrow from the entry dot or to the exit dot, a piece of the drawing: never counted, stepped to or opened. */
export type LifecycleFsmArrow = { key: string; diff: DiffStatus };

export type LifecycleFiniteAutomatonPayload = {
  lifecycle_graph_node_id: string;
  host_entity_type_qualname: string;
  field_name: string;
  lifecycle_class_qualname: string;
  initial_state_keys: string[];
  states: LifecycleFsmStateWire[];
  transitions: LifecycleFsmTransitionWire[];
  /** In Diff: the arrows from the entry dot, of either version. */
  entries?: LifecycleFsmArrow[];
  /** In Diff: the arrows to the exit dot, of either version. */
  exits?: LifecycleFsmArrow[];
};
