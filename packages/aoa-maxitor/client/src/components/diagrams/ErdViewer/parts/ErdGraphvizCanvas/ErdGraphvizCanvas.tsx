// src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx
import type { Engine } from "@hpcc-js/wasm-graphviz";
import Box from "@mui/material/Box";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactElement, type SVGProps } from "react";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { DomainLegend } from "@/components/ui/DomainLegend";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { loadGraphvizWasm } from "../../hooks/useGraphviz";
import { useSvgPanZoom } from "../../hooks/useSvgPanZoom";
import {
  buildDotSource,
  erdGraphvizEngine,
  type ErdEntity,
  type ErdGraphPayload,
  type ErdGraphvizLayout,
  type ErdRelation,
} from "@/lib/buildDotSource";
import { enrichErdDataForViewer } from "@/lib/enrichErdData";
import type { ErdDomainsBundle } from "@/lib/loadErdDomainsBundle";
import {
  LayoutGlyphCirco,
  LayoutGlyphDotLR,
  LayoutGlyphDotTB,
  LayoutGlyphFdp,
  LayoutGlyphNeato,
} from "./layoutEngineGlyphs";

function mergeDomainPayloads(parts: ErdGraphPayload[]): ErdGraphPayload {
  const nodeById = new Map<string, ErdEntity>();
  const seenRelations = new Set<string>();
  const relationsOut: ErdRelation[] = [];
  const edgeSig = (e: ErdRelation) => `${e.source}\u001f${e.target}\u001f${e.label ?? ""}`;
  for (const part of parts) {
    for (const n of part.entities ?? []) nodeById.set(n.id, n);
    for (const e of part.relations ?? []) {
      const sig = edgeSig(e);
      if (seenRelations.has(sig)) continue;
      seenRelations.add(sig);
      relationsOut.push(e);
    }
  }
  return { entities: [...nodeById.values()], relations: relationsOut };
}

function getMergedFromDomains(enriched: Record<string, unknown>, enabled: Set<string>): ErdGraphPayload {
  const domainsRaw = enriched.domains;
  if (!domainsRaw || typeof domainsRaw !== "object") {
    return { entities: [], relations: [] };
  }
  const domains = domainsRaw as Record<string, { entities?: ErdEntity[]; relations?: ErdRelation[] }>;
  const keys = Object.keys(domains);
  if (!keys.length) return { entities: [], relations: [] };
  const on = keys.filter((k) => enabled.has(k));
  if (!on.length) return { entities: [], relations: [] };
  if (on.length === 1) {
    const slice = domains[on[0]!]!;
    return { entities: slice.entities ?? [], relations: slice.relations ?? [] };
  }
  return mergeDomainPayloads(
    on.map((k) => ({
      entities: domains[k]!.entities ?? [],
      relations: domains[k]!.relations ?? [],
    })),
  );
}

export type ErdGraphvizCanvasProps = {
  bundle: ErdDomainsBundle;
  diagramResetKey: string;
  includeOneHop: boolean;
  onIncludeOneHopChange: (next: boolean) => void;
};

const LAYOUT_TOOLS: {
  value: ErdGraphvizLayout;
  title: string;
  Glyph: (props: SVGProps<SVGSVGElement>) => ReactElement;
}[] = [
  { value: "gv-dot-lr", title: "Dot — left to right", Glyph: LayoutGlyphDotLR },
  { value: "gv-dot-tb", title: "Dot — top to bottom", Glyph: LayoutGlyphDotTB },
  { value: "gv-neato", title: "Neato (spring)", Glyph: LayoutGlyphNeato },
  { value: "gv-fdp", title: "FDP (force)", Glyph: LayoutGlyphFdp },
  { value: "gv-circo", title: "Circo (circular)", Glyph: LayoutGlyphCirco },
];

