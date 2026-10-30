// src/components/history/VersionTrack/proposalLook.ts
import type { ProposalState } from "@/api/history";

/** How a pull request still open is drawn, in GitHub's own colours (Primer): its point's colour, its chip's tint, its state's name. */
export const PROPOSAL_LOOK: Record<ProposalState, { colour: string; tint: string; name: string }> = {
  // GitHub's "attention": a pull request waiting for its review.
  open: { colour: "#9a6700", tint: "#fff8c5", name: "Review required" },
  approved: { colour: "#1a7f37", tint: "#dafbe1", name: "Approved" },
  changes_requested: { colour: "#d1242f", tint: "#ffebe9", name: "Changes requested" },
};

/** A merged pull request's mark, in GitHub's purple. */
export const MERGED_LOOK = { colour: "#8250df", tint: "#fbefff" } as const;

/** A change pushed straight to the branch, with no pull request: grey. */
export const DIRECT_LOOK = { colour: "#8c959f", tint: "#f6f8fa" } as const;

/** Live: what the service runs now, a hollow grey point. */
export const LIVE_LOOK = { colour: "#8c959f" } as const;
