// src/components/pages/DiagramWorkspacePage/DiagramWorkspacePage.tsx
import Box from "@mui/material/Box";
import type { DiagramSelection } from "@/model/diagramSelection";
import { ErdViewer } from "@/components/diagrams/ErdViewer";
import { FullGraphViewer } from "@/components/diagrams/FullGraphViewer";
import { LifecycleFsmViewer } from "@/components/diagrams/LifecycleFsmViewer";
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
};

/** Central workspace: full graph, ERD, use-case, lifecycle, or empty dotted surface from sidebar selection. */
export function DiagramWorkspacePage({ diagram }: DiagramWorkspacePageProps) {
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
      {diagram?.kind === "interchange_graph" ? (
        <FullGraphViewer key="full-graph" />
      ) : diagram?.kind === "erd" ? (
        <ErdViewer key={diagram.qualifier ?? "all"} selection={diagram} />
      ) : diagram?.kind === "lifecycle_fsm" ? (
        <LifecycleFsmViewer key={diagram.lifecycle_graph_node_id} lifecycleGraphNodeId={diagram.lifecycle_graph_node_id} />
      ) : diagram?.kind === "use_case" ? (
        <UseCaseDiagramViewer key={diagram.domain_qualifier} domainId={diagram.domain_qualifier} />
      ) : (
        <Box sx={EMPTY_WORKSPACE_SX} aria-label="Diagram workspace" />
      )}
    </Box>
  );
}
