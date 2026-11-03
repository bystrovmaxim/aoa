// src/lib/openDiagram.ts
/** How something deep in a diagram opens another page of the left panel, as a click on its row does. */
import { createContext, useContext } from "react";
import type { DiagramSelection } from "@/model/diagramSelection";

export const OpenDiagramContext = createContext<((selection: DiagramSelection) => void) | null>(null);

export function useOpenDiagram(): ((selection: DiagramSelection) => void) | null {
  return useContext(OpenDiagramContext);
}

/** The left panel's selection of a lifecycle: its id is ``<entity>:lifecycle:<field>``. */
export function lifecycleSelection(lifecycleId: string): DiagramSelection {
  return { kind: "lifecycle_fsm", lifecycle_graph_node_id: lifecycleId, host_entity_interchange_id: lifecycleId.split(":lifecycle:")[0] ?? lifecycleId };
}
