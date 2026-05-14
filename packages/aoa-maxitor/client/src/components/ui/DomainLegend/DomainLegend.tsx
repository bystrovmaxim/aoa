// src/components/ui/DomainLegend/DomainLegend.tsx
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Typography from "@mui/material/Typography";

export type DomainLegendProps = {
  domainKeys: string[];
  enabledDomains: Set<string>;
  accents: Record<string, string>;
  icons: Record<string, string>;
  onToggle: (key: string) => void;
};

/** Multi-domain ERD legend with toggles — absolute inside the graph viewport. */
export function DomainLegend({ domainKeys, enabledDomains, accents, icons, onToggle }: DomainLegendProps) {
  if (domainKeys.length <= 1) return null;

  return (
    <Box
      component="aside"
      aria-label="Domains"
      sx={{
        position: "absolute",
        top: 12,
        left: 12,
        zIndex: 40,
        maxHeight: "calc(100% - 60px)",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 0.5,
        p: 1,
        minWidth: 180,
        maxWidth: 260,
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
          px: 0.5,
        }}
      >
        Domains
      </Typography>
      {domainKeys.map((k) => {
        const on = enabledDomains.has(k);
        const color = accents[k] || "#3b82f6";
        const iconSrc = icons[k];
        return (
          <Button
            key={k}
            size="small"
            variant={on ? "contained" : "outlined"}
            onClick={() => onToggle(k)}
            sx={{
              justifyContent: "flex-start",
              textTransform: "none",
              minWidth: 140,
              ...(on
                ? { bgcolor: color, "&:hover": { bgcolor: color } }
                : { borderColor: color, color: "text.primary" }),
            }}
            startIcon={
              iconSrc ? (
                <Box component="img" src={iconSrc} alt="" sx={{ width: 18, height: 18 }} />
              ) : (
                <Box sx={{ width: 14, height: 14, borderRadius: "50%", bgcolor: color }} />
              )
            }
          >
            {k}
          </Button>
        );
      })}
    </Box>
  );
}
