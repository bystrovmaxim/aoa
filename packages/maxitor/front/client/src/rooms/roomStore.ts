// src/rooms/roomStore.ts
/**
 * The room as this tab knows it, rebuilt from the server's events.
 *
 * ``reduceRoom`` is pure: the session hook feeds it every event and renders what it returns. The
 * server sends a whole ``welcome`` after every (re)connect, so nothing here is ever patched up after
 * a lost connection.
 */
import type { FollowLinks, PageSettings, Participant, ServerEvent } from "@/rooms/protocol";

/** A line in the row that fades after a few seconds: *Boris joined*, *Anna left*. */
export type RoomNotice = { id: number; text: string };

export type RoomState = {
  roomId: string;
  source: string;
  youId: string;
  createdBy: string;
  /** Everyone in the room, you included, in the order they joined. */
  participants: Participant[];
  settings: PageSettings;
  follows: FollowLinks;
  serverBuild: string;
  /** The page the server chose because the link's page does not exist for this service. */
  fallbackPage: string | null;
  /** Joins, leaves and refusals of this tab's own messages (a name, a setting, Reload), fading. */
  notices: RoomNotice[];
  /** Bumped by ``graph_changed``: the service's graph was rebuilt for the room. */
  graphVersion: number;
};

let nextNoticeId = 1;

function notice(text: string): RoomNotice {
  return { id: nextNoticeId++, text };
}

function upsert(participants: Participant[], next: Participant): Participant[] {
  const index = participants.findIndex((p) => p.id === next.id);
  if (index < 0) return [...participants, next];
  return participants.map((p, i) => (i === index ? next : p));
}

/** The room after ``event``; ``null`` before the first ``welcome``. */
export function reduceRoom(state: RoomState | null, event: ServerEvent): RoomState | null {
  if (event.type === "welcome") {
    return {
      roomId: event.room.id,
      source: event.room.source,
      youId: event.you.id,
      createdBy: event.room.created_by,
      participants: event.room.participants,
      settings: event.room.settings,
      follows: event.room.follows,
      serverBuild: event.server_build,
      fallbackPage: event.fallback_page,
      notices: state?.notices ?? [],
      graphVersion: state?.graphVersion ?? 0,
    };
  }
  if (!state) return null;
  switch (event.type) {
    case "joined":
      return {
        ...state,
        participants: upsert(state.participants, event.participant),
        notices: [...state.notices, notice(`${event.participant.name} joined`)],
      };
    case "left":
      return {
        ...state,
        participants: state.participants.filter((p) => p.id !== event.participant.id),
        notices: [...state.notices, notice(`${event.participant.name} left`)],
      };
    case "presence": {
      // A return within two minutes arrives as presence, never as joined: nobody is told.
      const { type: _type, ...participant } = event;
      return { ...state, participants: upsert(state.participants, participant) };
    }
    case "renamed":
      return {
        ...state,
        participants: state.participants.map((p) => (p.id === event.participant ? { ...p, name: event.name } : p)),
      };
    case "setting":
      return {
        ...state,
        settings: { ...state.settings, [event.page]: { ...state.settings[event.page], [event.name]: event.value } },
      };
    case "follows":
      return { ...state, follows: event.follows };
    case "follow_refused":
    case "refused":
      return { ...state, notices: [...state.notices, notice(event.reason)] };
    case "graph_changed":
      return { ...state, graphVersion: state.graphVersion + 1 };
    default:
      return state;
  }
}

/** The room with ``id``'s notice gone. */
export function dismissNotice(state: RoomState, id: number): RoomState {
  return { ...state, notices: state.notices.filter((n) => n.id !== id) };
}

/** The room with this tab's own page set: the server does not echo a tab's presence back to it. */
export function withOwnPage(state: RoomState, page: string): RoomState {
  return { ...state, participants: state.participants.map((p) => (p.id === state.youId ? { ...p, page } : p)) };
}

/** You first, then everyone else in the order they joined. */
export function youFirst(state: RoomState): Participant[] {
  const you = state.participants.find((p) => p.id === state.youId);
  const others = state.participants.filter((p) => p.id !== state.youId);
  return you ? [you, ...others] : others;
}

/** How many participants follow ``id``, directly. */
export function followerCount(state: RoomState, id: string): number {
  return followerNames(state, id).length;
}

/** The names of those who follow ``id`` directly, in the order they joined — not who follows them in turn. */
export function followerNames(state: RoomState, id: string): string[] {
  return state.participants.filter((participant) => state.follows[participant.id] === id).map((participant) => participant.name);
}
