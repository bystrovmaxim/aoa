// packages/aoa-client-js/src/primitive.ts
//
// Shared, hand-written machinery behind every generated `Primitive` (chapter 5): the
// generated file only supplies a per-endpoint operation string (for verdict/can) and a
// descriptor (for run) — the actual resolve/invoke logic lives here once, so a codegen
// templating bug can't silently duplicate a mistake into every endpoint's output.

import { AoaResolveError, type AoaEngine } from "./engine.ts";
import type { Verdict } from "./types.ts";

// verdict()/can() only -- no .run() at the type level, not merely absent at runtime.
// This is the whole point of the two-facade split: code that only ever received a
// GatePrimitive (e.g. a UI gate) is statically unable to invoke the action at all.
export interface GatePrimitive<TParams> {
  verdict(params: TParams): Promise<Verdict>;
  can(params: TParams): Promise<boolean>;
}

export interface CallablePrimitive<TParams, TResult> extends GatePrimitive<TParams> {
  run(params: TParams): Promise<TResult>;
}

// What actionInvoker receives: a fully-built call -- method, path, and body already
// fixed by buildInvocation from the generated descriptor. actionInvoker only executes
// it; it cannot construct a different URL or body, so ".can()" and ".run()" are
// guaranteed to be about the same route.
export interface Invocation {
  method: string;
  path: string;
  body: unknown;
}

// Generic in TResult so a real (untyped-internally) implementation -- e.g. a fetch
// wrapper returning Promise<any> -- satisfies this without the generated code needing
// an `as` cast at the call site; each Primitive.run() supplies its own TResult.
export type ActionInvoker = <TResult>(invocation: Invocation) => Promise<TResult>;

export function buildInvocation(descriptor: { method: string; path: string }, params: unknown): Invocation {
  return { method: descriptor.method, path: descriptor.path, body: params };
}

// TParams is always one of the generated, closed Params interfaces (no index
// signature), so it is never structurally assignable to ResolveItem.params
// (Record<string, unknown>) without a cast -- see engine.ts/types.ts. Written once
// here, not re-templated per endpoint by the generator.
export function makeGatePrimitive<TParams>(engine: AoaEngine, operation: string): GatePrimitive<TParams> {
  return {
    async verdict(params: TParams): Promise<Verdict> {
      const [item] = await engine.resolve([{ operation, params: params as Record<string, unknown> }]);
      return item;
    },
    async can(params: TParams): Promise<boolean> {
      const [item] = await engine.resolve([{ operation, params: params as Record<string, unknown> }]);
      if (item.kind === "FailErrorVerdict") throw new AoaResolveError(item.reason);
      return item.kind === "AllowedVerdict";
    },
  };
}

export function makeCallablePrimitive<TParams, TResult>(
  engine: AoaEngine,
  operation: string,
  descriptor: { method: string; path: string },
  actionInvoker: ActionInvoker,
): CallablePrimitive<TParams, TResult> {
  return {
    ...makeGatePrimitive<TParams>(engine, operation),
    // Precheck (chapter 5.5): a fresh, non-cached can() right before the real call --
    // skipCache is mandatory here, a cache hit would defeat the whole point of asking
    // again right before invoking. The caller doesn't need to know this check even
    // happened: a denial here throws the same plain shape .can()/.verdict() callers
    // would recognize, not a dedicated "precheck" error class.
    async run(params: TParams): Promise<TResult> {
      const [item] = await engine.resolve([{ operation, params: params as Record<string, unknown> }], {
        skipCache: true,
      });
      if (item.kind === "FailErrorVerdict") throw new AoaResolveError(item.reason);
      if (item.kind === "FailSecurityVerdict") throw new Error(`action not allowed: ${item.reason}`);
      return actionInvoker<TResult>(buildInvocation(descriptor, params));
    },
  };
}
