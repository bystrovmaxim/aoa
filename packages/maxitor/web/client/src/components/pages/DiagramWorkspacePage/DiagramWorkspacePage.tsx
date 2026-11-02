// src/components/pages/DiagramWorkspacePage/DiagramWorkspacePage.tsx
import Box from "@mui/material/Box";
import type { DiagramSelection } from "@/model/diagramSelection";
import { ErdViewer } from "@/components/diagrams/ErdViewer";
import { SideBySide } from "@/components/diagrams/SideBySide";
import type { Half } from "@/lib/half";
import { MapViewer } from "@/components/diagrams/MapViewer";
import { LifecycleFsmViewer } from "@/components/diagrams/LifecycleFsmViewer";
import { EventsDiagramViewer } from "@/components/diagrams/EventsDiagramViewer";
import { UseCaseDiagramViewer } from "@/components/diagrams/UseCaseDiagramViewer";

/** Same dot grid as ``ErdGraphvizCanvas`` — empty workspace before any diagram is chosen. */
const EMPTY_WORKSPACE_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
} as const;

type DiagramWorkspacePageProps = {
  diagram: DiagramSelection | null;
  /** Go to the ERD of all domains, for a browser that cannot draw the map. */
  onOpenErd?: () => void;
  /** Open a page from a link on a card. */
  onOpenDiagram?: (selection: DiagramSelection) => void;
  /** In Side by side, the two versions; ``null`` shows one diagram (spec 044). */
  halves?: { a: Half; b: Half } | null;
};

/** The viewer of ``diagram``, or the empty surface. */
function DiagramOf({ diagram, onOpenErd, onOpenDiagram }: Pick<DiagramWorkspacePageProps, "diagram" | "onOpenErd" | "onOpenDiagram">) {
  if (diagram?.kind === "interchange_graph") return <MapViewer key="full-graph" onOpenErd={onOpenErd} />;
  if (diagram?.kind === "erd") return <ErdViewer key={diagram.qualifier ?? "all"} selection={diagram} />;
  if (diagram?.kind === "lifecycle_fsm") return <LifecycleFsmViewer key={diagram.lifecycle_graph_node_id} lifecycleGraphNodeId={diagram.lifecycle_graph_node_id} />;
  if (diagram?.kind === "use_case") return <UseCaseDiagramViewer key={diagram.domain_qualifier} domainId={diagram.domain_qualifier} />;
  if (diagram?.kind === "use_case_all") return <UseCaseDiagramViewer key="all" domainId={null} />;
  if (diagram?.kind === "events") return <EventsDiagramViewer key={diagram.domain_qualifier} domainId={diagram.domain_qualifier} onOpen={onOpenDiagram} />;
  if (diagram?.kind === "events_all") return <EventsDiagramViewer key="all" domainId={null} onOpen={onOpenDiagram} />;
  return <Box sx={EMPTY_WORKSPACE_SX} aria-label="Diagram workspace" />;
}

/** Central workspace: full graph, ERD, use-case, lifecycle, or empty dotted surface from sidebar selection. */
export function DiagramWorkspacePage({ diagram, onOpenErd, onOpenDiagram, halves = null }: DiagramWorkspacePageProps) {
  return (
    <Box
      sx={{
        flex: 1,
        minWidth: 0,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        bgcolor: "#f4f5f7",
        overflow: "hidden",
      }}
    >
      {halves ? (
        <SideBySide a={halves.a} b={halves.b}>
          <DiagramOf diagram={diagram} onOpenErd={onOpenErd} onOpenDiagram={onOpenDiagram} />
        </SideBySide>
      ) : (
        <DiagramOf diagram={diagram} onOpenErd={onOpenErd} onOpenDiagram={onOpenDiagram} />
      )}
    </Box>
  );
}
