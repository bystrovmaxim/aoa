// src/components/diagrams/ErdViewer/ErdViewer.tsx
import { useCallback, useState } from "react";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { ErdGraphvizCanvas } from "./parts/ErdGraphvizCanvas";
import { loadErdDomainsBundle, type ErdViewerSelection } from "@/lib/loadErdDomainsBundle";

export type { ErdViewerSelection };

type ErdViewerProps = {
  selection: ErdViewerSelection;
};

/** Full-page ERD workspace: API JSON rendered with Graphviz WASM in React. */
export function ErdViewer({ selection }: ErdViewerProps) {
  const [includeOneHop, setIncludeOneHop] = useState(true);
  const { qualifier } = selection;

  const loadBundle = useCallback(
    () => loadErdDomainsBundle({ kind: "erd", qualifier }, includeOneHop),
    [qualifier, includeOneHop],
  );

  const { data: bundle, loading, error } = useDiagramLoader(loadBundle);

  return (
    <DiagramShell loading={loading} error={error}>
      {bundle && <ErdGraphvizCanvas bundle={bundle} includeOneHop={includeOneHop} onIncludeOneHopChange={setIncludeOneHop} />}
    </DiagramShell>
  );
}
