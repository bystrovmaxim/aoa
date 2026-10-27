// src/rooms/followCircle.ts
/**
 * The follow-circle rule, as the server checks it (``model/rooms/follow_circle.py``), so the card can
 * disable **Follow** with its reason before anything is sent (spec 028, FR-054). The server stays the
 * authority: two crossing requests are settled there, under the room's lock.
 */
import type { FollowLinks } from "@/rooms/protocol";

/** Whether ``follower`` following ``target`` closes a circle: ``target``'s own links lead back to ``follower``. */
export function wouldCloseCircle(follows: FollowLinks, follower: string, target: string): boolean {
  const seen = new Set<string>();
  let current: string | null | undefined = target;
  while (current != null && !seen.has(current)) {
    if (current === follower) return true;
    seen.add(current);
    current = follows[current];
  }
  return false;
}

/**
 * How ``other`` follows ``you``: ``"direct"`` when they follow you, the id of the person they follow
 * when it is through others, ``null`` when they do not.
 */
export function followsYou(follows: FollowLinks, you: string, other: string): "direct" | string | null {
  const first = follows[other];
  if (first == null || other === you) return null;
  if (first === you) return "direct";
  return wouldCloseCircle(follows, you, other) ? first : null;
}
