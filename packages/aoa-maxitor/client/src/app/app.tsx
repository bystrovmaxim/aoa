// packages/aoa-maxitor/client/src/app/app.tsx
import { useMemo, useState } from "react";
import {
  buildSidebarGroupedMaps,
  SidebarNav,
  useSidebarPayload,
  type DiagramSelection,
} from "../features";
import { MainLayout } from "./layout/main_layout";
import { MainDiagramView } from "./views/main_diagram_view";

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
      <MainDiagramView diagram={diagram} />
    </MainLayout>
  );
}
