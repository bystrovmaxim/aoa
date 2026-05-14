// src/components/ui/DomainLegend/DomainLegend.tsx
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import {
  floatingLegendPanelSx,
  floatingLegendTitleSx,
  legendDiskImgSx,
  legendRowLabelSx,
  legendRowSx,
} from "@/lib/ui";

export type DomainLegendProps = {
  domainKeys: string[];
  enabledDomains: Set<string>;
  accents: Record<string, string>;
  /** Reserved for future custom per-domain glyphs; legend uses shared Domain disk from ``@/lib/icons``. */
  icons?: Record<string, string>;
  onToggle: (key: string) => void;
};

const ROW_OFF_OPACITY = 0.42;

/** Multi-domain ERD legend — same row chrome as ``NodeTypeLegend``; toggles dim rows, no chip chrome. */
export function DomainLegend({ domainKeys, enabledDomains, accents, onToggle }: DomainLegendProps) {
  if (domainKeys.length <= 1) return null;

  return (
    <Box component="aside" aria-label="Domains" sx={floatingLegendPanelSx}>
      <Typography variant="caption" sx={floatingLegendTitleSx}>
        Domains
      </Typography>
      {domainKeys.map((k) => {
        const on = enabledDomains.has(k);
        const color = accents[k] || "#3b82f6";
        const src = svgDataUriForInterchangeDomainLegend(color);
        return (
          <Box
            key={k}
            component="button"
            type="button"
            title={k}
            onClick={() => onToggle(k)}
            aria-pressed={on}
            sx={{
              ...legendRowSx,
              m: 0,
              p: 0,
              width: "100%",
              border: "none",
              bgcolor: "transparent",
              cursor: "pointer",
              textAlign: "left",
              borderRadius: 0.5,
              opacity: on ? 1 : ROW_OFF_OPACITY,
              transition: "opacity 120ms ease",
              "&:hover": { opacity: on ? 1 : Math.min(ROW_OFF_OPACITY + 0.22, 0.85) },
              "&:focus-visible": {
                outline: "2px solid rgba(59, 130, 246, 0.45)",
                outlineOffset: 1,
              },
            }}
          >
            <Box component="img" src={src} width={20} height={20} alt="" sx={legendDiskImgSx} />
            <Typography variant="caption" sx={legendRowLabelSx}>
              {k}
            </Typography>
          </Box>
        );
      })}
    </Box>
  );
}
