// src/lib/useCaseRoleLabels.ts
/**
 * Role labels on the use-case diagram appear only for the role under the pointer (spec 029, FR-042).
 *
 * The DOT source gives every role node the class ``uc-role``; the viewer hides a role's text unless its
 * node carries ``is-hovered``, which this module sets on ``mouseenter`` and clears on ``mouseleave``.
 * A class, not CSS ``:hover``, so a follower — whose diagram replays the followed person's hover with
 * those very events — sees the label too.
 */

/** The class a role node carries in the drawing. */
export const ROLE_NODE_CLASS = "uc-role";
/** The class that shows a role's label. */
export const ROLE_HOVER_CLASS = "is-hovered";

/**
 * Show each role's label while it is hovered. Listens once on ``root``, in the capture phase, so it keeps
 * working when the drawing inside is replaced and sees the non-bubbling ``mouseenter`` of every node.
 */
export function bindRoleLabels(root: Element, signal: AbortSignal): void {
  const toggle = (on: boolean) => (event: Event) => {
    const target = event.target;
    if (target instanceof Element && target.matches(`g.node.${ROLE_NODE_CLASS}`)) target.classList.toggle(ROLE_HOVER_CLASS, on);
  };
  root.addEventListener("mouseenter", toggle(true), { capture: true, signal });
  root.addEventListener("mouseleave", toggle(false), { capture: true, signal });
}

/** The viewer's style for role labels: hidden, and shown on a hovered role. */
export const roleLabelSx = {
  [`& g.node.${ROLE_NODE_CLASS} text`]: { visibility: "hidden" },
  [`& g.node.${ROLE_NODE_CLASS}.${ROLE_HOVER_CLASS} text`]: { visibility: "visible" },
} as const;
