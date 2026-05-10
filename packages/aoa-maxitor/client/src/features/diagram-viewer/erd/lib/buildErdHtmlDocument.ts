// packages/aoa-maxitor/client/src/features/diagram-viewer/erd/lib/buildErdHtmlDocument.ts
/**
 * Assemble the standalone ERD viewer HTML in the browser from bundled shell assets
 * (``erd/shell/*`` imported as raw strings). Graph engines load from CDN inside the iframe.
 *
 * The FastAPI app only exposes JSON at ``/api/v1/erd/*``; this module is the sole HTML stitcher.
 */

import erdBootstrapJs from "../shell/erd-bootstrap.js?raw";
import interchangeChromeCss from "../shell/interchange_chrome.css?raw";
import erdTemplateHtml from "../shell/template.html?raw";
import { enrichErdDataForViewer } from "./enrichErdData";

const ERD_BOOTSTRAP_PLACEHOLDER = "__MAXITOR_ERD_DATA_JSON__";

function escapeHtml(s: string): string {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

/** Full standalone HTML document for ``ERD_DATA``-shaped ``domains`` / ``domain_qualifiers``. */
export function buildErdHtmlDocument(erdData: Record<string, unknown>, title: string): string {
  const enriched = enrichErdDataForViewer(erdData);
  /** Avoid closing ``</script>`` inside string literals when the parser reads the inline module. */
  const json = JSON.stringify(enriched).replace(/</g, "\\u003c");
  const bootstrap = erdBootstrapJs;
  if (!bootstrap.includes(ERD_BOOTSTRAP_PLACEHOLDER)) {
    throw new Error("erd/shell/erd-bootstrap.js is missing __MAXITOR_ERD_DATA_JSON__");
  }
  const scriptBody = bootstrap.replaceAll(ERD_BOOTSTRAP_PLACEHOLDER, json);
  let html = erdTemplateHtml.replace("@@INTERCHANGE_CHROME_CSS@@", interchangeChromeCss);
  html = html.replace("@@HTML_ESCAPED_TITLE@@", escapeHtml(title));
  html = html.replace("@@INLINE_ERD_SCRIPT@@", scriptBody);
  html = html.replaceAll("@@CONTAINER_WIDTH@@", "1400").replaceAll("@@CONTAINER_HEIGHT@@", "900");
  return html;
}
