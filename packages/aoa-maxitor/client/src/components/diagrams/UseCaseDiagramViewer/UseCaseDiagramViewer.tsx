// src/components/diagrams/UseCaseDiagramViewer/UseCaseDiagramViewer.tsx
import type { Engine } from "@hpcc-js/wasm-graphviz";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactElement, type SVGProps } from "react";
import { useSvgLayoutHash } from "@/lib/useSvgLayoutHash";
import { useSvgDiagramSurface } from "@/rooms/diagramSurface";
import { useGraphvizFocus } from "@/rooms/graphvizFocus";
import { enabledKeys } from "@/lib/freshGraph";
import { useCurrentPage, usePageSetting } from "@/lib/pageSettings";
import { fetchDomainUseCaseDiagram } from "@/api/domainUseCaseDiagram";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { useSvgPanZoom } from "@/components/diagrams/ErdViewer/hooks/useSvgPanZoom";
import {
  LayoutGlyphDotLR,
  LayoutGlyphDotTB,
  LayoutGlyphFdp,
  LayoutGlyphNeato,
} from "@/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/layoutEngineGlyphs";
import { DomainLegend } from "@/components/ui/DomainLegend";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import useCaseRoleActorUrl from "@/assets/useCaseRoleActor.svg?url";
import {
  buildDomainUseCaseDotBundle,
  type DomainUseCaseLayoutEngine,
  type DomainUseCaseRankdir,
} from "@/lib/buildDomainUseCaseDotSource";
import { filterUseCaseDiagramByDomains } from "@/lib/filterUseCaseDiagramByDomains";
import { loadGraphvizWasmFor } from "@/lib/prefetch/erdGraphviz";
import { postProcessGraphvizSvgDom } from "@/lib/sanitizeGraphvizSvgOverlays";
import { diagramCanvasEmptyMessageSx } from "@/lib/ui";
import { bindRoleLabels, roleLabelSx } from "@/lib/useCaseRoleLabels";


const GRID_SX = {
  flex: 1,
  minWidth: 0,
  minHeight: 0,
  position: "relative" as const,
  bgcolor: "#f4f5f7",
  backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
  backgroundSize: "20px 20px",
};

type UseCaseDiagramLayoutPreset = "dot_lr" | "dot_tb" | "neato" | "fdp";


const USE_CASE_LAYOUT_TOOL_ROW: {
  preset: UseCaseDiagramLayoutPreset;
  title: string;
  Glyph: (props: SVGProps<SVGSVGElement>) => ReactElement;
}[] = [
  { preset: "dot_lr", title: "Dot — left to right", Glyph: LayoutGlyphDotLR },
  { preset: "dot_tb", title: "Dot — top to bottom", Glyph: LayoutGlyphDotTB },
  { preset: "neato", title: "Neato (spring)", Glyph: LayoutGlyphNeato },
  { preset: "fdp", title: "FDP (force)", Glyph: LayoutGlyphFdp },
];

function presetToRankdir(preset: UseCaseDiagramLayoutPreset): DomainUseCaseRankdir {
  return preset === "dot_tb" ? "TB" : "LR";
}

function presetToLayoutEngine(preset: UseCaseDiagramLayoutPreset): DomainUseCaseLayoutEngine {
  switch (preset) {
    case "neato":
      return "neato";
    case "fdp":
      return "fdp";
    default:
      return "dot";
  }
}

const graphvizRoleActorImage = {
  path: useCaseRoleActorUrl,
  width: "52px",
  height: "74px",
} as const;

export type UseCaseDiagramViewerProps = {
  domainId: string;
};

