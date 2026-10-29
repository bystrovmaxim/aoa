// src/rooms/useRoomSession.ts
/**
 * The tab's room session: whether it is in a room, the name dialog, the connection and the room.
 *
 * ``App`` owns one. It opens a room on **Open room**, joins the room a link names after the name
 * dialog, reports the tab's page and visibility, and leaves on **Leave room** — keeping the page, its
 * settings and layout mode, only taking ``room`` out of the address (spec 028, FR-019 … FR-028).
 */
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { keepRoomSettings, ownSettingsByPage } from "@/lib/pageSettings";
import { seedMessages } from "@/rooms/seed";
import { setUrlRoom } from "@/lib/urlState";
import { closeSentence } from "@/rooms/closeCodes";
import { RoomConnection, type ConnectionState } from "@/rooms/connection";
import type { DiagramSurface } from "@/rooms/diagramSurface";
import { checkNotice, decideCheck, lastSelfReload, pageReport, reloadKeepingView, takeSavedView } from "@/rooms/pageCheck";
import { clearFocus, putFocus } from "@/rooms/focusStore";
import { clearPointers, dropPointer, putPointer, putViewport } from "@/rooms/pointerStore";
import type { ClientMessage, ServerEvent } from "@/rooms/protocol";
import { dismissNotice, reduceRoom, withOwnPage, type RoomState } from "@/rooms/roomStore";

/** What the name dialog is for. */
export type NameDialogMode = "open" | "join" | "rename";

/** A message across the top of the workspace. ``open`` offers **Open room** with it. */
export type RoomBanner = { kind: "info" | "warn" | "error"; text: string; open: boolean };

const NAME_KEY = "maxitor.name";
const HIDE_POINTERS_KEY = "maxitor.hidePointers";

function storedFlag(key: string): boolean {
  try {
    return localStorage.getItem(key) === "1";
  } catch {
    return false;
  }
}

function storeFlag(key: string, on: boolean): void {
  try {
    localStorage.setItem(key, on ? "1" : "0");
  } catch {
    // The choice lasts for this page only.
  }
}

/** The ``data-layout-hash`` the diagram on screen carries now, following every redraw. */
function useLayoutHash(surface: DiagramSurface | null): string | null {
  const [hash, setHash] = useState<string | null>(null);
  useEffect(() => {
    const element = surface?.element;
    if (!element) {
      setHash(null);
      return undefined;
    }
    const read = () => setHash(element.getAttribute("data-layout-hash"));
    read();
    const observer = new MutationObserver(read);
    observer.observe(element, { attributes: true, attributeFilter: ["data-layout-hash", "data-layout-input"] });
    return () => observer.disconnect();
  }, [surface]);
  return hash;
}

/** The name used last in this browser, to fill the dialog with. */
export function lastName(): string {
  try {
    return localStorage.getItem(NAME_KEY) ?? "";
  } catch {
    return "";
  }
}

function rememberName(name: string): void {
  try {
    localStorage.setItem(NAME_KEY, name);
  } catch {
    // Without storage the dialog starts empty next time.
  }
}

/** A name the server accepts: 1 to 40 characters after trimming (FR-011). */
export function nameIsValid(name: string): boolean {
  const length = [...name.trim()].length;
  return length >= 1 && length <= 40;
}

type Action = { kind: "event"; event: ServerEvent } | { kind: "reset" } | { kind: "dismiss"; id: number } | { kind: "own-page"; page: string };

function reducer(state: RoomState | null, action: Action): RoomState | null {
  switch (action.kind) {
    case "event":
      return reduceRoom(state, action.event);
    case "reset":
      return null;
    case "dismiss":
      return state ? dismissNotice(state, action.id) : state;
    case "own-page":
      return state ? withOwnPage(state, action.page) : state;
  }
}

export type RoomSessionOptions = {
  /** The room the address named when the page opened, or ``null``. */
  initialRoom: string | null;
  /** The open source; a room needs one. */
  source: string | null;
  /** The key of the page the tab shows, or ``null`` before one is chosen. */
  page: string | null;
  /** The server opened the tab on another page than its link named (FR-010). */
  onFallbackPage: (page: string) => void;
  /** The room's source was rebuilt: read the left panel and the diagram again. */
  onGraphChanged: () => void;
  /** The diagram on screen, for the page check and the restored view. */
  surface: DiagramSurface | null;
  /** The fingerprint of the graph the left panel was read from. */
  fingerprint: string | null;
};

