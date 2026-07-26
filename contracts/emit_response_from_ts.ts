// contracts/emit_response_from_ts.ts
//
// The TypeScript half of the two-way contract check (chapter 12, #144).
//
// The fixtures in ./fixtures/ only ever travel Python -> TypeScript: each valid one
// is asserted byte-equivalent to what the pydantic model itself would emit
// (test_resolve_contract.py's round-trip test), and the TypeScript half then parses
// it. Nothing ever went the other way, so a response shaped the way TYPESCRIPT
// believes it should be shaped was never handed to pydantic.
//
// This script closes that direction: it builds a response out of the TypeScript
// types -- not by copying a fixture, but by constructing `Verdict` values whose
// shape the TS compiler enforces -- and prints it as JSON on stdout.
// test_resolve_contract.py spawns this file and feeds that stdout to
// ResolveResponse. If the two sides ever disagree about the shape, the Python half
// rejects TypeScript's own idea of a valid response and says so.
//
// Deliberately imports the hand-maintained types rather than the generated zod
// schema: the generated schema needs a live manifest fetch, and pulling that into a
// pytest run would make the bridge test depend on the codegen pipeline as well as
// on the shape it is supposed to be checking.
//
// Run: node --experimental-strip-types contracts/emit_response_from_ts.ts

import type { ResolveResponse, Verdict } from "../packages/aoa-client-js/src/types.ts";

// One of each outcome class, so a shape disagreement about ANY of the three is
// caught rather than only whichever one happened to be first.
const results: Verdict[] = [
  { kind: "AllowedVerdict" },
  { kind: "FailSecurityVerdict", reason: "FORBIDDEN_OBJECT" },
  { kind: "FailErrorVerdict", reason: "EVALUATION_FAILED" },
];

const response: ResolveResponse = { version: 1, results };

process.stdout.write(JSON.stringify(response));
