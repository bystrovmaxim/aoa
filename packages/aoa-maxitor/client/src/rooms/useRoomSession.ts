// src/rooms/useRoomSession.ts
/**
 * The tab's room session: whether it is in a room, the name dialog, the connection and the room.
 *
 * ``App`` owns one. It opens a room on **Open room**, joins the room a link names after the name
 * dialog, reports the tab's page and visibility, and leaves on **Leave room** — keeping the page, its
 * settings and layout mode, only taking ``room`` out of the address (spec 028, FR-019 … FR-028).
 */
import { useCallback, useEffect, useReducer, useRef, useState } from "react";
import { setUrlRoom } from "@/lib/urlState";
import { closeSentence } from "@/rooms/closeCodes";
import { RoomConnection, type ConnectionState } from "@/rooms/connection";
import type { ClientMessage, ServerEvent } from "@/rooms/protocol";
import { dismissNotice, reduceRoom, withOwnPage, type RoomState } from "@/rooms/roomStore";

/** What the name dialog is for. */
export type NameDialogMode = "open" | "join" | "rename";

/** A message across the top of the workspace. ``open`` offers **Open room** with it. */
export type RoomBanner = { kind: "info" | "error"; text: string; open: boolean };

const NAME_KEY = "maxitor.name";

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
};

export function useRoomSession({ initialRoom, source, page, onFallbackPage, onGraphChanged }: RoomSessionOptions) {
  const [room, dispatch] = useReducer(reducer, null);
  const [connection, setConnection] = useState<ConnectionState | null>(null);
  const [dialog, setDialog] = useState<{ mode: NameDialogMode; error: string | null } | null>(
    initialRoom ? { mode: "join", error: null } : null,
  );
  const [banner, setBanner] = useState<RoomBanner | null>(null);
  const [inviteOpen, setInviteOpen] = useState(false);
  const target = useRef<string | null>(initialRoom);
  const socket = useRef<RoomConnection | null>(null);
  const opening = useRef(false);
  const callbacks = useRef({ onFallbackPage, onGraphChanged });
  callbacks.current = { onFallbackPage, onGraphChanged };
  const pageRef = useRef(page);
  pageRef.current = page;
  const graphVersion = useRef(0);

  const send = useCallback((message: ClientMessage) => socket.current?.send(message), []);

  const onEvent = useCallback((event: ServerEvent) => {
    if (event.type === "welcome") {
      target.current = event.room.id;
      setUrlRoom(event.room.id);
      if (opening.current) setInviteOpen(true);
      opening.current = false;
      if (event.fallback_page) callbacks.current.onFallbackPage(event.fallback_page);
    }
    dispatch({ kind: "event", event });
  }, []);

  const onState = useCallback((state: ConnectionState) => {
    setConnection(state);
    if (state.kind !== "closed") return;
    socket.current = null;
    dispatch({ kind: "reset" });
    setInviteOpen(false);
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
    send({ type: "leave" });
    socket.current?.close();
    socket.current = null;
    target.current = null;
    setUrlRoom(null);
    setConnection(null);
    setInviteOpen(false);
    dispatch({ kind: "reset" });
  }, [send]);

  // Every page the tab opens is reported, so the room knows where its participants are (FR-013).
  useEffect(() => {
    if (!page) return;
    socket.current?.setPage(page);
    if (room) {
      send({ type: "page", page });
      dispatch({ kind: "own-page", page });
    }
    // The page is reported again after every welcome, which is a fresh join.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, room?.roomId, connection?.kind, send]);

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
    inviteOpen,
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
  };
}

export type RoomSession = ReturnType<typeof useRoomSession>;
