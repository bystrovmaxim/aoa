// src/app/App.tsx
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { MainLayout } from "@/components/layout/MainLayout";
import { DiagramWorkspacePage } from "@/components/pages/DiagramWorkspacePage";
import { LeftSidebar } from "@/components/navigation/LeftSidebar";
import { useSidebarPayload } from "@/components/navigation/LeftSidebar/hooks/useSidebarPayload";
import type { DiagramSelection } from "@/model/diagramSelection";
import type { SidebarPayload } from "@/model/sidebar";
import { GraphReadError, onGraphBusy, setActiveSource } from "@/api/client";
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
  setUrlRoom,
  syncUrlToState,
  type UrlDeepLink,
} from "@/lib/urlState";
import { PageSettingsProvider, type RoomSettings } from "@/lib/pageSettings";
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
  if (!initialLinkRef.current) {
    initialLinkRef.current = readUrlDeepLink();
    // The source must be known before the page's first read: the read below goes out with it.
    setActiveSource(initialLinkRef.current.source ?? null);
    // A room link keeps ``room`` in the address while its name dialog is open.
    setUrlRoom(initialLinkRef.current.room ?? null);
  }

  const page = diagram ? pageKeyOf(diagram) : null;
  const [askLeaveForService, setAskLeaveForService] = useState(false);

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
  });
  // Pointers go out and come in only while connected and while this page's layout is the room's
  // (FR-045, FR-093); Hide pointers only stops drawing other people's.
  // Outside a room a tab asks every 30 s whether its graph changed; inside one the room tells it.
  useFingerprintPoll(!room.inRoom && serviceUrl !== null && sidebar !== null, getGraphFingerprint, sidebar?.fingerprint ?? null, handleGraphChanged);
  const pointersLive = room.inRoom && room.connection?.kind === "open" && !room.pointersOff;
  usePointerSender(surface, room.send, pointersLive);
  const roomSettings = room.room?.settings;
  const { setPageSetting } = room;
  const sharedSettings = useMemo<RoomSettings | null>(
    () => (roomSettings ? { settings: roomSettings, set: setPageSetting } : null),
    [roomSettings, setPageSetting],
  );
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

  /** Read the sidebar of ``source``; a refused source falls back to the manual prompt. */
  async function readSidebar(source: string) {
    try {
      await reload();
      pushServiceUrl(source);
      setBusy(false);
    } catch (e) {
      if (e instanceof GraphReadError && e.status === 422) {
        setActiveSource(null);
        setServiceUrl(null);
        reset();
      }
    }
  }

  /** Applies a service+view combination read from the URL — initial load or a popstate. */
  function applyDeepLink(link: UrlDeepLink, activeServiceUrl: string | null, activeSidebar: SidebarPayload | null) {
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

  // Keep the URL accurate as state resolves — replaceState, so it never adds a history entry on its own.
  useEffect(() => {
    syncUrlToState(serviceUrl, diagram);
  }, [serviceUrl, diagram]);

  function handleSelectDiagram(sel: DiagramSelection) {
    stopFollowingOnOwnMove();
    pushUrlState(serviceUrl, sel);
    setDiagram(sel);
  }

  function handleLoaded(url: string) {
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
        <RoomBar
          session={room}
          page={page}
          pageLabel={labelOfPage}
          canOpen={serviceUrl !== null}
          compact={compact}
          onGoTo={(participant, theirPage) => {
            // Going to someone is your own navigation: it ends following (FR-051).
            stopFollowingOnOwnMove();
            goTo(participant, theirPage);
          }}
          onFollow={follow}
          onStopFollowing={stopFollowing}
        />
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
        </>
      }
      sidebar={
        <LeftSidebar
          diagram={diagram}
          onSelectDiagram={handleSelectDiagram}
          sidebar={sidebar}
          onLoaded={handleLoaded}
          onReset={requestReset}
          source={serviceUrl}
          onReloadFromService={() => void handleReloadFromService()}
          reloading={reloading}
          reloadError={reloadError}
          busy={busy}
        />
      }
    >
      <PageSettingsProvider page={page} room={sharedSettings}>
        <DiagramWorkspacePage key={`workspace-${workspaceKey}`} diagram={diagram} />
      </PageSettingsProvider>
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
