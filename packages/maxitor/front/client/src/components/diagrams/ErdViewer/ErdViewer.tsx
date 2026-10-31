// src/components/diagrams/ErdViewer/ErdViewer.tsx
import { useCallback } from "react";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { ErdGraphvizCanvas } from "./parts/ErdGraphvizCanvas";
import { loadErdDomainsBundle, type ErdViewerSelection } from "@/lib/loadErdDomainsBundle";
import { usePageSetting } from "@/lib/pageSettings";

export type { ErdViewerSelection };

type ErdViewerProps = {
  selection: ErdViewerSelection;
};

/** Full-page ERD workspace: API JSON rendered with Graphviz WASM in React. */
export function ErdViewer({ selection }: ErdViewerProps) {
  // A page setting: shared inside a room (spec 028, FR-030).
  const [includeOneHop, setIncludeOneHop] = usePageSetting("one_hop", true);
  const { qualifier } = selection;

  // The base always holds the 1-hop neighbours: 1-hop is applied on the page, over the filters, so switching it
  // neither reloads the diagram nor touches a filter (spec 038).
  const loadBundle = useCallback(() => loadErdDomainsBundle({ kind: "erd", qualifier }, true), [qualifier]);

  const diagramResetKey = qualifier ?? "all";

  const { data: bundle, dataVersion, loading, error } = useDiagramLoader(loadBundle, { keepPreviousData: true });

  return (
    <DiagramShell loading={loading} error={error}>
      {bundle != null && (
        <ErdGraphvizCanvas
          key={`${diagramResetKey}:${dataVersion}`}
          bundle={bundle}
          bundleVersion={dataVersion}
          includeOneHop={includeOneHop}
          onIncludeOneHopChange={setIncludeOneHop}
        />
      )}
    </DiagramShell>
  );
}
