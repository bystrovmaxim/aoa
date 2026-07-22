// examples/step_27_ui_permissions_client/04_engine_with_fake_fetch_for_tests.ts
//
// The pattern this whole book relies on for testing anything that talks to
// AoaEngine: fetchImpl is a constructor parameter, not window.fetch read off
// the global. That's dependency injection -- swap in a fake, and a component
// test never needs a real server. This is the same shape as engine.test.ts's
// own readiness tests (packages/aoa-client-js/src/engine.test.ts); shown here
// standalone because a reader building their own app will want this pattern
// immediately, not after finding it buried in the package's own test suite.
import { AoaEngine } from "../../packages/aoa-client-js/src/index.ts";
import type { ResolveResponse } from "../../packages/aoa-client-js/src/types.ts";

// A tiny fake: always answers AllowedVerdict, and records what it was asked.
function fakeFetchThatAlwaysAllows(callLog: string[]): typeof fetch {
  return async (_url, init) => {
    const body = JSON.parse((init as RequestInit).body as string);
    callLog.push(body.items[0].operation);
    const response: ResolveResponse = { version: 1, results: body.items.map(() => ({ kind: "AllowedVerdict" })) };
    return new Response(JSON.stringify(response), { headers: { "content-type": "application/json" } });
  };
}

// The function under test -- an ordinary component-level helper, no
// awareness that fetchImpl is fake in this run.
async function checkCanCancel(engine: AoaEngine, orderId: number): Promise<boolean> {
  const [result] = await engine.resolve([{ operation: "POST /actions/cancel-order", params: { order_id: orderId } }]);
  return result.kind === "AllowedVerdict";
}

// "Test" body: no real server, no real network -- just the fake above.
const callLog: string[] = [];
const engine = new AoaEngine({
  transport: { baseUrl: "https://example.test", fetchImpl: fakeFetchThatAlwaysAllows(callLog), cachePartition: "user:42" },
});

const canCancel = await checkCanCancel(engine, 7);
console.assert(canCancel === true, "expected checkCanCancel to resolve true");
console.assert(callLog.length === 1 && callLog[0] === "POST /actions/cancel-order", "expected exactly one recorded call");
console.log(`checkCanCancel(7) === ${canCancel}; fake fetchImpl recorded: ${JSON.stringify(callLog)}`);
