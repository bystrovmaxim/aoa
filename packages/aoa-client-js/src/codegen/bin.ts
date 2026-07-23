#!/usr/bin/env node
// packages/aoa-client-js/src/codegen/bin.ts
//
// aoa-codegen --url <manifest> --out <path> -- thin CLI wrapper over generateClient.
// No generation logic of its own: it only parses these two flags and writes whatever
// generateClient returns, so the CLI's output and generateClient's output are identical
// by construction -- there is no second generator here to drift from the first.

import { writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { generateClient } from "./generate-client.ts";

export interface CliArgs {
  url: string;
  out: string;
}

export function parseArgs(argv: string[]): CliArgs {
  let url: string | undefined;
  let out: string | undefined;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--url") {
      url = argv[i + 1];
      i += 1;
    } else if (arg === "--out") {
      out = argv[i + 1];
      i += 1;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!url) throw new Error("Missing required --url <manifest-url>");
  if (!out) throw new Error("Missing required --out <path>");
  return { url, out };
}

export async function main(argv: string[]): Promise<void> {
  const { url, out } = parseArgs(argv);
  const source = await generateClient(url);
  await writeFile(out, source, "utf8");
  console.log(`aoa-codegen: wrote ${out} from ${url}`);
}

const isMainModule = process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMainModule) {
  main(process.argv.slice(2)).catch((error: unknown) => {
    console.error(`aoa-codegen: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  });
}
