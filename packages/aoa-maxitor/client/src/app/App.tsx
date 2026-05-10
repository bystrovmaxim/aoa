// packages/aoa-maxitor/client/src/app/App.tsx
import { useMemo, useState } from "react";
import { SidebarNav } from "../features/sidebar/SidebarNav";
import { buildSidebarGroupedMaps } from "../features/sidebar/model";
import { useSidebarPayload } from "../features/sidebar/useSidebarPayload";
import { DiagramWorkspace } from "../features/diagram-viewer/DiagramWorkspace";
import { MainLayout } from "./layout/MainLayout";

export function App() {
  const { sidebar, error } = useSidebarPayload();
  const [diagramUrl, setDiagramUrl] = useState<string | null>(null);

  const group = useMemo(() => (sidebar ? buildSidebarGroupedMaps(sidebar) : null), [sidebar]);

  return (
    <MainLayout
      sidebar={
        <SidebarNav sidebar={sidebar} group={group} error={error} diagramUrl={diagramUrl} onSelectDiagram={setDiagramUrl} />
      }
    >
      <DiagramWorkspace diagramUrl={diagramUrl} />
    </MainLayout>
  );
}
