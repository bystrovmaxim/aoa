// src/rooms/protocol.ts
/**
 * The room connection's messages, as the server sends and expects them
 * (specs/028-maxitor-rooms/contracts/room-protocol.md, specs/029-maxitor-rooms-polish/contracts/room-protocol.md).
 */
import type { FocusState } from "@/rooms/focusStore";

/** A participant as the room shows them. ``page`` is the page key of their active tab. */
export type Participant = {
  id: string;
  name: string;
  colour: string;
  page: string | null;
  visible: boolean;
  away: boolean;
};

/** Page key → setting name → value; the server keeps the last value set. */
export type PageSettings = Record<string, Record<string, unknown>>;

/** Follower id → the id they follow, or ``null``. */
export type FollowLinks = Record<string, string | null>;

export type WelcomeEvent = {
  type: "welcome";
  you: { id: string; colour: string };
  room: {
    id: string;
    source: string;
    /** The history a room on one shows, its address without a key, and its version (spec 037). */
    history?: string | null;
    version?: string | null;
    created_by: string;
    participants: Participant[];
    settings: PageSettings;
    follows: FollowLinks;
  };
  server_build: string;
  fallback_page: string | null;
};

export type ServerEvent =
  | WelcomeEvent
  | { type: "joined"; participant: Participant }
  | { type: "left"; participant: Participant }
  | ({ type: "presence" } & Participant)
  | { type: "renamed"; participant: string; name: string }
  | { type: "setting"; page: string; name: string; value: unknown; by: string }
  | { type: "follows"; follows: FollowLinks }
  | { type: "follow_refused"; target: string; reason: string }
  | { type: "pointer"; participant: string; x: number; y: number; kind: "mouse" | "touch" }
  | { type: "viewport"; participant: string; cx: number; cy: number; w: number; h: number }
  | ({ type: "focus"; participant: string } & FocusState)
  | { type: "check"; build: "ok" | "reload"; fingerprint: "ok" | "reread"; layout: "ok" | "off" }
  | { type: "graph_changed"; fingerprint: string }
  | { type: "version"; b: string | null; by: string | null }
  | { type: "history_changed" }
  | { type: "refused"; code: number; reason: string }
  | { type: "error"; reason: string };

export type ClientMessage =
  | { type: "page"; page: string; build?: string; fingerprint?: string; layout_hash?: string; settings_digest?: string }
  | { type: "activity"; visible: boolean }
  | { type: "setting"; page: string; name: string; value: unknown }
  | { type: "seed"; page: string; settings: Record<string, unknown> }
  | { type: "rename"; name: string }
  | { type: "follow"; target: string }
  | { type: "stop_following" }
  | { type: "leave" }
  | { type: "reload" }
  | { type: "version"; b: string }
  | { type: "pointer"; kind: "mouse" | "touch"; x: number; y: number }
  | { type: "viewport"; cx: number; cy: number; w: number; h: number }
  | ({ type: "focus" } & FocusState);

/** The largest room message Maxitor accepts, in bytes; a larger one closes the connection with 4413. */
export const MAX_MESSAGE_BYTES = 4096;
