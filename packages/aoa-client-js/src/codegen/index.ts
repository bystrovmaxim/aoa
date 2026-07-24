// packages/aoa-client-js/src/codegen/index.ts
//
// Public surface of the `aoa-client-js/codegen` entry point — separate from the runtime
// entry (`aoa-client-js`) so a plain app bundle never pulls in the generator.

export { generateClient } from "./generate-client.ts";