export function useRoomSession({ initialRoom, source, page, onFallbackPage, onGraphChanged, surface, fingerprint }: RoomSessionOptions) {
  const [room, dispatch] = useReducer(reducer, null);
  const [connection, setConnection] = useState<ConnectionState | null>(null);
  const [dialog, setDialog] = useState<{ mode: NameDialogMode; error: string | null } | null>(
    initialRoom ? { mode: "join", error: null } : null,
  );
  const [banner, setBanner] = useState<RoomBanner | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  /** A sentence about this tab's picture: reloading, held back, or pointers off. */
  const [pageNotice, setPageNotice] = useState<string | null>(null);
  /** The page whose layout differs from the room's: pointers are off there, both ways (FR-093). */
  const [pointersOffPage, setPointersOffPage] = useState<string | null>(null);
  const [hidePointers, setHidePointers] = useState(() => storedFlag(HIDE_POINTERS_KEY));
  const layoutHash = useLayoutHash(surface);
  const surfaceRef = useRef(surface);
  surfaceRef.current = surface;
  const target = useRef<string | null>(initialRoom);
  const socket = useRef<RoomConnection | null>(null);
  const opening = useRef(false);
  const callbacks = useRef({ onFallbackPage, onGraphChanged });
  callbacks.current = { onFallbackPage, onGraphChanged };
  const pageRef = useRef(page);
  pageRef.current = page;
  const graphVersion = useRef(0);

  const send = useCallback((message: ClientMessage) => socket.current?.send(message), []);

  /** Send this tab's own settings to the room it just opened, and show them before the echo. */
  const seedRoom = useCallback((you: string) => {
    for (const message of seedMessages(ownSettingsByPage())) {
      socket.current?.send(message);
      if (message.type !== "seed") continue;
      for (const [name, value] of Object.entries(message.settings)) {
        dispatch({ kind: "event", event: { type: "setting", page: message.page, name, value, by: you } });
      }
    }
  }, []);

  const onEvent = useCallback((event: ServerEvent) => {
    // Pointers and screens change many times a second: they bypass React state.
    if (event.type === "pointer") {
      putPointer(event.participant, { x: event.x, y: event.y, kind: event.kind, at: Date.now() });
      return;
    }
    if (event.type === "viewport") {
      putViewport(event.participant, { cx: event.cx, cy: event.cy, w: event.w, h: event.h });
      return;
    }
    if (event.type === "focus") {
      const { participant, page, hover, tooltip, selection, panels } = event;
      putFocus(participant, { page, hover, tooltip, selection, panels });
      return;
    }
    if (event.type === "check") {
      const outcome = decideCheck(event, Date.now(), lastSelfReload());
      setPageNotice(checkNotice(outcome));
      setPointersOffPage(outcome.pointersOff ? pageRef.current : null);
      if (outcome.reload) reloadKeepingView(surfaceRef.current?.view() ?? null, Date.now(), () => window.location.reload());
      else if (outcome.reread) callbacks.current.onGraphChanged();
      return;
    }
    if (event.type === "left" || (event.type === "presence" && (event.away || event.page !== pageRef.current))) {
      dropPointer(event.type === "left" ? event.participant.id : event.id);
    }
    if (event.type === "welcome") {
      target.current = event.room.id;
      setUrlRoom(event.room.id);
      if (opening.current) setInviteOpen(true);
      if (event.fallback_page) callbacks.current.onFallbackPage(event.fallback_page);
    }
    dispatch({ kind: "event", event });
    if (event.type === "welcome") {
      // A room this tab opened starts as its picture: its own settings, shown at once, confirmed by the echo.
      if (opening.current) seedRoom(event.you.id);
      opening.current = false;
    }
  }, [seedRoom]);

  const roomRef = useRef(room);
  roomRef.current = room;

  const onState = useCallback((state: ConnectionState) => {
    setConnection(state);
    if (state.kind !== "closed") return;
    if (roomRef.current) keepRoomSettings(roomRef.current.settings);
    socket.current = null;
    dispatch({ kind: "reset" });
    setInviteOpen(false);
    clearPointers();
    clearFocus();
    setPageNotice(null);
    if (state.code === 4422) {
      // The server refused the name: the dialog opens again with the rule.
      setDialog({ mode: opening.current ? "open" : "join", error: closeSentence(4422) });
      return;
    }
    target.current = null;
    opening.current = false;
    setUrlRoom(null);
    const text = closeSentence(state.code);
    if (text) setBanner({ kind: state.code === 4404 ? "info" : "error", text, open: state.code === 4404 });
  }, []);

  const connect = useCallback(
    (name: string) => {
      const roomId = target.current ?? "new";
      if (roomId === "new" && !source) return;
      socket.current?.close();
      const next = new RoomConnection({
        room: roomId,
        source: source ?? undefined,
        name,
        page: pageRef.current ?? "",
        onEvent,
        onState,
      });
      socket.current = next;
      next.open();
    },
    [source, onEvent, onState],
  );

  /** **Open room**: ask for a name, then open a new room for the source. */
  const requestOpen = useCallback(() => {
    setBanner(null);
    target.current = null;
    setDialog({ mode: "open", error: null });
  }, []);

  /** **Change name** on your own card. */
  const requestRename = useCallback(() => setDialog({ mode: "rename", error: null }), []);

  const cancelDialog = useCallback(() => {
    if (dialog?.mode === "join") {
      // Declining to join leaves the page as it is, without the room.
      target.current = null;
      setUrlRoom(null);
    }
    setDialog(null);
  }, [dialog]);

  const confirmName = useCallback(
    (raw: string) => {
      const name = raw.trim();
      if (!nameIsValid(name) || !dialog) return;
      rememberName(name);
      setDialog(null);
      if (dialog.mode === "rename") {
        send({ type: "rename", name });
        return;
      }
      opening.current = dialog.mode === "open";
      connect(name);
    },
    [dialog, connect, send],
  );

  /** **Leave room**: close the connection, keep the page, take ``room`` out of the address. */
  const leave = useCallback(() => {
    if (roomRef.current) keepRoomSettings(roomRef.current.settings);
    send({ type: "leave" });
    socket.current?.close();
    socket.current = null;
    target.current = null;
    setUrlRoom(null);
    setConnection(null);
    setInviteOpen(false);
    setPageNotice(null);
    setPointersOffPage(null);
    clearPointers();
    clearFocus();
    dispatch({ kind: "reset" });
  }, [send]);

  /**
   * Set a page setting for the room: sent as the new value, shown at once; the room's echo of every
   * change, in the order the server took them, ends in the same last value for everyone (FR-031).
   */
  const setPageSetting = useCallback(
    (settingPage: string, name: string, value: unknown) => {
      const you = roomRef.current?.youId ?? "";
      send({ type: "setting", page: settingPage, name, value });
      dispatch({ kind: "event", event: { type: "setting", page: settingPage, name, value, by: you } });
    },
    [send],
  );

  /** **Hide pointers** / **Show pointers**: other people's pointers on this tab, remembered in the browser. */
  const toggleHidePointers = useCallback(() => {
    setHidePointers((hidden) => {
      storeFlag(HIDE_POINTERS_KEY, !hidden);
      return !hidden;
    });
  }, []);

  // Another page: pointers seen on the old one do not belong here.
  useEffect(() => {
    clearPointers();
    clearFocus();
  }, [page]);

  // Every page the tab opens is reported, so the room knows where its participants are (FR-013),
  // and again after every draw with what the picture is, so the room can check it (FR-090).
  useEffect(() => {
    if (!page) return;
    socket.current?.setPage(page);
    if (room) {
      send(pageReport(page, __MAXITOR_BUILD__, fingerprint, layoutHash ? (surfaceRef.current?.element ?? null) : null));
      dispatch({ kind: "own-page", page });
    }
    // The page is reported again after every welcome, which is a fresh join.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, room?.roomId, connection?.kind, send, layoutHash, fingerprint]);

  // After Maxitor reloaded itself, the first diagram opens at the zoom and centre it had (FR-090).
  useEffect(() => {
    if (!surface) return undefined;
    const saved = takeSavedView();
    if (!saved) return undefined;
    // Let the viewer fit first; the saved view then replaces the fit.
    const timer = setTimeout(() => surface.restore(saved), 300);
    return () => clearTimeout(timer);
  }, [surface]);

  // Hidden and shown again: the circle pales while the tab is in the background (FR-044).
  useEffect(() => {
    function report() {
      send({ type: "activity", visible: document.visibilityState === "visible" });
    }
    document.addEventListener("visibilitychange", report);
    return () => document.removeEventListener("visibilitychange", report);
  }, [send]);

  // The room's source was rebuilt by someone's Reload.
  useEffect(() => {
    if (!room || room.graphVersion === graphVersion.current) return;
    graphVersion.current = room.graphVersion;
    callbacks.current.onGraphChanged();
  }, [room]);

  // Joined/left notices fade after a few seconds.
  useEffect(() => {
    if (!room?.notices.length) return;
    const first = room.notices[0];
    const timer = setTimeout(() => dispatch({ kind: "dismiss", id: first.id }), 4000);
    return () => clearTimeout(timer);
  }, [room?.notices]);

  useEffect(() => () => socket.current?.close(), []);

  return {
    room,
    connection,
    dialog,
    banner,
    pageNotice,
    inviteOpen,
    hidePointers,
    toggleHidePointers,
    /** Pointers are off on this page because its layout differs from the room's. */
    pointersOff: page !== null && pointersOffPage === page,
    /** The room id the tab is in or is joining. */
    roomId: room?.roomId ?? target.current,
    inRoom: room !== null,
    requestOpen,
    requestRename,
    cancelDialog,
    confirmName,
    leave,
    send,
    closeInvite: () => setInviteOpen(false),
    openInvite: () => setInviteOpen(true),
    dismissBanner: () => setBanner(null),
    setPageSetting,
    dismissPageNotice: () => setPageNotice(null),
  };
}

export type RoomSession = ReturnType<typeof useRoomSession>;
