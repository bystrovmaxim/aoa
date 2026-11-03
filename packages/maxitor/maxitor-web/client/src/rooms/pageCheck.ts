// src/rooms/pageCheck.ts
/**
 * Whether this tab's picture is the room's (spec 028, FR-090 … FR-093).
 *
 * After every draw the tab reports its client build, the fingerprint of the graph it drew, the
 * layout hash and the settings digest; the server answers ``check``. Another build reloads the tab
 * — at most once in five minutes, keeping zoom and centre; another graph is re-read in place. A
 * layout other than the room's — the followed person's, else the one most tabs drew (spec 038) —
 * reloads the tab once the same way. The report after it says so (``layout_reloaded``): a layout still other
 * then reloads the room's side once instead, since it may be the one on old code; still other after that, the
 * server answers ``off`` and pointers stay off on that page, both ways.
 */
import { comparedDigest } from "@/api/compare";
import type { SavedView } from "@/rooms/diagramSurface";
import type { ClientMessage } from "@/rooms/protocol";

export type CheckAnswer = { build: "ok" | "reload"; fingerprint: "ok" | "reread"; layout: "ok" | "reload" | "off" };

export type CheckOutcome = {
  /** Reload the page now. */
  reload: boolean;
  /** The reload is for the layout: the room drew the page another way. */
  layoutReload: boolean;
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
const LAYOUT_RELOAD_KEY = "maxitor.layout-reload.at";

/** What to do about a ``check``, given when this tab last reloaded itself for its build and for its layout. */
export function decideCheck(check: CheckAnswer, now: number, lastReloadAt: number | null, lastLayoutReloadAt: number | null = null): CheckOutcome {
  const allowedSince = (at: number | null) => at === null || now - at >= RELOAD_GUARD_MS;
  const due = check.build === "reload";
  const allowed = allowedSince(lastReloadAt);
  const layoutDue = !due && check.layout === "reload";
  const layoutAllowed = layoutDue && allowedSince(lastLayoutReloadAt);
  return {
    reload: (due && allowed) || layoutAllowed,
    layoutReload: layoutAllowed,
    reloadHeldBack: due && !allowed,
    reread: check.fingerprint === "reread",
    pointersOff: (layoutDue && !layoutAllowed) || (!due && check.layout === "off"),
  };
}

/** The sentence the page shows for an outcome, or ``null``. */
export function checkNotice(outcome: CheckOutcome): string | null {
  if (outcome.layoutReload) return "Taking the room's picture of this page — reloading…";
  if (outcome.reload) return "Maxitor was updated — reloading…";
  if (outcome.reloadHeldBack) return "Maxitor was updated. Reload this page to get the new version.";
  if (outcome.pointersOff) return "Pointers are off on this page: your diagram is laid out differently from the room's.";
  return null;
}

/**
 * The ``page`` message after a draw: the page, the build, the graph and what the picture is — and whether this tab
 * reloaded for its layout within the last five minutes, ``now`` being the time.
 */
export function pageReport(page: string, build: string, fingerprint: string | null, element: HTMLElement | null, now = Date.now(), elementA: HTMLElement | null = null): ClientMessage {
  const message: Extract<ClientMessage, { type: "page" }> = { type: "page", page, build };
  const layoutReloadAt = lastLayoutReload();
  if (layoutReloadAt !== null && now - layoutReloadAt < RELOAD_GUARD_MS) message.layout_reloaded = true;
  if (fingerprint) message.fingerprint = fingerprint;
  const hash = element?.getAttribute("data-layout-hash");
  if (hash) {
    // In Side by side the picture is two, and in any comparison the digest takes in the two graphs (spec 044, FR-035).
    const hashA = elementA?.getAttribute("data-layout-hash");
    message.layout_hash = hashA ? `${hashA}.${hash}` : hash;
    const inputs = [elementA?.getAttribute("data-layout-input"), element?.getAttribute("data-layout-input") ?? "", comparedDigest()];
    message.settings_digest = inputs.filter((part) => part !== undefined && part !== null && part !== "").join(".");
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

function readTime(key: string): number | null {
  const value = Number(read(key));
  return Number.isFinite(value) && value > 0 ? value : null;
}

/** When this tab last reloaded itself for a new build, or ``null``. */
export function lastSelfReload(): number | null {
  return readTime(RELOAD_KEY);
}

/** When this tab last reloaded itself to take the room's layout, or ``null``. */
export function lastLayoutReload(): number | null {
  return readTime(LAYOUT_RELOAD_KEY);
}

/** Remember the view and the time — of a layout reload when ``forLayout`` — then reload. */
export function reloadKeepingView(view: SavedView | null, now: number, reload: () => void, forLayout = false): void {
  write(forLayout ? LAYOUT_RELOAD_KEY : RELOAD_KEY, String(now));
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
