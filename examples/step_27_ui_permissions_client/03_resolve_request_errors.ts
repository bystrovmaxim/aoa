// examples/step_27_ui_permissions_client/03_resolve_request_errors.ts
//
// Two different kinds of "something went wrong", handled two different ways.
//
// 1. Request-level failures (network down, 401) never reach `results` at
//    all -- AoaEngine throws a typed error instead. A transport failure must
//    never be misread as "no permission".
// 2. A FailErrorVerdict INSIDE `results` is a per-question failure: the
//    resolver answered the HTTP request just fine, but couldn't check this
//    one particular question. It's not a denial either -- isRetryableCheckError
//    is how a caller decides whether asking again is worth it.
import { AoaEngine, NetworkUnavailable, Unauthorized, isRetryableCheckError } from "../../packages/aoa-client-js/src/index.ts";
import type { ResolveResponse } from "../../packages/aoa-client-js/src/types.ts";

function engineWith(fetchImpl: typeof fetch): AoaEngine {
  return new AoaEngine({
    transport: { baseUrl: "https://example.test", fetchImpl, cachePartition: "user:42" },
  });
}

const items = [{ operation: "POST /actions/cancel-order", params: { order_id: 7 } }];

// -- Network down: fetch itself throws.
try {
  const down = engineWith(async () => {
    throw new Error("getaddrinfo ENOTFOUND");
  });
  await down.resolve(items);
} catch (err) {
  console.log(`network down -> threw NetworkUnavailable: ${err instanceof NetworkUnavailable}`);
}

// -- 401: the caller isn't authenticated at all.
try {
  const unauthorized = engineWith(async () => new Response(null, { status: 401 }));
  await unauthorized.resolve(items);
} catch (err) {
  console.log(`401 -> threw Unauthorized: ${err instanceof Unauthorized}`);
}

// -- FailErrorVerdict inside a normal 200 response: the resolver ran fine,
//    but this one question couldn't be checked (e.g. a timing out dependency).
const withCheckError = engineWith(async () => {
  const response: ResolveResponse = { version: 1, results: [{ kind: "FailErrorVerdict", reason: "TIMEOUT" }] };
  return new Response(JSON.stringify(response), { headers: { "content-type": "application/json" } });
});
const [result] = await withCheckError.resolve(items);
if (result.kind === "FailErrorVerdict") {
  console.log(`check failed with reason=${result.reason}, retryable=${isRetryableCheckError(result.reason)}`);
}
