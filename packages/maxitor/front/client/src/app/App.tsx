// src/app/App.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { DiagramWorkspacePage } from "@/components/pages/DiagramWorkspacePage";
import { LeftSidebar } from "@/components/navigation/LeftSidebar";
import { useSidebarPayload } from "@/components/navigation/LeftSidebar/hooks/useSidebarPayload";
import type { DiagramSelection } from "@/model/diagramSelection";
import type { SidebarPayload } from "@/model/sidebar";
import Box from "@mui/material/Box";
import { useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import { GraphReadError, onGraphBusy, setActiveBase, setActiveHistoryKey, setActiveSource } from "@/api/client";
import { setDiffNames, useDiffCounts } from "@/lib/diffCounts";
import { HistoryRequestError, historyVersions, openHistory, type OpenedHistory } from "@/api/history";
import { VersionButton } from "@/components/history/VersionButton";
import { VersionMessage } from "@/components/history/VersionMessage";
import { VersionPicker } from "@/components/history/VersionPicker";
import { VersionsBetween } from "@/components/history/VersionsBetween";
import { keyFor } from "@/lib/historyKey";
import { liveLine } from "@/lib/liveLine";
import { shortNameOf, shownNameOf } from "@/lib/versionNames";
import { hasPicker } from "@/model/historyMode";
import { keysOf, sourceOf, useOpenHistory, versionOf } from "./useOpenHistory";
import { diffOffered, oneToDiff, stepShown, type Range } from "@/lib/versionRange";
import { stepOfKey } from "@/lib/stepKeys";
import type { PickerMode } from "@/components/history/VersionPicker";
import { loadGraph } from "@/api/load";
import { getGraphFingerprint } from "@/api/graphFingerprint";
import { useFingerprintPoll, useModelRefresh } from "@/lib/freshGraph";
import { pushServiceUrl } from "@/lib/serviceUrlHistory";
import { firstSelectionOfKind } from "@/lib/sidebarNavigation";
import {
  deepLinkNeedsSidebarDefault,
  deepLinkToSelection,
  pushUrlState,
  readUrlDeepLink,
  setUrlHistory,
  setUrlRoom,
  syncUrlToState,
  readUrlParams,
  setUrlView,
  type UrlDeepLink,
} from "@/lib/urlState";
import { PageSettingsProvider, seedPageSettings, shownPageSettings, usePageSettingsVersion, type RoomSettings } from "@/lib/pageSettings";
import { presetPaint, useErdPaint } from "@/lib/erdPaint";
import { cameraToParams, paramsToCamera, paramsToView, viewToParams } from "@/lib/viewUrl";
import type { SavedView } from "@/rooms/diagramSurface";
import { NameDialog } from "@/rooms/NameDialog";
import { PointerLayer } from "@/rooms/PointerLayer";
import { useDiagramSurface } from "@/rooms/diagramSurface";
import { usePointerSender } from "@/rooms/usePointerSender";
import { useGoTo } from "@/rooms/goTo";
import { useFollow } from "@/rooms/follow";
import { FollowFrame } from "@/rooms/FollowFrame";
import { LeaveForServiceDialog, RoomBanner, RoomBar } from "@/rooms/RoomBar";
import { pageKeyOf, pageLabel, selectionOfPageKey } from "@/rooms/pageKey";
import { lastName, useRoomSession } from "@/rooms/useRoomSession";

/** How long a pan or zoom must rest before the address takes it: the address does not chase every frame. */
const CAMERA_SETTLE_MS = 250;

export function App() {
  const [diagram, setDiagram] = useState<DiagramSelection | null>(null);
  const [serviceUrl, setServiceUrl] = useState<string | null>(null);
  const [reloading, setReloading] = useState(false);
  const [reloadError, setReloadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [workspaceKey, setWorkspaceKey] = useState(0);
  const { sidebar, reload, reset } = useSidebarPayload();
  const pendingKind = useRef<ReturnType<typeof deepLinkNeedsSidebarDefault>>(null);

  // Captured once on the first render — reading window.location.search fresh inside the
  // mount effect below is unsafe: the URL-sync effect further down rewrites the URL as soon
  // as it runs, so a second read (e.g. React StrictMode's dev-only double-invoke of mount
  // effects) would see an already-rewritten URL and silently drop the deep link.
  const initialLinkRef = useRef<UrlDeepLink | undefined>(undefined);
  /** The zoom and centre the address opened with, placed on the first diagram drawn, then forgotten. */
  const openingCamera = useRef<SavedView | null>(null);
  if (!initialLinkRef.current) {
    initialLinkRef.current = readUrlDeepLink();
    // The source must be known before the page's first read: the read below goes out with it.
    setActiveSource(initialLinkRef.current.source ?? null);
    // A room link keeps ``room`` in the address while its name dialog is open.
    setUrlRoom(initialLinkRef.current.room ?? null);
    // The view the address names — filters, layout, modes, paint — is the page's own from the first render (spec 038).
    const view = paramsToView(readUrlParams());
    openingCamera.current = paramsToCamera(readUrlParams());
    const opening = deepLinkToSelection(initialLinkRef.current);
    if (opening) seedPageSettings(pageKeyOf(opening), view.settings);
    if (view.paint) presetPaint(Boolean(initialLinkRef.current.a), view.paint);
  }

  const page = diagram ? pageKeyOf(diagram) : null;
  const [askLeaveForService, setAskLeaveForService] = useState(false);
  // A history (spec 037): polled outside a room only — inside one, the room says when it changed.
  const [roomOpen, setRoomOpen] = useState(false);
  const opened = useOpenHistory(!roomOpen);
  const shown = opened.history;
  const shownSource = shown ? sourceOf(shown) : null;
  const shownVersion = shown ? versionOf(shown, shown.b) : null;
  const shownName = shown ? shownNameOf(shown.versions, shown.b, shown.proposals) : null;
  // In Diff (spec 038) the tab compares A with B; the diagram shows B until the comparison draws both.
  const olderName = shown?.a ? shownNameOf(shown.versions, shown.a, shown.proposals) : null;
  const trackPoints = shown ? keysOf(shown) : [];
  const pickerMode: PickerMode = shown?.a ? "diff" : "one";
  const olderVersion = shown?.a ? versionOf(shown, shown.a) : null;
  const diffCounts = useDiffCounts();
  // The picker opens under the version button there is now: the button may be drawn anew while it is open.
  const [pickerOpen, setPickerOpen] = useState(false);
  const versionButton = useRef<HTMLButtonElement | null>(null);
  // On a phone the picker is a sheet from the bottom (FR-031), at the width MainLayout calls a phone.
  const phone = useMediaQuery(useTheme().breakpoints.down("sm"));
  /** When Live was last read, or since when it cannot be: its closing line under the track (FR-030). */
  const [liveState, setLiveState] = useState<{ ok: boolean; at: number } | null>(null);

  /** The server opened this tab on a page other than its link's: go there, without a history entry. */
  const handleFallbackPage = useCallback(
    (key: string) => {
      const selection = selectionOfPageKey(key);
      if (!selection) return;
      pushUrlState(serviceUrl, selection, { replace: true });
      setDiagram(selection);
    },
    [serviceUrl],
  );

  const surface = useDiagramSurface();
  const rereadSidebar = useCallback(() => void reload().catch(() => undefined), [reload]);
  const redraw = useCallback(() => setWorkspaceKey((count) => count + 1), []);
  /**
   * The model changed — the room said so, or the fingerprint poll found it: read the left panel and the
   * diagram again in place, keeping page, settings, layout mode, zoom and centre (spec 028, FR-076).
   */
  const model = useModelRefresh({ surface, rereadSidebar, redraw });
  const handleGraphChanged = model.refresh;
  const room = useRoomSession({
    initialRoom: initialLinkRef.current.room,
    source: serviceUrl,
    page,
    onFallbackPage: handleFallbackPage,
    onGraphChanged: handleGraphChanged,
    surface,
    fingerprint: sidebar?.fingerprint ?? null,
    history: shown ? { name: shown.name, version: shown.b, versionA: shown.a, key: shown.key } : null,
    onVersion: (b, a) => (a ? opened.pickRange({ a, b }) : opened.pick(b)),
    onHistoryChanged: () => {
      if (!shown) return;
      void historyVersions(shown.name, shown.key)
        .then((answer) => answer && opened.takeList(answer.versions, answer.live, answer.etag, { liveSameAs: answer.live_same_as, proposals: answer.proposals }))
        .catch(() => undefined);
    },
  });
  // Pointers go out and come in only while connected and while this page's layout is the room's
  // (FR-045, FR-093); Hide pointers only stops drawing other people's.
  // Outside a room a tab asks every 30 s whether its graph changed; inside one the room tells it.
  useFingerprintPoll(!room.inRoom && serviceUrl !== null && sidebar !== null, getGraphFingerprint, sidebar?.fingerprint ?? null, handleGraphChanged);
  useEffect(() => setRoomOpen(room.inRoom), [room.inRoom]);
  const pointersLive = room.inRoom && room.connection?.kind === "open" && !room.pointersOff;
  usePointerSender(surface, room.send, pointersLive);
  const roomSettings = room.room?.settings;
  const { setPageSetting } = room;
  const sharedSettings = useMemo<RoomSettings | null>(
    () => (roomSettings ? { settings: roomSettings, set: setPageSetting } : null),
    [roomSettings, setPageSetting],
  );

  // The address always carries the view on screen — the room's inside one —, so a reload or a copied link shows it.
  const settingsVersion = usePageSettingsVersion();
  const paint = useErdPaint();
  const paintChoice = diagram?.kind === "erd" ? (shown?.a ? paint.inDiff : paint.one) : null;
  // Where the diagram is looked at, too: every pan and zoom, a moment after it settles.
  // Until the first diagram is drawn the address keeps the view it opened with, so a second reload loses nothing.
  const [camera, setCamera] = useState<SavedView | null>(() => openingCamera.current);
  useEffect(() => {
    if (!surface) return undefined;
    if (openingCamera.current) {
      surface.restore(openingCamera.current);
      openingCamera.current = null;
    }
    let timer: ReturnType<typeof setTimeout> | undefined;
    const note = () => {
      clearTimeout(timer);
      timer = setTimeout(() => setCamera(surface.view()), CAMERA_SETTLE_MS);
    };
    note();
    const stop = surface.subscribe(note);
    return () => {
      clearTimeout(timer);
      stop();
    };
  }, [surface]);
  useEffect(() => {
    setUrlView(page ? { ...viewToParams(shownPageSettings(page, sharedSettings), paintChoice), ...cameraToParams(camera) } : {});
  }, [page, settingsVersion, sharedSettings, paintChoice, camera]);
  /**
   * Going to someone opens their page like any navigation: the left panel and the address follow.
   * Following replaces the history entry instead, so Back is not flooded (FR-057).
   */
  const navigateToPage = useCallback(
    (key: string, options: { replace: boolean } = { replace: false }) => {
      const selection = selectionOfPageKey(key);
      if (!selection) return;
      pushUrlState(serviceUrl, selection, options);
      setDiagram(selection);
    },
    [serviceUrl],
  );
  const goTo = useGoTo({ surface, page, navigate: navigateToPage });
  const { following, follow, stop: stopFollowing } = useFollow({
    room: room.room,
    send: room.send,
    surface,
    page,
    navigate: navigateToPage,
  });
  const followingRef = useRef(following);
  followingRef.current = following;
  /** Your own navigation stops following (FR-051). */
  const stopFollowingOnOwnMove = () => {
    if (followingRef.current) stopFollowing();
  };
  const pointerPeople = room.room
    ? room.room.participants.filter((p) => p.id !== room.room?.youId && p.page === page && !p.away)
    : [];
  const labelOfPage = (key: string | null) => pageLabel(key, sidebar);

  // A busy server means "retrying", not "your source is wrong": the page says so and waits.
  useEffect(() => onGraphBusy(() => setBusy(true)), []);

  /** Read the sidebar of ``source``; a refused source falls back to the manual prompt, or, for a history's Live, says so. */
  async function readSidebar(source: string, inHistory = false) {
    try {
      await reload();
      if (!inHistory) pushServiceUrl(source);
      if (inHistory && source === shown?.live) setLiveState({ ok: true, at: Date.now() });
      setBusy(false);
    } catch (e) {
      if (inHistory) {
        if (source === shown?.live) setLiveState((current) => (current && !current.ok ? current : { ok: false, at: Date.now() }));
        // Live that cannot be reached leaves the history open: another version can still be picked (FR-021).
        opened.setNotice("Live cannot be reached; pick a version");
        return;
      }
      if (e instanceof GraphReadError && e.status === 422) {
        setActiveSource(null);
        setServiceUrl(null);
        reset();
      }
    }
  }

  /** Open the history an address names, with the key this tab or Recent holds; a refusal is a notice. */
  async function openHistoryOf(name: string, b: string | null, a: string | null = null) {
    const key = keyFor(name);
    try {
      opened.show(await openHistory(name, key), key, b, a);
    } catch (e) {
      setUrlHistory(null);
      opened.close();
      setReloadError(e instanceof HistoryRequestError ? e.message : String(e));
    }
  }

  /** Applies a service+view combination read from the URL — initial load or a popstate. */
  function applyDeepLink(link: UrlDeepLink, activeServiceUrl: string | null, activeSidebar: SidebarPayload | null) {
    if (link.history) {
      // Named at once, so the address keeps ``history`` and ``b`` while the history is still being opened.
      setUrlHistory({ name: link.history, b: link.b ?? null, a: link.a ?? null });
      const resolvedHistory = deepLinkToSelection(link);
      if (resolvedHistory) setDiagram(resolvedHistory);
      if (link.history !== shown?.name) void openHistoryOf(link.history, link.b ?? null, link.a ?? null);
      else if (link.a && link.b && (link.a !== shown.a || link.b !== shown.b)) opened.pickRange({ a: link.a, b: link.b });
      else if (link.b && (link.b !== shown.b || (!link.a && shown.a))) opened.pick(link.b);
      return;
    }
    setUrlHistory(null);
    opened.close();
    const resolved = deepLinkToSelection(link);
    if (resolved) {
      pendingKind.current = null;
      setDiagram(resolved);
    } else {
      const kind = deepLinkNeedsSidebarDefault(link);
      const fallback = kind && activeSidebar ? firstSelectionOfKind(activeSidebar, kind) : null;
      pendingKind.current = fallback ? null : kind;
      setDiagram(fallback);
    }

    if (link.source && link.source !== activeServiceUrl) {
      const source = link.source;
      setActiveSource(source);
      setServiceUrl(source);
      // A deep link only reads: the source is built by the read itself, not by POST /api/load.
      void readSidebar(source);
    } else if (!link.source) {
      setActiveSource(null);
      setServiceUrl(null);
      reset();
    }
  }

  // Honor a deep link on first load: ?source=<service-url>&view=<slug>[&domain=|&node=|&host=].
  useEffect(() => {
    applyDeepLink(initialLinkRef.current!, null, null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reload]);

  // Resolve a use-case/lifecycle-fsm deep link that named a kind but no qualifier, once the sidebar arrives.
  useEffect(() => {
    if (!sidebar || !pendingKind.current) return;
    const resolved = firstSelectionOfKind(sidebar, pendingKind.current);
    pendingKind.current = null;
    if (resolved) setDiagram(resolved);
  }, [sidebar]);

  // Back/forward — the browser already changed the URL for us; mirror it into state.
  useEffect(() => {
    function handlePopState() {
      stopFollowingOnOwnMove();
      applyDeepLink(readUrlDeepLink(), serviceUrl, sidebar);
    }
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [serviceUrl, sidebar]);

  // A history's chosen version is what the page reads: its source, its key, and the address that names it.
  useEffect(() => {
    if (!shown) return;
    setUrlHistory({ name: shown.name, b: shown.b, a: shown.a });
    setActiveHistoryKey(shown.b === "live" ? "" : shown.key);
    if (shownSource && shownSource !== serviceUrl) {
      setActiveSource(shownSource);
      setServiceUrl(shownSource);
      void readSidebar(shownSource, true);
      // Another version is another graph: the diagram on screen is read again from it, page kept.
      setWorkspaceKey((count) => count + 1);
    } else if (!shownSource) {
      setActiveSource(null);
      setServiceUrl(null);
      reset();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shown?.name, shown?.b, shownSource]);

  // The address follows A as well: it names the two compared (spec 038, FR-014). The diagrams read A beside B, with
  // the history's key — B may be Live, which needs none —, and the diagram on screen is drawn again from both.
  useEffect(() => {
    if (shown) setUrlHistory({ name: shown.name, b: shown.b, a: shown.a });
    syncUrlToState(serviceUrl, diagram);
    setActiveBase(olderVersion && !olderVersion.refused ? { source: olderVersion.source, key: shown?.key ?? "" } : null);
    if (shown) {
      setWorkspaceKey((count) => count + 1);
      // The left panel lists A's pages beside B's in Diff, B's alone in One.
      rereadSidebar();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shown?.a, olderVersion?.source]);

  // A changed element's card says what it was added or removed in: the two versions' names.
  useEffect(() => setDiffNames(shown?.a ? { a: olderName ?? "A", b: shownName ?? "B" } : null), [shown?.a, olderName, shownName]);

  // The tab's title names the history and its version, never its address (FR-011c).
  useEffect(() => {
    document.title = shown ? `${shown.title} · ${shownName ?? "no version yet"} — Maxitor` : "Maxitor";
  }, [shown, shownName]);

  // Keep the URL accurate as state resolves — replaceState, so it never adds a history entry on its own.
  useEffect(() => {
    syncUrlToState(serviceUrl, diagram);
  }, [serviceUrl, diagram, shown?.b]);

  function handleSelectDiagram(sel: DiagramSelection) {
    stopFollowingOnOwnMove();
    pushUrlState(serviceUrl, sel);
    setDiagram(sel);
  }

  /** A history opened from the field or Recent: show it on its default version, as a new navigation. */
  function handleHistoryOpened(history: OpenedHistory, key: string) {
    setReloadError(null);
    opened.show(history, key, null);
    setUrlHistory({ name: history.name, b: null });
    pushUrlState(null, null);
  }

  /** Pick a version: in a room the whole room moves (FR-022a), outside one only this tab. */
  function pickVersion(b: string) {
    if (room.inRoom) room.send({ type: "version", b });
    else opened.pick(b);
  }

  /** Pick two versions, A before B: in a room the whole room moves, outside one only this tab (spec 038, FR-016). */
  function pickRange(range: Range) {
    if (room.inRoom) room.send({ type: "version", b: range.b, a: range.a });
    else opened.pickRange(range);
  }

  /** One step older or newer without the picker — the version in One, the whole range in Diff — as a pick would. */
  function step(delta: -1 | 1) {
    if (!shown?.b) return;
    const next = stepShown(trackPoints, shown.a, shown.b, delta);
    if (next?.a) pickRange({ a: next.a, b: next.b });
    else if (next) pickVersion(next.b);
  }
  const stepRef = useRef(step);
  stepRef.current = step;

  // Shift + ← → step the same way anywhere on the page.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const delta = stepOfKey(event);
      if (delta === null) return;
      event.preventDefault();
      stepRef.current(delta);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  /** One → Diff keeps the version as B and puts A on the one before it; Diff → One keeps B (spec 038, FR-013). */
  function pickMode(mode: PickerMode) {
    if (!shown?.b) return;
    if (mode === "one") pickVersion(shown.b);
    else {
      const range = oneToDiff(trackPoints, shown.b);
      if (range) pickRange(range);
    }
  }

  function handleLoaded(url: string) {
    setUrlHistory(null);
    opened.close();
    pushUrlState(url, null);
    setActiveSource(url);
    setServiceUrl(url);
    setReloadError(null);
    // The typed source already sent its one POST /api/load; this only reads its sidebar.
    void reload().catch(() => undefined);
  }

  /** *Load a different service*: inside a room it asks first, since the room is for this service (FR-064). */
  function requestReset() {
    if (room.inRoom) setAskLeaveForService(true);
    else handleReset();
  }

  function handleReset() {
    setUrlHistory(null);
    opened.close();
    setActiveHistoryKey("");
    pushUrlState(null, null);
    setActiveSource(null);
    setServiceUrl(null);
    setDiagram(null);
    setReloadError(null);
    setBusy(false);
    reset();
  }

  /** Rebuild the open source from its service, then read its sidebar and the current diagram again. */
  async function handleReloadFromService() {
    if (!serviceUrl || reloading) return;
    if (room.inRoom) {
      // Inside a room Reload rebuilds the graph for everyone and nobody leaves (FR-065).
      room.send({ type: "reload" });
      return;
    }
    setReloading(true);
    setReloadError(null);
    try {
      await loadGraph(serviceUrl);
      await reload();
      setWorkspaceKey((count) => count + 1);
    } catch (e) {
      setReloadError(e instanceof Error ? e.message : String(e));
    } finally {
      setReloading(false);
    }
  }

  return (
    <MainLayout
      topRow={(compact) => (
        <Box sx={{ display: "flex", alignItems: "center", gap: 1, width: "100%", minWidth: 0 }}>
          {shown && hasPicker(opened.mode) && (
            <VersionButton
              ref={versionButton}
              name={shown.a ? (phone ? `A ${shortNameOf(shown.versions, shown.a, shown.proposals)} → B ${shortNameOf(shown.versions, shown.b, shown.proposals)}` : `A ${olderName ?? "—"} → B ${shownName ?? "—"}`) : (shownName ?? "—")}
              compact={phone}
              counts={shown.a && diagram?.kind === "erd" ? diffCounts : null}
              open={pickerOpen}
              onClick={() => setPickerOpen((open) => !open)}
              onStep={step}
              canStep={{ older: shown.b ? stepShown(trackPoints, shown.a, shown.b, -1) !== null : false, newer: shown.b ? stepShown(trackPoints, shown.a, shown.b, 1) !== null : false }}
            />
          )}
          <Box sx={{ flex: 1 }} />
        <RoomBar
          session={room}
          page={page}
          pageLabel={labelOfPage}
          canOpen={serviceUrl !== null || (shown !== null && hasPicker(opened.mode))}
          compact={compact}
          onGoTo={(participant, theirPage) => {
            // Going to someone is your own navigation: it ends following (FR-051).
            stopFollowingOnOwnMove();
            goTo(participant, theirPage);
          }}
          onFollow={follow}
          onStopFollowing={stopFollowing}
        />
        </Box>
      )}
      overlay={
        <>
          <RoomBanner banner={room.banner} onOpenRoom={room.requestOpen} onDismiss={room.dismissBanner} />
          <FollowFrame following={following} onStop={stopFollowing} />
          <RoomBanner
            banner={model.updated ? { kind: "info", text: "The model was updated.", open: false } : null}
            onOpenRoom={room.requestOpen}
            onDismiss={model.dismiss}
          />
          <RoomBanner
            banner={room.pageNotice ? { kind: "warn", text: room.pageNotice, open: false } : null}
            onOpenRoom={room.requestOpen}
            onDismiss={room.dismissPageNotice}
          />
          <RoomBanner
            banner={opened.notice ? { kind: "info", text: opened.notice, open: false } : null}
            onOpenRoom={room.requestOpen}
            onDismiss={() => opened.setNotice(null)}
          />
        </>
      }
      sidebar={
        <LeftSidebar
          diagram={diagram}
          onSelectDiagram={handleSelectDiagram}
          sidebar={sidebar}
          onLoaded={handleLoaded}
          onHistoryOpened={handleHistoryOpened}
          onReset={requestReset}
          source={serviceUrl}
          onReloadFromService={() => void handleReloadFromService()}
          reloading={reloading}
          reloadError={reloadError}
          busy={busy}
        />
      }
    >
      {shown && opened.mode === "M7" ? (
        <WorkspaceNote text="This history has no version yet." />
      ) : shownVersion?.refused ? (
        <WorkspaceNote text={`${shown?.a ? "B " : ""}${shownName ?? "This version"} is refused: ${shownVersion.refused}`} />
      ) : olderVersion?.refused ? (
        <WorkspaceNote text={`A ${olderName ?? "This version"} is refused: ${olderVersion.refused}`} />
      ) : (
        <PageSettingsProvider page={page} room={sharedSettings}>
          <DiagramWorkspacePage key={`workspace-${workspaceKey}`} diagram={diagram} />
        </PageSettingsProvider>
      )}
      {shown && (
        <VersionPicker
          anchor={pickerOpen ? versionButton : null}
          onClose={() => setPickerOpen(false)}
          title={shown.title}
          versions={shown.versions}
          live={shown.live}
          liveIs={shown.liveSameAs}
          proposals={shown.proposals}
          value={shown.b}
          onChange={pickVersion}
          phone={phone}
          mode={pickerMode}
          onMode={pickMode}
          diffOffered={diffOffered(trackPoints)}
          range={shown.a && shown.b ? { a: shown.a, b: shown.b } : null}
          onRange={pickRange}
          older={shown.a ? <VersionMessage version={olderVersion} repository={shown.host === "github" ? shown.repository : null} /> : undefined}
          between={
            shown.a && shown.b ? (
              <VersionsBetween versions={shown.versions} live={shown.live} liveIs={shown.liveSameAs} proposals={shown.proposals} range={{ a: shown.a, b: shown.b }} repository={shown.host === "github" ? shown.repository : null} />
            ) : undefined
          }
        >
          <VersionMessage
            version={shownVersion ?? (shown.b === "live" ? versionOf(shown, shown.liveSameAs) : null)}
            repository={shown.host === "github" ? shown.repository : null}
            liveLine={shown.b === "live" ? liveLine(shown.versions, liveState) : undefined}
          />
        </VersionPicker>
      )}
      {surface && pointersLive && !room.hidePointers && <PointerLayer surface={surface} participants={pointerPeople} />}
      <NameDialog
        mode={room.dialog?.mode ?? null}
        initialName={room.dialog?.mode === "rename" ? (room.room?.participants.find((p) => p.id === room.room?.youId)?.name ?? lastName()) : lastName()}
        pageLabel={labelOfPage(page)}
        error={room.dialog?.error ?? null}
        onCancel={room.cancelDialog}
        onConfirm={room.confirmName}
      />
      <LeaveForServiceDialog
        open={askLeaveForService}
        onCancel={() => setAskLeaveForService(false)}
        onConfirm={() => {
          setAskLeaveForService(false);
          room.leave();
          handleReset();
        }}
      />
    </MainLayout>
  );
}

/** A sentence in place of the diagram: a history with no version yet, or a refused version and why. */
function WorkspaceNote({ text }: { text: string }) {
  return (
    <Box role="status" sx={{ m: "auto", p: 4, maxWidth: 520, textAlign: "center", fontSize: 14, color: "rgb(71, 85, 105)" }}>
      {text}
    </Box>
  );
}

