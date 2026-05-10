// packages/aoa-maxitor/client/src/features/diagram-viewer/erd/index.ts
/**
 * ERD viewer sub-feature: JSON from ``/api/v1/erd/*`` + bundled ``shell/*`` assets → blob iframe document.
 */

export { ErdViewer } from "./components/ErdViewer";
export { useErdViewerBlobUrl } from "./hooks/useErdViewerBlobUrl";
export type { ErdViewerSelection } from "./hooks/useErdViewerBlobUrl";
export { buildErdHtmlDocument } from "./lib/buildErdHtmlDocument";
export { enrichErdDataForViewer } from "./lib/enrichErdData";
export { allocateDomainTabKey } from "./lib/domainTabKeys";
export { fetchErdDomainPayload, fetchErdDomainQualnames } from "./api/erdApi";
