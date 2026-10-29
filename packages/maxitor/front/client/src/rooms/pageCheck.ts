// src/rooms/pageCheck.ts
/**
 * Whether this tab's picture is the room's (spec 028, FR-090 … FR-093).
 *
 * After every draw the tab reports its client build, the fingerprint of the graph it drew, the
 * layout hash and the settings digest; the server answers ``check``. Another build reloads the tab
 * — at most once in five minutes, keeping zoom and centre; another graph is re-read in place; a
 * layout that differs although build and graph agree turns pointers off on that page, both ways.
 */
import type { SavedView } from "@/rooms/diagramSurface";
import type { ClientMessage } from "@/rooms/protocol";

export type CheckAnswer = { build: "ok" | "reload"; fingerprint: "ok" | "reread"; layout: "ok" | "off" };

export type CheckOutcome = {
  /** Reload the page now. */
  reload: boolean;
  /** A reload is due but one happened under five minutes ago: say so instead of looping. */
  reloadHeldBack: boolean;
  /** Read the graph again in place. */
  reread: boolean;
  /** Pointers are off on this page, both ways. */
  pointersOff: boolean;
};

/** The shortest time between two reloads Maxitor does by itself. */
export const RELOAD_GUARD_MS = 5 * 60 * 1000;

const VIEW_KEY = "maxitor.view.restore";
const RELOAD_KEY = "maxitor.reload.at";

/** What to do about a ``check``, given when this tab last reloaded itself. */
export function decideCheck(check: CheckAnswer, now: number, lastReloadAt: number | null): CheckOutcome {
  const due = check.build === "reload";
  const allowed = lastReloadAt === null || now - lastReloadAt >= RELOAD_GUARD_MS;
  return {
    reload: due && allowed,
    reloadHeldBack: due && !allowed,
    reread: check.fingerprint === "reread",
    pointersOff: check.layout === "off",
  };
}

/** The sentence the page shows for an outcome, or ``null``. */
export function checkNotice(outcome: CheckOutcome): string | null {
  if (outcome.reload) return "Maxitor was updated — reloading…";
  if (outcome.reloadHeldBack) return "Maxitor was updated. Reload this page to get the new version.";
  if (outcome.pointersOff) return "Pointers are off on this page: your diagram is laid out differently from the room's.";
  return null;
}

/** The ``page`` message after a draw: the page, the build, the graph and what the picture is. */
export function pageReport(page: string, build: string, fingerprint: string | null, element: HTMLElement | null): ClientMessage {
  const message: Extract<ClientMessage, { type: "page" }> = { type: "page", page, build };
  if (fingerprint) message.fingerprint = fingerprint;
  const hash = element?.getAttribute("data-layout-hash");
  if (hash) {
    message.layout_hash = hash;
    message.settings_digest = element?.getAttribute("data-layout-input") ?? "";
  }
  return message;
}

function read(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function write(key: string, value: string | null): void {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch {
    // Without storage the reload simply starts from the fitted view.
  }
}

/** When this tab last reloaded itself, or ``null``. */
export function lastSelfReload(): number | null {
  const value = Number(read(RELOAD_KEY));
  return Number.isFinite(value) && value > 0 ? value : null;
}

/** Remember the view and the time, then reload. */
export function reloadKeepingView(view: SavedView | null, now: number, reload: () => void): void {
  write(RELOAD_KEY, String(now));
  write(VIEW_KEY, view ? JSON.stringify(view) : null);
  reload();
}

/** The view saved before a self-reload, once: reading it forgets it. */
export function takeSavedView(): SavedView | null {
  const raw = read(VIEW_KEY);
  if (!raw) return null;
  write(VIEW_KEY, null);
  try {
    const view = JSON.parse(raw) as SavedView;
    return [view.x, view.y, view.zoom].every(Number.isFinite) ? view : null;
  } catch {
    return null;
  }
}
