// src/app/App.tsx
import { useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { DiagramWorkspacePage } from "@/components/pages/DiagramWorkspacePage";
import { LeftSidebar } from "@/components/navigation/LeftSidebar";
import type { DiagramSelection } from "@/model/diagramSelection";

export function App() {
  const [diagram, setDiagram] = useState<DiagramSelection | null>(null);

  return (
    <MainLayout sidebar={<LeftSidebar diagram={diagram} onSelectDiagram={setDiagram} />}>
      <DiagramWorkspacePage diagram={diagram} />
    </MainLayout>
  );
}
