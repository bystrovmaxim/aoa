// src/components/diagrams/MapViewer/MapViewer.tsx
import Box from "@mui/material/Box";
import ButtonBase from "@mui/material/ButtonBase";
import Typography from "@mui/material/Typography";
import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from "react";
import { DiagramShell, useDiagramLoader } from "@/components/diagrams/DiagramShell";
import { ErdFilterPanel } from "@/components/ui/ErdFilterPanel";
import { HoverCardsButton, ZoomToolbar } from "@/components/ui/ZoomToolbar";
import { ElementCard, type CardSubject } from "@/components/diagrams/ElementCard";
import { DiffCard } from "@/components/history/DiffCard";
import { getActiveBase } from "@/api/client";
import { mapChanges, mapOverview, type MapChange, type MapOverview } from "@/api/map";
import { setChangeStepping, type ChangeEntry } from "@/lib/changeStepping";
import { setDiffCounts, useDiffNames } from "@/lib/diffCounts";
import { HalfNote } from "@/components/diagrams/SideBySide";
import { drawnOn, useHalf, writesForPair, type Half } from "@/lib/half";
import { joinSteps, noteOf, stepBoth } from "@/lib/halfPicking";
import { defaultPaint, paintSettingName, paintSource, type PaintSection } from "@/lib/erdPaint";
import { layoutHash } from "@/lib/layoutHash";
import { countChanges } from "@/lib/mapDiff";
import { mapFilterRows } from "@/lib/mapFilterRows";
import { changesLeft, mapFacts, presence, type HiddenBy, type MapFilters } from "@/lib/mapVisibility";
import { usePageSetting } from "@/lib/pageSettings";
import { useHoverCard } from "@/lib/useHoverCard";
import { isFollowing, mirroredFocus, sameRef, useMirroredFocus, type ElementRef } from "@/rooms/focusStore";
import type { MapCard, MapEngine } from "./mapEngine";

const LAYERS_SX = { position: "absolute", inset: 0, width: "100%", height: "100%" } as const;

/** Whether this browser can draw the map. */
function canDrawMap(): boolean {
  const canvas = document.createElement("canvas");
  return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
}

/** Switch a key of a list of what is off. */
function toggled(list: readonly string[], key: string): string[] {
  return list.includes(key) ? list.filter((each) => each !== key) : [...list, key].sort();
}

/** The pair's changes for what is on screen. A half reads its own version's map, so it first asks for the pair's, which the changes are read from (spec 044). */
async function changesFor(half: Half | null, overview: MapOverview, onLayingOut: () => void): Promise<MapChange[]> {
  if (!half) return overview.links_changed === undefined ? [] : mapChanges();
  await mapOverview(onLayingOut);
  return mapChanges();
}

/**
 * The full graph as a map (spec 040): named domains far away, what they hold closer. The overview comes first; Sigma
 * is loaded with it, so that no other diagram carries its weight. The filters and the paint are page settings, as on
 * the ERD: a room shares them and the address carries them, and applying them moves nothing. A browser that cannot draw
 * the map says so and offers the ERD (FR-036).
 */
