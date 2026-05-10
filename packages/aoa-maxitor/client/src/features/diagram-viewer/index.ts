// packages/aoa-maxitor/client/src/features/diagram-viewer/index.ts
/**
 * Diagram viewer feature — interchange graph (G6) + ERD viewer (see ``erd/``).
 */

export { DiagramWorkspace } from "./DiagramWorkspace";
export type { DiagramSelection, DomainQualnamesPayload, ErdDomainPayload } from "./model/types";
export * from "./erd";
export * from "./icons";
export * from "./interchange-graph";
