// packages/aoa-client-js/src/types.ts

export interface ResolveItem {
  operation: string;
  params: Record<string, unknown>;
  context?: Record<string, unknown>; // reserved for future client-supplied ABAC hints (chapter 8); server ignores it today
}

// Three outcome classes -- same names as the server's BaseVerdict/
// AllowedVerdict/FailSecurityVerdict/FailErrorVerdict (aoa-action-machine).
// kind is not a channel enum value, it's the name of the class that answered.
// AllowedVerdict is success -- no
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

// Everything the rest of this library actually needs from an engine: one
// method. AoaEngine satisfies it (and says so with `implements`), and so does
// the test double in aoa-client-js/testing.
//
// Why an interface at all, when AoaEngine is right there: AoaEngine has
// private fields (config, cache), and a private field makes a TypeScript class
// type NOMINAL, not structural. A hand-written object with the same public
// surface is therefore NOT assignable to AoaEngine -- no amount of matching
// methods helps. Every consumer that named the class (makeGatePrimitive,
// makeCallablePrimitive, buildDynamicGateApi, and the generated
// createGateApi/createApi) was consequently impossible to hand a test double
// without an `as any`. Naming this interface instead costs nothing at runtime
// and makes the double a first-class citizen rather than a cast.
//
// Deliberately narrow -- resolve() only. cachePartition, loadFrom() and the
// cache stay on the concrete class: nothing between the engine and a primitive
// reads them, and widening this interface later is additive, while narrowing
// it would be a break.
export interface ResolveEngine {
  resolve(items: ResolveItem[], opts?: { traceId?: string; skipCache?: boolean }): Promise<Verdict[]>;
}
