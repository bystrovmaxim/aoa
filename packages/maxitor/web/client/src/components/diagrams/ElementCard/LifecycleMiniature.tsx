// src/components/diagrams/ElementCard/LifecycleMiniature.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import { useEffect, useState } from "react";
import { LIFECYCLE_FADED_CLASS } from "@/lib/buildLifecycleFsmDotSource";
import { lifecycleMiniature } from "@/lib/lifecycleMiniature";
import { lifecycleSelection, useOpenDiagram } from "@/lib/openDiagram";

/** How tall a miniature may stand; a long lifecycle shrinks to its whole width first. */
const MINIATURE_MAX_HEIGHT_PX = 220;

/** The drawing's own width, from its ``viewBox``; ``0`` when it has none. */
export function drawnWidth(svg: string | null | undefined): number {
  return Number(/viewBox="[-\d.]+ [-\d.]+ ([\d.]+)/.exec(svg ?? "")?.[1] ?? 0);
}

/**
 * A lifecycle fitted whole into the card (spec 043, FR-015 – FR-019); a click opens the full diagram. ``fullWidth`` is the
 * drawn width that fills the card: one for all the pictures of a card, so that they share one scale.
 */
export function LifecycleMiniature({
  lifecycleId,
  fullWidth,
  dimmed = false,
  onSettled,
}: {
  lifecycleId: string;
  fullWidth?: number;
  /** Another lifecycle of the card is pointed at. */
  dimmed?: boolean;
  onSettled?: (width: number) => void;
}) {
  const [svg, setSvg] = useState<string | null | undefined>(undefined);
  const [failed, setFailed] = useState(false);
  const open = useOpenDiagram();

  useEffect(() => {
    let live = true;
    setSvg(undefined);
    setFailed(false);
    lifecycleMiniature(lifecycleId).then(
      (drawn) => {
        if (!live) return;
        setSvg(drawn);
        onSettled?.(drawnWidth(drawn));
      },
      () => {
        if (!live) return;
        setFailed(true);
        onSettled?.(0);
      },
    );
    return () => {
      live = false;
    };
    // ``onSettled`` is a new function every render; the read belongs to the lifecycle alone.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [lifecycleId]);

  if (failed || svg === null) return <Box sx={{ mt: "6px", color: "#64748b" }}>The lifecycle could not be read.</Box>;
  if (svg === undefined) return <Box sx={{ mt: "6px", color: "#64748b" }}>Reading…</Box>;
  return (
    <ButtonBase
      data-testid="lifecycle-miniature"
      aria-label="Open the full lifecycle diagram"
      onClick={() => open?.(lifecycleSelection(lifecycleId))}
      sx={{
        display: "block",
        width: "100%",
        mt: "6px",
        opacity: dimmed ? 0.25 : 1,
        transition: "opacity 120ms",
        [`& .${LIFECYCLE_FADED_CLASS}`]: { opacity: 0.3 },
        "& svg": { display: "block", margin: "0 auto", width: fullWidth ? `${Math.min(100, (drawnWidth(svg) / fullWidth) * 100)}%` : "100%", height: "auto", maxHeight: MINIATURE_MAX_HEIGHT_PX },
      }}
    >
      <Box component="span" sx={{ display: "block" }} dangerouslySetInnerHTML={{ __html: svg }} />
    </ButtonBase>
  );
}
