// packages/aoa-client-js/src/types.ts

export interface ResolveItem {
  operation: string;
  params: Record<string, unknown>;
  context?: Record<string, unknown>; // reserved for future client-supplied ABAC hints (chapter 8); server ignores it today
}

// Three outcome classes -- same names as the server's BaseVerdict/
// AllowedVerdict/FailSecurityVerdict/FailErrorVerdict (aoa-action-machine).
// kind is not a channel enum value, it's the class's own name
// (type(self).__name__ on the server). AllowedVerdict is success -- no
// reason field at all, not an empty string. FailSecurityVerdict is a
// durable denial (role/guard=/access_decide said no) -- reason is mandatory.
// FailErrorVerdict is not a denial, it's the absence of a decision: the
// server could not check (unknown endpoint, unhandled exception) -- the one
// class that must never be shown as a denial or cached as one.
export interface AllowedVerdict {
  kind: "AllowedVerdict";
}

export interface FailSecurityVerdict {
  kind: "FailSecurityVerdict";
  reason: string;
}

export interface FailErrorVerdict {
  kind: "FailErrorVerdict";
  reason: string;
}

// Discriminated union: after a check like result.kind === "FailErrorVerdict",
// TypeScript narrows result to FailErrorVerdict inside that branch, so reason
// is visible without a cast. The client-side stale flag (chapter 6) lives on
// a SEPARATE client type, not here. The set of three classes is fixed and
// stable -- later chapters only add new reason values, never a new class.
export type Verdict = AllowedVerdict | FailSecurityVerdict | FailErrorVerdict;

// The resolver's whole response body: the wire-language version plus one
// result per requested item, in the same order.
export interface ResolveResponse {
  version: number;
  results: Verdict[];
}
