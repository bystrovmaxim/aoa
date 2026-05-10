// packages/aoa-maxitor/client/src/features/diagrams/index.ts
/**
 * Diagram views — central pane (`MainDiagramView`), interchange graph (G6), ERD viewer (`erd/`).
 */

export { MainDiagramView } from "./main_diagram_view";
export type { DiagramSelection, DomainQualnamesPayload, ErdDomainPayload } from "../model/types";
export * from "./erd";
export * from "./interchange_graph";