export function ErdGraphvizCanvas({
  bundle,
  diagramResetKey,
  includeOneHop,
  onIncludeOneHopChange,
}: ErdGraphvizCanvasProps) {
  const [layout, setLayout] = useState<ErdGraphvizLayout>("gv-dot-lr");
  const [svgMarkup, setSvgMarkup] = useState("");
  const [renderError, setRenderError] = useState<string | null>(null);
  const [gvBusy, setGvBusy] = useState(false);

  const enriched = useMemo(
    () => enrichErdDataForViewer(bundle as unknown as Record<string, unknown>),
    [bundle],
  );

  const domainKeyList = useMemo(() => {
    const d = enriched.domains as Record<string, unknown> | undefined;
    return d ? Object.keys(d).sort() : [];
  }, [enriched]);

  const [enabledDomains, setEnabledDomains] = useState(
    () => new Set(Object.keys(bundle.domains ?? {}).sort()),
  );

  const prevDiagramKeyRef = useRef<string | null>(null);

  const { viewportRef, pannerRef, zoomPct, fitToContainer, zoomIn, zoomOut, bindInteractions, resetFitFlag } =
    useSvgPanZoom();

  useLayoutEffect(() => {
    const keys = Object.keys(bundle.domains ?? {}).sort();
    const all = new Set(keys);
    const prevKey = prevDiagramKeyRef.current;
    const sameDiagram = prevKey === diagramResetKey;
    prevDiagramKeyRef.current = diagramResetKey;

    if (prevKey === null || !sameDiagram) {
      setEnabledDomains(all);
      return;
    }

    setEnabledDomains((prevEnabled) => {
      const merged = new Set(keys.filter((k) => prevEnabled.has(k)));
      return merged.size > 0 ? merged : all;
    });
  }, [bundle, diagramResetKey]);

  const mergedData = useMemo(
    () => getMergedFromDomains(enriched, enabledDomains),
    [enriched, enabledDomains],
  );

  const dot = useMemo(() => buildDotSource(mergedData, layout), [mergedData, layout]);

  // Reset fit flag whenever the DOT source changes (new diagram, layout mode, or 1-hop toggle)
  // so the next SVG insertion always re-fits
  const prevDotRef = useRef<string>("");
  useLayoutEffect(() => {
    if (dot !== prevDotRef.current) {
      prevDotRef.current = dot;
      resetFitFlag();
    }
  }, [dot, resetFitFlag]);

  useEffect(() => {
    let cancelled = false;
    setGvBusy(true);
    setRenderError(null);
    loadGraphvizWasm()
      .then((gv) => {
        if (cancelled) return;
        const engine = erdGraphvizEngine(layout) as Engine;
        const svg = gv.layout(dot, "svg", engine);
        if (cancelled) return;
        setSvgMarkup(svg);
      })
      .catch((e) => {
        if (!cancelled) setRenderError(e instanceof Error ? e.message : String(e));
      })
      .finally(() => {
        if (!cancelled) setGvBusy(false);
      });
    return () => {
      cancelled = true;
    };
  }, [dot, layout]);

  useLayoutEffect(() => {
    if (!svgMarkup) return;
    const panner = pannerRef.current;
    if (!panner) return;

    const ac = new AbortController();
    const svg = panner.querySelector("svg");
    if (svg) {
      // Remove size constraints so getBBox works correctly
      svg.removeAttribute("width");
      svg.removeAttribute("height");

      const gg = svg.querySelector("g.graph");
      const bgPoly = gg?.querySelector("polygon");
      if (bgPoly) {
        const fill = String(bgPoly.getAttribute("fill") || "").toLowerCase().trim();
        const backdrop =
          fill === "#f8fafc" ||
          fill === "#f4f5f7" ||
          fill === "#ffffff" ||
          fill === "#fff" ||
          fill === "white" ||
          fill === "lightgray" ||
          fill === "lightgrey";
        if (backdrop) {
          bgPoly.remove();
        }
      }
    }

    const onEnter = (evt: Event) => {
      const el = evt.currentTarget as Element;
      const title = el.querySelector("title")?.textContent?.trim() || "";
      panner.querySelectorAll("g.node").forEach((n) => {
        (n as HTMLElement).style.opacity =
          n.querySelector("title")?.textContent?.trim() === title ? "1" : "0.35";
      });
      panner.querySelectorAll("g.edge").forEach((e) => {
        const edgeTitle = e.querySelector("title")?.textContent?.trim() || "";
        (e as HTMLElement).style.opacity = edgeTitle.includes(title) ? "1" : "0.2";
      });
    };
    const onLeave = () => {
      panner.querySelectorAll("g.node").forEach((n) => {
        (n as HTMLElement).style.opacity = "1";
      });
      panner.querySelectorAll("g.edge").forEach((e) => {
        (e as HTMLElement).style.opacity = "1";
      });
    };

    panner.querySelectorAll("g.node").forEach((node) => {
      (node as HTMLElement).style.cursor = "pointer";
      node.addEventListener("mouseenter", onEnter, { signal: ac.signal });
      node.addEventListener("mouseleave", onLeave, { signal: ac.signal });
    });

    // Use triple-rAF to ensure the browser has fully laid out and painted the SVG
    // before we measure getBBox() and compute the fit transform.
    let unbindPan: (() => void) | undefined;
    let cancelled = false;

    const doFitAndBind = () => {
      if (cancelled) return;
      fitToContainer();
      unbindPan = bindInteractions();
    };

    let raf1: number;
    let raf2: number;
    let raf3: number;

    raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(() => {
        raf3 = requestAnimationFrame(doFitAndBind);
      });
    });

    return () => {
      cancelled = true;
      ac.abort();
      unbindPan?.();
      cancelAnimationFrame(raf1);
      cancelAnimationFrame(raf2);
      cancelAnimationFrame(raf3);
    };
  }, [svgMarkup, fitToContainer, bindInteractions]);

  const accents = (enriched.domain_accent_colors ?? {}) as Record<string, string>;
  const icons = (enriched.domain_legend_icons ?? {}) as Record<string, string>;

  const toggleDomain = (key: string) => {
    setEnabledDomains((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  return (
    <Box sx={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 0, minWidth: 0, position: "relative" }}>
      {renderError && (
        <Typography color="error" variant="body2" sx={{ p: 1 }}>
          {renderError}
        </Typography>
      )}
      <Box
        sx={{
          flex: 1,
          position: "relative",
          minHeight: 0,
          bgcolor: "#f4f5f7",
          backgroundImage: "radial-gradient(rgba(160, 168, 180, 0.42) 1px, transparent 1px)",
          backgroundSize: "20px 20px",
        }}
      >
        <DomainLegend
          domainKeys={domainKeyList}
          enabledDomains={enabledDomains}
          accents={accents}
          icons={icons}
          onToggle={toggleDomain}
        />

        <Box
          ref={viewportRef}
          className="erd-svg-viewport"
          sx={{
            position: "absolute",
            inset: 0,
            overflow: "hidden",
            cursor: "grab",
            touchAction: "none",
            zIndex: 1,
            "&.erd-panning": { cursor: "grabbing" },
          }}
        >
          {gvBusy && !svgMarkup && (
            <Typography variant="body2" sx={{ p: 2, color: "text.secondary" }}>
              Loading Graphviz…
            </Typography>
          )}
          <Box
            ref={pannerRef}
            className="erd-svg-panner"
            sx={{
              position: "absolute",
              left: 0,
              top: 0,
              transformOrigin: "0 0",
              willChange: "transform",
              display: "block",
              "& svg": { display: "block", maxWidth: "none", height: "auto" },
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
            value={layout}
            onChange={(_, v: ErdGraphvizLayout | null) => {
              if (v !== null) setLayout(v);
            }}
            sx={{
              flexWrap: "wrap",
              gap: "1px",
              bgcolor: "transparent",
              "& .MuiToggleButtonGroup-grouped": {
                border: 0,
                borderRadius: "8px !important",
                mx: 0,
              },
              "& .MuiToggleButton-root": {
                px: 0.35,
                py: 0.25,
                minWidth: 30,
                fontSize: 15,
                lineHeight: 1,
                border: "none",
                bgcolor: "transparent",
                color: "#64748b",
                "&:hover": {
                  bgcolor: "rgba(15, 23, 42, 0.06)",
                  color: "#0f172a",
                },
                "&.Mui-selected": {
                  color: "#1d4ed8",
                  bgcolor: "transparent !important",
                },
                "&.Mui-selected:hover": {
                  bgcolor: "rgba(15, 23, 42, 0.06) !important",
                  color: "#1d4ed8",
                },
              },
            }}
          >
            {LAYOUT_TOOLS.map(({ value, title, Glyph }) => (
              <ToggleButton key={value} value={value} aria-label={title}>
                <Tooltip title={title} placement="top">
                  <Box
                    component="span"
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      width: "1em",
                      height: "1em",
                    }}
                  >
                    <Glyph />
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
          <OneHopToggle checked={includeOneHop} onChange={onIncludeOneHopChange} />
        </ZoomToolbar>
      </Box>
    </Box>
  );
}
