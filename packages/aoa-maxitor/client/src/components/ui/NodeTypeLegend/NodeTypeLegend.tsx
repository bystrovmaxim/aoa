// src/components/ui/NodeTypeLegend/NodeTypeLegend.tsx
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { svgDataUriForGraphNodeIcon } from "@/lib/icons";
import {
  floatingLegendPanelSx,
  floatingLegendTitleSx,
  legendDiskImgSx,
  legendRowLabelSx,
  legendRowSx,
} from "@/lib/ui";

export type NodeTypeLegendItem = { type: string; color: string };

export type NodeTypeLegendProps = {
  items: NodeTypeLegendItem[];
};

/** Full-graph (G6) node-type legend — absolute inside the graph viewport. */
export function NodeTypeLegend({ items }: NodeTypeLegendProps) {
  return (
    <Box component="aside" aria-label="Node types" sx={floatingLegendPanelSx}>
      <Typography variant="caption" sx={floatingLegendTitleSx}>
        Node types
      </Typography>
      {items.map((it) => (
        <Box key={it.type} sx={legendRowSx} title={it.type}>
          <Box
            component="img"
            src={svgDataUriForGraphNodeIcon(it.color, it.type)}
            width={20}
            height={20}
            alt=""
            sx={legendDiskImgSx}
          />
          <Typography variant="caption" sx={legendRowLabelSx}>
            {it.type}
          </Typography>
        </Box>
      ))}
    </Box>
  );
}
