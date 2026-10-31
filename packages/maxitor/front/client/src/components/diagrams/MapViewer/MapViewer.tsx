// src/components/diagrams/MapViewer/MapViewer.tsx
import Box from "@mui/material/Box";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useRef, useState } from "react";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { DiffCard } from "@/components/history/DiffCard";
import { mapChanges, mapOverview } from "@/api/map";
import { setChangeStepping, type ChangeEntry } from "@/lib/changeStepping";
import { setDiffCounts, useDiffNames } from "@/lib/diffCounts";
import { layoutHash } from "@/lib/layoutHash";
import { countChanges } from "@/lib/mapDiff";
import type { MapCard, MapEngine } from "./mapEngine";

const LAYERS_SX = { position: "absolute", inset: 0, width: "100%", height: "100%" } as const;

/**
 * The full graph as a map (spec 040): named domains far away, what they hold closer. The overview comes first; Sigma
 * is loaded with it, so that no other diagram carries its weight.
 */
export function MapViewer() {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<HTMLDivElement | null>(null);
  const underRef = useRef<HTMLCanvasElement | null>(null);
  const overRef = useRef<HTMLCanvasElement | null>(null);
  const labelRef = useRef<HTMLDivElement | null>(null);
  const engineRef = useRef<MapEngine | null>(null);
  const [layingOut, setLayingOut] = useState(false);
  const [zoomPct, setZoomPct] = useState(100);
  const [mapError, setMapError] = useState<string | null>(null);
  const [card, setCard] = useState<MapCard | null>(null);
  const names = useDiffNames();

  const load = useCallback(async () => {
    const [overview, module] = await Promise.all([mapOverview(() => setLayingOut(true)), import("./mapEngine")]);
    return { overview, module, changes: overview.links_changed === undefined ? [] : await mapChanges() };
  }, []);
  const { data, loading, error } = useDiagramLoader(load);

  useEffect(() => {
    const [stage, sigma, under, over, label] = [stageRef.current, sigmaRef.current, underRef.current, overRef.current, labelRef.current];
    if (!data || !stage || !sigma || !under || !over || !label) return undefined;
    setLayingOut(false);
    let gone = false;
    const { overview, module, changes } = data;
    if (overview.links_changed !== undefined) setDiffCounts(countChanges(changes));
    const areaNames = new Map(overview.areas.map((area) => [area.id, area.name]));
    const entries: ChangeEntry[] = changes.map((change) => ({ key: change.id, title: change.label, detail: change.type, status: change.status, group: areaNames.get(change.area) ?? change.area }));
    let position: number | null = null;
    let cardOpen = false;
    const go = (next: number) => engineRef.current?.goTo(next);
    const mirror = (next: number | null, open: boolean) => engineRef.current?.mirror(next, open);
    const say = () => setChangeStepping(entries.length ? { entries, position, card: cardOpen, go, mirror } : null);
    say();
    const events = {
      onZoom: (zoom: number) => setZoomPct(Math.round(zoom * 100)),
      onCard: (next: MapCard | null) => {
        setCard(next);
        cardOpen = next !== null;
        say();
      },
      onStep: (next: number | null) => {
        position = next;
        say();
      },
    };
    module.MapEngine.create(overview, changes, { stage, sigma, under, over, label }, events)
      .then(async (engine) => {
        if (gone) {
          engine.destroy();
          return;
        }
        engineRef.current = engine;
        const positions = Object.fromEntries(overview.areas.map((area) => [area.id, [area.x, area.y] as [number, number]]));
        stage.setAttribute("data-layout-hash", await layoutHash(positions, overview.areas.map((area) => area.id)));
      })
      .catch((reason: unknown) => setMapError(reason instanceof Error && /webgl/i.test(reason.message) ? "This browser cannot draw the map: WebGL is off. The ERD still works." : String(reason)));
    return () => {
      gone = true;
      stage.removeAttribute("data-layout-hash");
      engineRef.current?.destroy();
      engineRef.current = null;
      setDiffCounts(null);
      setChangeStepping(null);
    };
  }, [data]);

  return (
    <DiagramShell loading={loading && !layingOut} error={error ?? mapError}>
      <Box
        ref={stageRef}
        className="ix-interchange-viewport"
        sx={{ flex: 1, minHeight: 0, minWidth: 0, position: "relative", overflow: "hidden", cursor: "grab", touchAction: "none", "&:active": { cursor: "grabbing" }, bgcolor: "#fbfcfd", backgroundImage: "radial-gradient(#d5dbe3 1px, transparent 1.2px)", backgroundSize: "22px 22px" }}
      >
        <Box component="canvas" ref={underRef} sx={{ ...LAYERS_SX, zIndex: 1 }} />
        <Box ref={sigmaRef} sx={{ ...LAYERS_SX, zIndex: 2 }} />
        <Box component="canvas" ref={overRef} sx={{ ...LAYERS_SX, zIndex: 3, pointerEvents: "none" }} />
        <Box ref={labelRef} sx={{ position: "absolute", zIndex: 12, display: "none", transform: "translateX(-50%)", bgcolor: "#fff", borderLeft: "3px solid #94a3b8", borderRadius: "4px", px: 1, py: "3px", fontSize: 11, boxShadow: "0 2px 8px rgba(0,0,0,.13)", pointerEvents: "none", whiteSpace: "nowrap" }} />
        {layingOut && (
          <Typography variant="caption" sx={{ position: "absolute", zIndex: 12, left: "50%", top: "45%", transform: "translateX(-50%)", color: "text.secondary" }}>
            Laying this version out…
          </Typography>
        )}
        {card && <DiffCard target={card.target} newer={names?.b ?? "B"} at={card.at} onClose={() => setCard(null)} />}
        <ZoomToolbar zoomPct={zoomPct} onZoomIn={() => engineRef.current?.zoomBy(1.5)} onZoomOut={() => engineRef.current?.zoomBy(1 / 1.5)} onFit={() => engineRef.current?.fit()} />
      </Box>
    </DiagramShell>
  );
}