export function UseCaseDiagramViewer({ domainId }: UseCaseDiagramViewerProps) {
  const load = useCallback(() => fetchDomainUseCaseDiagram(domainId), [domainId]);
  const { data, loading, error } = useDiagramLoader(load, { keepPreviousData: true });

  // Page settings: the person's own outside a room, the room's inside one (spec 028, FR-030). The
  // direction is part of the layout preset (``dot_lr`` / ``dot_tb``), so it needs no setting of its own.
  const [layoutPreset, setLayoutPreset] = usePageSetting<UseCaseDiagramLayoutPreset>("layout", "dot_lr");
  /** LR/TB + Neato/FDP when Boundary is off; Boundary on keeps the preset for when it goes off again. */
  const [boundary, setBoundary] = usePageSetting("boundary", true);

  /** Boundary on forces hierarchical dot ranks; preserve neato/fdp in ``layoutPreset`` for when Boundary turns off. */
  const layoutForBundler = useMemo((): UseCaseDiagramLayoutPreset => {
    if (boundary) {
      if (layoutPreset === "dot_lr" || layoutPreset === "dot_tb") return layoutPreset;
      return "dot_lr";
    }
    return layoutPreset;
  }, [boundary, layoutPreset]);

  const domainKeyList = useMemo(() => {
    if (!data) return [];
    const u = new Set(data.actions.map((a) => a.domain_id));
    return [...u].sort();
  }, [data]);

  const accents = useMemo(() => {
    if (!data) return {};
    const m: Record<string, string> = {};
    for (const a of data.actions) {
      if (m[a.domain_id] === undefined) m[a.domain_id] = a.accent_color;
    }
    return m;
  }, [data]);

  const rowLabels = useMemo(() => {
    if (!data) return {};
    const m: Record<string, string> = {};
    for (const a of data.actions) {
      if (m[a.domain_id] === undefined) m[a.domain_id] = a.domain_short_label || a.domain_id;
    }
    return m;
  }, [data]);

  /** The domains switched on; ``null`` until someone chooses, which means all of them. */
  const [chosenDomains, setChosenDomains] = usePageSetting<string[] | null>("domains", null);

  // A domain the model no longer has stops applying (spec 028, FR-076).
  const effectiveEnabled = useMemo(
    () => new Set(data ? enabledKeys([...new Set(data.actions.map((a) => a.domain_id))].sort(), chosenDomains) : []),
    [data, chosenDomains],
  );

  const filtered = useMemo(
    () => (data != null ? filterUseCaseDiagramByDomains(data, effectiveEnabled) : null),
    [data, effectiveEnabled],
  );

  const bundle = useMemo(
    () =>
      filtered != null
        ? buildDomainUseCaseDotBundle(
            filtered,
            presetToRankdir(layoutForBundler),
            { roleActorImageUrl: useCaseRoleActorUrl },
            { boundary, layoutEngine: presetToLayoutEngine(layoutForBundler) },
          )
        : null,
    [filtered, layoutForBundler, boundary],
  );

  const graphvizEngineForBundle = useMemo(
    (): Engine => presetToLayoutEngine(layoutForBundler) as Engine,
    [layoutForBundler],
  );

  const dot = bundle?.dot ?? "";

  // Each change is sent as the whole new set, never as a toggle (FR-031).
  const toggleDomain = useCallback(
    (key: string) => {
      const next = new Set(effectiveEnabled);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      setChosenDomains([...next].sort());
    },
    [effectiveEnabled, setChosenDomains],
  );

  const panZoom = useSvgPanZoom({
    fitBottomInset: 56,
    fitMarginPx: 14,
    fitBoundsSelector: "g.graph g.node, g.graph g.edge, g.graph g.cluster",
  });
  const { viewportRef, pannerRef, zoomPct, zoomIn, zoomOut, fitToContainer, bindInteractions, resetFitFlag } = panZoom;

  const [svgMarkup, setSvgMarkup] = useState("");
  // Graphviz's own output goes on screen unchanged, so its hash is the picture's (FR-005, FR-090).
  const layoutHashValue = useSvgLayoutHash(svgMarkup);
  // The text Graphviz is given, hashed: the settings digest a room compares layouts under (FR-093).
  const layoutInputDigest = useSvgLayoutHash(svgMarkup ? `${graphvizEngineForBundle}\n${dot}` : "");
  const [svgRenderVersion, setSvgRenderVersion] = useState(0);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [firstFitDone, setFirstFitDone] = useState(false);
  // Registered after the second fit (one frame after the first), so a placed view is not undone.
  useSvgDiagramSurface(viewportRef, panZoom, Boolean(svgMarkup) && firstFitDone);
  // Hover and tooltip shared with followers, and the followed person's shown here (spec 029).
  useGraphvizFocus(pannerRef.current, svgMarkup, useCurrentPage(), "node");
  // A role's label shows only while the role is hovered (spec 029, FR-042).
  useEffect(() => {
    const panner = pannerRef.current;
    if (!panner) return undefined;
    const controller = new AbortController();
    bindRoleLabels(panner, controller.signal);
    return () => controller.abort();
  }, [pannerRef, svgMarkup]);
  const prevDotRef = useRef<string | null>(null);

  useLayoutEffect(() => {
    const d = bundle?.dot ?? "";
    if (d === prevDotRef.current) return;
    const prev = prevDotRef.current;
    prevDotRef.current = d;
    setFirstFitDone(false);
    resetFitFlag();
    if (prev !== null) {
      setSvgMarkup("");
    }
  }, [dot, resetFitFlag]);

  useEffect(() => {
    if (!bundle) {
      setSvgMarkup("");
      setRenderError(null);
      return;
    }
    let cancelled = false;
    setRenderError(null);
    const needsRoleImages = (filtered?.roles.length ?? 0) > 0;
    loadGraphvizWasmFor(graphvizEngineForBundle)
      .then((gv) => {
        if (cancelled) return;
        const images = [
          ...bundle.actionImages,
          ...(needsRoleImages ? [graphvizRoleActorImage] : []),
        ];
        const svg = gv.layout(bundle.dot, "svg", graphvizEngineForBundle, {
          files: bundle.files,
          images,
        });
        if (cancelled) return;
        setSvgMarkup(svg);
        setSvgRenderVersion((v) => v + 1);
      })
      .catch((e) => {
        if (!cancelled) setRenderError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
    };
  }, [bundle, filtered, graphvizEngineForBundle]);

  useLayoutEffect(() => {
    if (!svgMarkup) return;
    const panner = pannerRef.current;
    if (!panner) return;

    const svg = panner.querySelector("svg");
    if (svg instanceof SVGSVGElement) {
      svg.removeAttribute("width");
      svg.removeAttribute("height");
      const vb = svg.viewBox.baseVal;
      if (Number.isFinite(vb.width) && vb.width > 0) {
        svg.style.width = `${vb.width}px`;
      }
      if (Number.isFinite(vb.height) && vb.height > 0) {
        svg.style.height = `${vb.height}px`;
      }

      postProcessGraphvizSvgDom(svg);
    }

    let unbindPan: (() => void) | undefined;
    let cancelled = false;
    let raf1: number;
    let raf2: number;
    let raf3: number;
    let raf4: number | undefined;

    const doFitAndBind = () => {
      if (cancelled) return;
      fitToContainer();
      raf4 = requestAnimationFrame(() => {
        if (cancelled) return;
        fitToContainer();
        unbindPan = bindInteractions();
        setFirstFitDone(true);
      });
    };

    raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        raf3 = requestAnimationFrame(doFitAndBind);
      });
    });

    return () => {
      cancelled = true;
      unbindPan?.();
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      cancelAnimationFrame(raf3);
      if (raf4 !== undefined) cancelAnimationFrame(raf4);
    };
  }, [svgMarkup, svgRenderVersion, fitToContainer, bindInteractions]);

  return (
    <DiagramShell loading={loading} error={error}>
      {data != null ? (
        <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0 }}>
          <Box sx={GRID_SX}>
            <DomainLegend
              domainKeys={domainKeyList}
              enabledDomains={effectiveEnabled}
              accents={accents}
              rowLabels={rowLabels}
              showWhenSingle
              onToggle={toggleDomain}
            />
            {filtered != null && filtered.actions.length === 0 && (
              <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
                {data.actions.length === 0
                  ? "No actions in this domain."
                  : "No actions for the selected domains."}
              </Typography>
            )}
            {renderError != null && (
              <Typography color="error" variant="body2" sx={{ position: "absolute", left: 8, top: 8, zIndex: 2 }}>
                {renderError}
              </Typography>
            )}
            <Box
              ref={viewportRef}
              data-layout-hash={layoutHashValue}
              data-layout-input={layoutInputDigest}
              sx={{
                position: "absolute",
                inset: 0,
                overflow: "hidden",
                cursor: "grab",
                touchAction: "none",
                zIndex: 1,
                "&.erd-panning": { cursor: "grabbing" },
                "&.erd-wheel-zooming .use-case-panner": { pointerEvents: "none" },
              }}
            >
              <Box
                ref={pannerRef}
                className="use-case-panner"
                sx={{
                  position: "absolute",
                  left: 0,
                  top: 0,
                  transformOrigin: "0 0",
                  display: "block",
                  opacity: firstFitDone ? 1 : 0,
                  pointerEvents: firstFitDone ? "auto" : "none",
                  transition: "none",
                  "& svg": {
                    display: "block",
                    maxWidth: "none",
                    width: "auto",
                    height: "auto",
                    overflow: "visible",
                    transformOrigin: "0 0",
                  },
                  ...roleLabelSx,
                }}
                dangerouslySetInnerHTML={{ __html: svgMarkup }}
              />
            </Box>

            <ZoomToolbar zoomPct={zoomPct} onZoomIn={zoomIn} onZoomOut={zoomOut} onFit={fitToContainer}>
              <Box
                component="span"
                aria-hidden
                sx={{ width: "1px", height: "22px", bgcolor: "rgba(15, 23, 42, 0.12)", flexShrink: 0, mx: "2px" }}
              />
              <ToggleButtonGroup
                exclusive
                size="small"
                value={layoutForBundler}
                onChange={(_, v: UseCaseDiagramLayoutPreset | null) => {
                  if (v !== null) setLayoutPreset(v);
                }}
                sx={{
                  flexWrap: "wrap",
                  gap: "1px",
                  bgcolor: "transparent",
                  "& .MuiToggleButtonGroup-grouped": { border: 0, borderRadius: "8px !important", mx: 0 },
                  "& .MuiToggleButton-root": {
                    px: 0.35, py: 0.25, minWidth: 30, fontSize: 15, lineHeight: 1,
                    border: "none", bgcolor: "transparent", color: "#64748b",
                    "&:hover": { bgcolor: "rgba(15, 23, 42, 0.06)", color: "#0f172a" },
                    "&.Mui-selected": { color: "#1d4ed8", bgcolor: "transparent !important" },
                    "&.Mui-selected:hover": { bgcolor: "rgba(15, 23, 42, 0.06) !important", color: "#1d4ed8" },
                  },
                }}
              >
                {(boundary ? USE_CASE_LAYOUT_TOOL_ROW.slice(0, 2) : USE_CASE_LAYOUT_TOOL_ROW).map(({ preset, title, Glyph: LayoutGlyph }) => (
                  <ToggleButton key={preset} value={preset} aria-label={title}>
                    <Tooltip title={title} placement="top">
                      <Box component="span" sx={{ display: "flex", alignItems: "center", justifyContent: "center", width: "1em", height: "1em" }}>
                        <LayoutGlyph />
                      </Box>
                    </Tooltip>
                  </ToggleButton>
                ))}
              </ToggleButtonGroup>
              <Box
                component="span"
                aria-hidden
                sx={{ width: "1px", height: "22px", bgcolor: "rgba(15, 23, 42, 0.12)", flexShrink: 0, mx: "2px" }}
              />
              <OneHopToggle checked={boundary} onChange={setBoundary} label="Boundary" />
            </ZoomToolbar>
          </Box>
        </Box>
      ) : null}
    </DiagramShell>
  );
}
