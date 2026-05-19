// src/model/lifecycleFiniteAutomaton.ts
/** Wire shape for ``GET /api/v1/lifecycle-finite-automaton`` (``GetLifecycleFiniteAutomatonAction.Result``). */
export type LifecycleFsmStateWire = {
  key: string;
  display_name: string;
  state_type: string;
  transitions: string[];
};

export type LifecycleFsmTransitionWire = {
  source: string;
  target: string;
};

export type LifecycleFiniteAutomatonPayload = {
  lifecycle_graph_node_id: string;
  host_entity_type_qualname: string;
  field_name: string;
  lifecycle_class_qualname: string;
  initial_state_keys: string[];
  states: LifecycleFsmStateWire[];
  transitions: LifecycleFsmTransitionWire[];
};
