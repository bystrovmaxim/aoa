// packages/aoa-maxitor/client/src/features/diagrams/interchange_graph/node_type_legend.tsx
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { svgDataUriForGraphNodeIcon } from "../../../shared/icons";

export type NodeTypeLegendItem = { type: string; color: string };

export type NodeTypeLegendProps = {
  items: NodeTypeLegendItem[];
};

/** Interchange graph node-type legend — absolute inside the graph viewport. */
export function NodeTypeLegend({ items }: NodeTypeLegendProps) {
  return (
    <Box
      component="aside"
      aria-label="Node types"
      sx={{
        position: "absolute",
        top: 12,
        left: 12,
        zIndex: 40,
        display: "flex",
        flexDirection: "column",
        gap: 0.75,
        p: 1.25,
        minWidth: 132,
        maxWidth: 260,
        maxHeight: "calc(100% - 60px)",
        overflowY: "auto",
        bgcolor: "rgba(255,255,255,0.88)",
        backdropFilter: "blur(8px)",
        border: "1px solid",
        borderColor: "rgba(0,0,0,0.08)",
        borderRadius: 1,
        boxShadow: "0 2px 10px rgba(0,0,0,0.07)",
      }}
    >
      <Typography
        variant="caption"
        sx={{
          fontWeight: 600,
          fontSize: "10px",
          textTransform: "uppercase",
          letterSpacing: "0.04em",
          color: "text.secondary",
          mb: 0.25,
        }}
      >
        Node types
      </Typography>
      {items.map((it) => (
        <Box key={it.type} sx={{ display: "flex", alignItems: "center", gap: 1 }} title={it.type}>
          <Box
            component="img"
            src={svgDataUriForGraphNodeIcon(it.color, it.type)}
            width={20}
            height={20}
            alt=""
            sx={{ borderRadius: "50%", border: "1px solid rgba(0,0,0,0.12)", flexShrink: 0 }}
          />
          <Typography variant="caption" sx={{ fontSize: 11, color: "text.primary" }}>
            {it.type}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
