// src/components/diagrams/ErdViewer/parts/ErdGraphvizCanvas/ErdGraphvizCanvas.tsx
import type { Engine } from "@hpcc-js/wasm-graphviz";
import Box from "@mui/material/Box";
import Snackbar from "@mui/material/Snackbar";
import ToggleButton from "@mui/material/ToggleButton";
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import { useEffect, useLayoutEffect, useMemo, useRef, useState, type ReactElement, type SVGProps } from "react";
import { useSvgLayoutHash } from "@/lib/useSvgLayoutHash";
import { useSvgDiagramSurface } from "@/rooms/diagramSurface";
import { useGraphvizFocus } from "@/rooms/graphvizFocus";
import { enabledKeys } from "@/lib/freshGraph";
import { useCurrentPage, usePageSetting } from "@/lib/pageSettings";
import { ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { ErdFilterPanel, type ErdFilterRow } from "@/components/ui/ErdFilterPanel";
import { OneHopToggle } from "@/components/ui/OneHopToggle";
import { loadGraphvizWasmFor } from "../../hooks/useGraphviz";
import { useSvgPanZoom } from "../../hooks/useSvgPanZoom";
import {
  buildDotSource,
  ERD_CARD_RADIUS,
  ERD_CARD_STROKE,
  erdGraphvizEngine,
  type ErdEntity,
  type ErdGraphPayload,
  type ErdGroup,
  type ErdGraphvizLayout,
  type ErdRelation,
} from "@/lib/buildDotSource";
import { containNodeFills } from "@/lib/containNodeFills";
import { enrichErdDataForViewer } from "@/lib/enrichErdData";
import { filterGraphByKinds, pruneGraphToEntities } from "@/lib/erdKindFilter";
import { mergeRelationsOnScreen } from "@/lib/mergeErdRelations";
import type { ErdDomainsBundle } from "@/lib/loadErdDomainsBundle";
import { bindNameCopy } from "@/lib/erdCopy";
import { addEdgeHitAreas, bindLineHover, clearTableFocus, drawErdCards, focusTables, placeKindIcons } from "@/lib/erdPostPass";
import { postProcessGraphvizSvgDom } from "@/lib/sanitizeGraphvizSvgOverlays";
import { kindGlyphSvg, kindLegendDiskUri, svgDataUriForInterchangeDomainLegend } from "@/lib/icons";
import { diagramCanvasEmptyMessageSx } from "@/lib/ui";
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
  const groupsOut: ErdGroup[] = [];
  const seenGroups = new Set<string>();
  for (const part of parts) {
    for (const n of part.entities ?? []) nodeById.set(n.id, n);
    for (const e of part.relations ?? []) {
      const sig = edgeSig(e);
      if (seenRelations.has(sig)) continue;
      seenRelations.add(sig);
      relationsOut.push(e);
    }
    for (const g of part.groups ?? []) {
      if (seenGroups.has(g.group_id)) continue;
      seenGroups.add(g.group_id);
      groupsOut.push(g);
    }
  }
  return { entities: [...nodeById.values()], relations: relationsOut, groups: groupsOut };
}

function getMergedFromDomains(enriched: Record<string, unknown>, enabled: Set<string>): ErdGraphPayload {
  const domainsRaw = enriched.domains;
  if (!domainsRaw || typeof domainsRaw !== "object") {
    return { entities: [], relations: [] };
  }
  const domains = domainsRaw as Record<
    string,
    { entities?: ErdEntity[]; relations?: ErdRelation[]; groups?: ErdGroup[] }
  >;
  const keys = Object.keys(domains);
  if (!keys.length) return { entities: [], relations: [] };
  const on = keys.filter((k) => enabled.has(k));
  if (!on.length) return { entities: [], relations: [] };
  if (on.length === 1) {
    const slice = domains[on[0]!]!;
    return { entities: slice.entities ?? [], relations: slice.relations ?? [], groups: slice.groups ?? [] };
  }
  const merged = mergeDomainPayloads(
    on.map((k) => ({
      entities: domains[k]!.entities ?? [],
      relations: domains[k]!.relations ?? [],
      groups: domains[k]!.groups ?? [],
    })),
  );
  // A line whose ends came from two slices is only in the request-wide list.
  const requestRelations = Array.isArray(enriched.relations) ? (enriched.relations as ErdRelation[]) : undefined;
  const onScreen = new Set((merged.entities ?? []).map((e) => e.id));
  return { ...merged, relations: mergeRelationsOnScreen(requestRelations, merged.relations ?? [], onScreen) };
}

