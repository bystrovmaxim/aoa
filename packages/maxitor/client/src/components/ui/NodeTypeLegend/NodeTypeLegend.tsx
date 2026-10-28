// src/components/ui/NodeTypeLegend/NodeTypeLegend.tsx
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { svgDataUriForGraphNodeIcon } from "@/lib/icons";
import { legendDiskImgSx, legendRowLabelSx, legendRowSx } from "@/lib/ui";
import { CollapsibleLegendPanel } from "@/components/ui/CollapsibleLegendPanel";

export type NodeTypeLegendItem = { type: string; color: string };

export type NodeTypeLegendProps = {
  items: NodeTypeLegendItem[];
};

/** Full-graph (G6) node-type legend — absolute inside the graph viewport. */
export function NodeTypeLegend({ items }: NodeTypeLegendProps) {
  return (
    <CollapsibleLegendPanel ariaLabel="Node types" title="Node types">
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
    </CollapsibleLegendPanel>
  );
}
