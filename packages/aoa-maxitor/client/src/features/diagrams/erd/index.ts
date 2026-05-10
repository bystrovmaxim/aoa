// packages/aoa-maxitor/client/src/features/diagrams/erd/index.ts
/**
 * ERD viewer sub-feature: JSON from ``/api/v1/erd/*`` + bundled ``shell/*`` assets → blob iframe document.
 */

export { ErdViewer } from "./components/erd_viewer";
export { useErdViewerBlobUrl } from "./hooks/use_erd_viewer_blob_url";
export type { ErdViewerSelection } from "./hooks/use_erd_viewer_blob_url";
export { buildErdHtmlDocument } from "./lib/build_erd_html_document";
export { enrichErdDataForViewer } from "./lib/enrich_erd_data";
export { allocateDomainTabKey } from "./lib/domain_tab_keys";
export { fetchErdDomainPayload, fetchErdDomainQualnames } from "./api/erd_api";