function readEntityQual(e: ErdEntity): string | null {
  const q = e.domain_qualname?.trim();
  if (q) return q;
  const raw = (e as unknown as Record<string, unknown>).domain_qualname;
  return typeof raw === "string" && raw.trim() ? raw.trim() : null;
}

function collectEntityQualifiers(entities: ErdEntity[] | undefined, fallbackQual: string | null): string[] {
  const s = new Set<string>();
  for (const e of entities ?? []) {
    const q = readEntityQual(e) ?? fallbackQual;
    if (q) s.add(q);
  }
  return [...s].sort();
}

function filterGraphByEntityQuals(
  data: ErdGraphPayload,
  enabled: Set<string>,
  fallbackQual: string | null,
): ErdGraphPayload {
  return pruneGraphToEntities(data, (e) => {
    const q = readEntityQual(e) ?? fallbackQual;
    return q != null && q !== "" && enabled.has(q);
  });
}

export type ErdGraphvizCanvasProps = {
  bundle: ErdDomainsBundle;
  /** Increments only when the async loader has accepted a new bundle. */
  bundleVersion: number;
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
  bundleVersion,
  includeOneHop,
  onIncludeOneHopChange,
}: ErdGraphvizCanvasProps) {
  // Page settings: the person's own outside a room, the room's inside one (spec 028, FR-030).
  const [layout, setLayout] = usePageSetting<ErdGraphvizLayout>("layout", "gv-dot-lr");
  const [svgMarkup, setSvgMarkup] = useState("");
  /** Graphviz's output before the post-passes; its hash fixes every node's position (FR-005, FR-090). */
  const [rawSvg, setRawSvg] = useState("");
  const layoutHashValue = useSvgLayoutHash(rawSvg);
  const [svgRenderVersion, setSvgRenderVersion] = useState(0);
  const [renderError, setRenderError] = useState<string | null>(null);
  const [gvBusy, setGvBusy] = useState(false);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);

  const enriched = useMemo(
    () => enrichErdDataForViewer(bundle as unknown as Record<string, unknown>),
    [bundle],
  );

  const domainKeyList = useMemo(() => {
    const d = enriched.domains as Record<string, unknown> | undefined;
    return d ? Object.keys(d).sort() : [];
  }, [enriched]);

  const multiTab = domainKeyList.length > 1;

  const bundleEntityTotal = useMemo(() => {
    const d = enriched.domains as Record<string, { entities?: ErdEntity[] }> | undefined;
    if (!d) return 0;
    let n = 0;
    for (const slice of Object.values(d)) {
      n += slice.entities?.length ?? 0;
    }
    return n;
  }, [enriched]);

  /** The domains switched on; ``null`` until someone chooses, which means all of them. */
  const [chosenDomains, setChosenDomains] = usePageSetting<string[] | null>("domains", null);
  /** Single-domain ERD: tables switched off, so a table 1-hop brings in later starts on. */
  const [disabledEntityList, setDisabledEntityList] = usePageSetting<string[]>("disabled_entities", []);
  /** Entity kinds switched off; a kind the graph gains later starts on. */
  const [disabledKindList, setDisabledKindList] = usePageSetting<string[]>("disabled_kinds", []);

  // A domain the model no longer has stops applying (spec 028, FR-076).
  const enabledDomains = useMemo(
    () => new Set(enabledKeys(Object.keys(bundle.domains ?? {}).sort(), chosenDomains)),
    [bundle, chosenDomains],
  );
  const disabledKinds = useMemo(() => new Set(disabledKindList), [disabledKindList]);

  const panZoom = useSvgPanZoom();
  const { viewportRef, pannerRef, zoomPct, fitToContainer, zoomIn, zoomOut, bindInteractions, resetFitFlag } = panZoom;
  useSvgDiagramSurface(viewportRef, panZoom, Boolean(svgMarkup) && panZoom.fitted);
  // Hover and tooltip shared with followers, and the followed person's shown here (spec 029).
  useGraphvizFocus(pannerRef.current, svgMarkup, useCurrentPage(), "table");


  const mergedByTabs = useMemo(
    () =>
      getMergedFromDomains(
        enriched,
        multiTab ? enabledDomains : new Set(domainKeyList),
      ),
    [enriched, multiTab, enabledDomains, domainKeyList],
  );

  const fallbackQual = useMemo(() => {
    if (multiTab || domainKeyList.length === 0) return null;
    const tab0 = domainKeyList[0]!;
    return bundle.domain_qualifiers[tab0]?.trim() || null;
  }, [multiTab, domainKeyList, bundle.domain_qualifiers]);

  const entityQualList = useMemo(
    () => collectEntityQualifiers(mergedByTabs.entities, fallbackQual),
    [mergedByTabs.entities, fallbackQual],
  );

  const enabledEntityQualifiers = useMemo(
    () => new Set(entityQualList.filter((q) => !disabledEntityList.includes(q))),
    [entityQualList, disabledEntityList],
  );

  const mergedData = useMemo(() => {
    // A table is on screen only when its domain (or qualifier) and its kind are both on.
    if (multiTab) return filterGraphByKinds(mergedByTabs, disabledKinds);
    if (enabledEntityQualifiers.size === 0) return { entities: [], relations: [] };
    return filterGraphByKinds(filterGraphByEntityQuals(mergedByTabs, enabledEntityQualifiers, fallbackQual), disabledKinds);
  }, [multiTab, mergedByTabs, enabledEntityQualifiers, fallbackQual, disabledKinds]);

  const erdEmptyOverlay =
    mergedData.entities.length === 0 ? (
      <Typography variant="body2" color="text.secondary" sx={diagramCanvasEmptyMessageSx}>
        {bundleEntityTotal === 0
          ? "No entities in this diagram."
          : "No entities for the selected domains."}
      </Typography>
    ) : null;

  // Each table carries its kind's display name for the header icon's tooltip.
  const drawnData = useMemo(() => {
    const labels = new Map((bundle.entity_kinds ?? []).map((row) => [row.entity_kind, row.label]));
    return {
      ...mergedData,
      entities: mergedData.entities.map((e) => ({ ...e, entity_kind_label: labels.get(e.entity_kind?.trim() || "unknown") })),
    };
  }, [mergedData, bundle.entity_kinds]);

  const dot = useMemo(() => buildDotSource(drawnData, layout), [drawnData, layout]);
  // The text Graphviz is given, hashed: the settings digest a room compares layouts under (FR-093).
  const layoutInputDigest = useSvgLayoutHash(rawSvg ? `${erdGraphvizEngine(layout)}\n${dot}` : "");

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
    setRawSvg("");
    const engine = erdGraphvizEngine(layout) as Engine;
    loadGraphvizWasmFor(engine)
      .then((gv) => {
        if (cancelled) return;
        const svg = gv.layout(dot, "svg", engine);
        if (cancelled) return;
        setRawSvg(svg);
        // The renderer paints a card's band and row tints as rectangles inside a rounded outline;
        // this trims every fill to the contour before the markup reaches the page.
        setSvgMarkup(placeKindIcons(drawErdCards(containNodeFills(svg), ERD_CARD_RADIUS, ERD_CARD_STROKE), drawnData.entities, kindGlyphSvg));
        setSvgRenderVersion((v) => v + 1);
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
  }, [dot, drawnData, layout, bundleVersion, resetFitFlag]);

  useLayoutEffect(() => {
    if (!svgMarkup) return;
    const panner = pannerRef.current;
    if (!panner) return;
    // The markup is placed here, not through ``dangerouslySetInnerHTML``: React re-applied that prop on
    // every render of the canvas (a zoom click is enough) and replaced the SVG, so the size, the table
    // hover and every listener bound below were lost on the drawing the user actually sees.
    panner.innerHTML = svgMarkup;

    const ac = new AbortController();
    const svg = panner.querySelector("svg");
    if (svg instanceof SVGSVGElement) {
      // Keep Graphviz as a real-size SVG canvas. If width/height are just removed,
      // browsers can fall back to a 300x150 SVG viewport and zoom math collapses.
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
      addEdgeHitAreas(svg);
      bindLineHover(svg, drawnData.relations, drawnData.entities, ac.signal);
    }
    bindNameCopy(panner, setCopyMessage, ac.signal);

    const onEnter = (evt: Event) => {
      const el = evt.currentTarget as Element;
      focusTables(panner, new Set([el.querySelector("title")?.textContent?.trim() || ""]));
    };
    const onLeave = () => clearTableFocus(panner);

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
  }, [svgMarkup, svgRenderVersion, fitToContainer, bindInteractions, drawnData]);

  const tabAccents = (enriched.domain_accent_colors ?? {}) as Record<string, string>;

  const qualAccents = useMemo(() => {
    const out: Record<string, string> = {};
    const palette = bundle.domain_qualifier_colors;
    for (const q of entityQualList) {
      // A domain the palette does not list takes the first domain hue, never grey (grey is the kinds').
      out[q] = palette[q] ?? "#3b82f6";
    }
    return out;
  }, [entityQualList, bundle.domain_qualifier_colors]);

  const qualRowLabels = useMemo(() => {
    const byQual = bundle.domain_qualifier_labels ?? {};
    const out: Record<string, string> = {};
    for (const q of entityQualList) {
      const lbl = byQual[q]?.trim();
      if (lbl) out[q] = lbl;
    }
    return Object.keys(out).length > 0 ? out : undefined;
  }, [entityQualList, bundle.domain_qualifier_labels]);

  // Each change is sent as the whole new set, never as a toggle (FR-031).
  const toggleDomain = (key: string) => {
    const next = new Set(enabledDomains);
    if (next.has(key)) next.delete(key);
    else next.add(key);
    setChosenDomains([...next].sort());
  };

  const toggleKind = (kind: string) => {
    const next = new Set(disabledKinds);
    if (next.has(kind)) next.delete(kind);
    else next.add(kind);
    setDisabledKindList([...next].sort());
  };

  const domainRows: ErdFilterRow[] = multiTab
    ? domainKeyList.map((key) => ({
        key,
        label: bundle.domain_tab_labels?.[key] ?? key,
        iconSrc: svgDataUriForInterchangeDomainLegend(tabAccents[key] || "#3b82f6"),
        on: enabledDomains.has(key),
      }))
    : entityQualList.map((qual) => ({
        key: qual,
        label: qualRowLabels?.[qual] ?? qual,
        iconSrc: svgDataUriForInterchangeDomainLegend(qualAccents[qual] || "#3b82f6"),
        on: enabledEntityQualifiers.has(qual),
      }));

  const kindRows: ErdFilterRow[] = (bundle.entity_kinds ?? []).map((row) => ({
    key: row.entity_kind,
    label: row.label,
    iconSrc: kindLegendDiskUri(row.entity_kind),
    on: !disabledKinds.has(row.entity_kind),
  }));

  const toggleEntityQual = (qual: string) => {
    const next = new Set(disabledEntityList);
    if (next.has(qual)) next.delete(qual);
    else next.add(qual);
    setDisabledEntityList([...next].sort());
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
        {domainRows.length > 0 && (
          <ErdFilterPanel
            domainRows={domainRows}
            kindRows={kindRows}
            onToggleDomain={multiTab ? toggleDomain : toggleEntityQual}
            onToggleKind={toggleKind}
          />
        )}
        {erdEmptyOverlay}
        <Snackbar
          open={copyMessage !== null}
          message={copyMessage ?? ""}
          autoHideDuration={1500}
          onClose={() => setCopyMessage(null)}
          anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
          sx={{ position: "absolute", bottom: "64px !important" }}
        />

        <Box
          ref={viewportRef}
          data-layout-hash={layoutHashValue}
          data-layout-input={layoutInputDigest}
          className="erd-svg-viewport"
          sx={{
            position: "absolute",
            inset: 0,
            overflow: "hidden",
            cursor: "grab",
            touchAction: "none",
            zIndex: 1,
            "&.erd-panning": { cursor: "grabbing" },
            "&.erd-wheel-zooming .erd-svg-panner": { pointerEvents: "none" },
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
              display: "block",
              // A hovered line (or every line of a hovered row): thicker, darker, ends and roles following.
              "& g.edge path": { transition: "stroke-width 100ms ease, stroke 100ms ease" },
              "& g.edge.is-hovered path:not(.erd-hit)": { stroke: "#475569", strokeWidth: 2.4 },
              "& g.edge.is-hovered polygon": { stroke: "#475569" },
              "& g.edge.is-hovered polygon:not([fill='none'])": { fill: "#475569" },
              "& g.edge.is-hovered text": { fill: "#334155", fontWeight: 700 },
              "@media (prefers-reduced-motion: reduce)": { "& g.edge path": { transition: "none" } },
              // Names copy on click.
              "& g[id^='a_hn'] text, & g[id^='a_fn'] text": { cursor: "copy" },
              "& svg": {
                display: "block",
                maxWidth: "none",
                width: "auto",
                height: "auto",
                overflow: "visible",
                transformOrigin: "0 0",
              },
            }}
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
