// packages/aoa-maxitor/client/src/features/diagrams/erd/components/erd_viewer.tsx
import { useCallback, useState } from "react";
import { DiagramShell, useDiagramLoader } from "../../shared";
import { ErdGraphvizCanvas } from "./erd_graphviz_canvas";
import { loadErdDomainsBundle, type ErdDomainsBundle, type ErdViewerSelection } from "../lib/load_erd_domains_bundle";

export type { ErdViewerSelection };

type ErdViewerProps = {
  selection: ErdViewerSelection;
};

/** Full-page ERD workspace: API JSON rendered with Graphviz WASM in React. */
export function ErdViewer({ selection }: ErdViewerProps) {
  const [includeOneHop, setIncludeOneHop] = useState(true);

  const loadBundle = useCallback(
    () => loadErdDomainsBundle(selection, includeOneHop),
    [selection.qualifier, includeOneHop],
  );

  const { data: bundle, loading, error } = useDiagramLoader(loadBundle);

  return (
    <DiagramShell loading={loading} error={error}>
      {bundle && <ErdGraphvizCanvas bundle={bundle} includeOneHop={includeOneHop} onIncludeOneHopChange={setIncludeOneHop} />}
    </DiagramShell>
  );
}