export function MapViewer({ onOpenErd }: { onOpenErd?: () => void }) {
  const stageRef = useRef<HTMLDivElement | null>(null);
  const sigmaRef = useRef<HTMLDivElement | null>(null);
  const underRef = useRef<HTMLCanvasElement | null>(null);
  const overRef = useRef<HTMLCanvasElement | null>(null);
  const labelRef = useRef<HTMLDivElement | null>(null);
  const [engine, setEngine] = useState<MapEngine | null>(null);
  const [layingOut, setLayingOut] = useState(false);
  const [zoomPct, setZoomPct] = useState(100);
  const [mapError, setMapError] = useState<string | null>(null);
  const [card, setCard] = useState<MapCard | null>(null);
  // A click on a change opens its card as before (spec 043, FR-012a); a hover opens the one card, none while that one stands.
  const hoverCard = useHoverCard<CardSubject>(card !== null);
  const hoverRef = useRef(hoverCard.want);
  hoverRef.current = hoverCard.want;
  const hoverNowRef = useRef(hoverCard.wantNow);
  hoverNowRef.current = hoverCard.wantNow;
  // The followed person's card goes by what they say of it, not by their hover: on the card they hover nothing.
  const followed = useMirroredFocus();
  const followedCard = followed?.panels.card?.ref ?? null;
  const shownCard = useRef<ElementRef | null>(null);
  useEffect(() => {
    if (!followed || !engine || sameRef(followedCard, shownCard.current)) return;
    shownCard.current = followedCard;
    const subject = followedCard ? engine.cardSubject(followedCard) : null;
    if (subject) hoverCard.wantNow(subject);
    else hoverCard.close();
  }, [engine, followed, followedCard, hoverCard]);
  const closeRef = useRef(hoverCard.close);
  closeRef.current = hoverCard.close;
  /** A press is a drag on its way: what passes under the pointer then is not being looked at. */
  const pressedRef = useRef(false);
  useEffect(() => {
    const release = () => void (pressedRef.current = false);
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
    return () => {
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
    };
  }, []);
  const [position, setPosition] = useState<number | null>(null);
  const [drawable] = useState(canDrawMap);
  const names = useDiffNames();
  const diffing = getActiveBase() !== null;
  const half = useHalf();
  const [offTypes, setOffTypes] = usePageSetting<string[]>("disabled_node_types", []);
  const [offDomains, setOffDomains] = usePageSetting<string[]>("disabled_domains", []);
  const [offChanges, setOffChanges] = usePageSetting<string[]>("disabled_changes", []);
  const [chosenPaint, setChosenPaint] = usePageSetting<PaintSection>(paintSettingName(diffing), defaultPaint(diffing));

  const load = useCallback(async () => {
    const [overview, module] = await Promise.all([mapOverview(() => setLayingOut(true), half?.read), import("./mapEngine")]);
    return { overview, module, changes: await changesFor(half, overview, () => setLayingOut(true)) };
  }, [half]);
  const { data, loading, error } = useDiagramLoader(load);

  const filters = useMemo<MapFilters>(() => ({ types: new Set(offTypes), domains: new Set(offDomains), changes: new Set(offChanges) }), [offTypes, offDomains, offChanges]);
  const facts = useMemo(() => (data ? mapFacts(data.overview) : null), [data]);
  const shownChanges = useMemo(() => (data && facts ? changesLeft(data.changes, filters, facts) : []), [data, facts, filters]);
  const entries = useMemo<ChangeEntry[]>(() => {
    const areaNames = new Map(data?.overview.areas.map((area) => [area.id, area.name]));
    return shownChanges.map((change) => ({ key: change.id, title: change.label, detail: change.type, status: change.status, group: areaNames.get(change.area) ?? change.area }));
  }, [data, shownChanges]);
  const entriesRef = useRef(entries);
  entriesRef.current = entries;
  const sections: PaintSection[] = ["domains", ...((data?.overview.types.length ?? 0) > 1 ? (["kinds"] as const) : []), ...(data?.changes.length ? (["changes"] as const) : [])];
  const paint = paintSource(sections, chosenPaint);
  const comparing = data !== null && data !== undefined && (half !== null || data.overview.links_changed !== undefined);
  // A half's map marks and steps through what its version has; the counts and the list stay the pair's (spec 044).
  const ownChanges = useMemo(() => (half ? shownChanges.filter((change) => drawnOn(half.side, change.status)) : shownChanges), [half, shownChanges]);

  useEffect(() => {
    const [stage, sigma, under, over, label] = [stageRef.current, sigmaRef.current, underRef.current, overRef.current, labelRef.current];
    if (!data || !drawable || !stage || !sigma || !under || !over || !label) return undefined;
    setLayingOut(false);
    let gone = false;
    let made: MapEngine | null = null;
    const { overview, module, changes } = data;
    const events = {
      onZoom: (zoom: number) => {
        setZoomPct(Math.round(zoom * 100));
        // A follower's card stays as long as the followed person holds it, and goes with the map.
        const ref = isFollowing() ? mirroredFocus()?.panels.card?.ref : null;
        const subject = ref ? made?.cardSubject(ref) : null;
        if (subject) hoverNowRef.current(subject);
        else closeRef.current();
      },
      onCard: setCard,
      onPick: half ? (node: string | null) => pickRef.current(node ? { kind: "node", id: node } : null) : undefined,
      onStep: setPosition,
      onHoverElement: (subject: CardSubject | null, now?: boolean) => {
        if (subject && now) hoverNowRef.current(subject);
        else if (!pressedRef.current) hoverRef.current(subject);
      },
    };
    module.MapEngine.create(overview, changes, { stage, sigma, under, over, label }, events, half)
      .then(async (engineMade) => {
        if (gone) {
          engineMade.destroy();
          return;
        }
        made = engineMade;
        setEngine(engineMade);
        const positions = Object.fromEntries(overview.areas.map((area) => [area.id, [area.x, area.y] as [number, number]]));
        stage.setAttribute("data-layout-hash", await layoutHash(positions, overview.areas.map((area) => area.id)));
      })
      .catch((reason: unknown) => setMapError(String(reason)));
    return () => {
      gone = true;
      stage.removeAttribute("data-layout-hash");
      made?.destroy();
      setEngine(null);
    };
  }, [data, drawable]);

  // A filter or a paint changes what is drawn, and moves nothing (FR-028).
  useEffect(() => engine?.setView({ filters, paint, changes: ownChanges }), [engine, filters, paint, ownChanges]);

  // One element across the two halves: selected in both, brought into view here, or said why not (spec 044).
  const [selected, setSelected] = usePageSetting<ElementRef | null>("selected", null);
  const pickRef = useRef(setSelected);
  pickRef.current = setSelected;
  const [note, setNote] = useState<string | null>(null);
  useEffect(() => {
    if (!engine || !half) return undefined;
    let gone = false;
    void engine.locate(selected?.kind === "node" ? selected.id : null).then((located) => {
      if (!gone) setNote(noteOf(located, half.name));
    });
    return () => {
      gone = true;
    };
  }, [engine, half, selected]);
  useEffect(() => {
    if (!half) return undefined;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") pickRef.current(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [half]);
  useEffect(() => (engine && half ? joinSteps(half.side, (index) => engine.goToChange(entriesRef.current[index]?.key ?? "")) : undefined), [engine, half]);

  useEffect(() => {
    if (writesForPair(half)) setDiffCounts(comparing ? countChanges(shownChanges) : null);
  }, [comparing, shownChanges]);

  useEffect(() => {
    if (writesForPair(half)) setChangeStepping(engine && entries.length ? { entries, position, card: card !== null, go: half ? stepBoth : (next) => engine.goTo(next), mirror: (next, open) => engine.mirror(next, open) } : null);
  }, [engine, entries, position, card]);

  useEffect(
    () => () => {
      if (!writesForPair(half)) return;
      setDiffCounts(null);
      setChangeStepping(null);
    },
    [],
  );

  const reveal = useCallback(
    (reasons: readonly HiddenBy[]) => {
      const keysOf = (section: HiddenBy["section"]) => new Set(reasons.filter((reason) => reason.section === section).map((reason) => reason.key));
      const [types, domains, changes] = [keysOf("types"), keysOf("domains"), keysOf("changes")];
      if (types.size) setOffTypes(offTypes.filter((key) => !types.has(key)));
      if (domains.size) setOffDomains(offDomains.filter((key) => !domains.has(key)));
      if (changes.size) setOffChanges(offChanges.filter((key) => !changes.has(key)));
    },
    [offTypes, offDomains, offChanges, setOffTypes, setOffDomains, setOffChanges],
  );
  // The picture answers a click first; the panel's rows follow in the next moment.
  const rowFilters = useDeferredValue(filters);
  const rows = useMemo(() => (data && facts ? mapFilterRows(data.overview, rowFilters, presence(data.overview, rowFilters, facts), paint, comparing, reveal) : null), [data, facts, rowFilters, paint, comparing, reveal]);

  return (
    <DiagramShell loading={loading && !layingOut} error={error ?? mapError}>
      <Box
        ref={stageRef}
        className="ix-interchange-viewport"
        onWheelCapture={hoverCard.close}
        onPointerDownCapture={(event) => {
          if (event.target instanceof Element && event.target.closest('[data-testid="element-card"]')) return;
          pressedRef.current = true;
          hoverCard.close();
        }}
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
        {!card && hoverCard.shown && (
          <ElementCard
            key={hoverCard.shown.key}
            subject={hoverCard.shown}
            newer={names?.b ?? "B"}
            onEnter={hoverCard.hold}
            onLeave={hoverCard.release}
            onClose={hoverCard.close}
          />
        )}
        {!drawable && (
          <Box role="alert" sx={{ position: "absolute", zIndex: 12, left: "50%", top: "42%", transform: "translateX(-50%)", display: "flex", flexDirection: "column", alignItems: "center", gap: 1.5, maxWidth: 340, textAlign: "center" }}>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              This browser cannot draw the map: WebGL is off.
            </Typography>
            {onOpenErd && (
              <ButtonBase onClick={onOpenErd} sx={{ height: 28, px: 1.5, borderRadius: "8px", fontSize: 12.5, fontWeight: 600, color: "#0f172a", bgcolor: "rgba(15, 23, 42, 0.05)", "&:hover": { bgcolor: "rgba(15, 23, 42, 0.1)" } }}>
                Open the ERD
              </ButtonBase>
            )}
          </Box>
        )}
        <HalfNote text={note} />
        {rows && drawable && half?.side !== "b" && (
          <ErdFilterPanel
            domainRows={rows.domainRows}
            kindRows={rows.typeRows}
            kindsTitle="Node types"
            onToggleDomain={(key) => setOffDomains(toggled(offDomains, key))}
            onToggleKind={(key) => setOffTypes(toggled(offTypes, key))}
            changeRows={rows.changeRows}
            onToggleChange={(key) => setOffChanges(toggled(offChanges, key))}
            paint={{ source: paint, onPaint: setChosenPaint }}
          />
        )}
        <ZoomToolbar zoomPct={zoomPct} onZoomIn={() => engine?.zoomBy(1.5)} onZoomOut={() => engine?.zoomBy(1 / 1.5)} onFit={() => engine?.fit()}>
          <HoverCardsButton />
        </ZoomToolbar>
      </Box>
    </DiagramShell>
  );
}
