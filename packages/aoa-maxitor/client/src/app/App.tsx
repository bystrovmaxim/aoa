// packages/aoa-maxitor/client/src/app/App.tsx
import { useMemo, useState } from "react";
import { DiagramWorkspace, type DiagramSelection } from "../features/diagram-viewer";
import { SidebarNav } from "../features/sidebar/SidebarNav";
import { buildSidebarGroupedMaps } from "../features/sidebar/model";
import { useSidebarPayload } from "../features/sidebar/useSidebarPayload";
import { MainLayout } from "./layout/MainLayout";

export function App() {
  const { sidebar, error } = useSidebarPayload();
  const [diagram, setDiagram] = useState<DiagramSelection | null>(null);

  const group = useMemo(() => (sidebar ? buildSidebarGroupedMaps(sidebar) : null), [sidebar]);

  return (
    <MainLayout
      sidebar={
        <SidebarNav sidebar={sidebar} group={group} error={error} diagram={diagram} onSelectDiagram={setDiagram} />
      }
    >
      <DiagramWorkspace diagram={diagram} />
    </MainLayout>
  );
}
