// packages/aoa-client-js/src/types.ts

export interface ResolveItem {
  operation: string;
  params: Record<string, unknown>;
  context?: Record<string, unknown>; // reserved for future client-supplied ABAC hints (chapter 8); server ignores it today
}

// The three answers, named exactly as the server names them. `kind` is the name of the
// class that answered, not a value from some list of codes.
//
// AllowedVerdict is yes, and has no reason field at all -- not an empty one.
// FailSecurityVerdict is no: somebody looked and refused, and the reason is always there.
// FailErrorVerdict is neither. Nobody could tell, so it must never be shown as a refusal
// or remembered as one.
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

// Checking `kind` narrows the type inside that branch, so `reason` is reachable without
// a cast. There are three answers and there will stay three: new situations get a new
// reason, never a fourth kind of answer.
export type Verdict = AllowedVerdict | FailSecurityVerdict | FailErrorVerdict;

// The resolver's whole response body: the wire-language version plus one
// result per requested item, in the same order.
export interface ResolveResponse {
  version: number;
  results: Verdict[];
}

// Everything the rest of this library needs from an engine: one method. The real engine
// satisfies it, and so does the test double.
//
// It has to be an interface rather than the class itself. A TypeScript class with private
// fields can only be satisfied by that class -- a hand-written object with an identical
// public surface is still rejected, however well it matches. Asking for the one method
// instead costs nothing at runtime and makes a test double a first-class value rather
// than a cast.
//
// Narrow on purpose. Adding to this later is harmless; taking something away is not.
export interface ResolveEngine {
  resolve(items: ResolveItem[], opts?: { traceId?: string; skipCache?: boolean }): Promise<Verdict[]>;
}
