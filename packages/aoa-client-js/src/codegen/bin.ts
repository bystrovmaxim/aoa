#!/usr/bin/env node
// packages/aoa-client-js/src/codegen/bin.ts
//
// aoa-codegen --url <manifest> --out <path> -- thin CLI wrapper over generateClient.
// No generation logic of its own: it only parses these flags and writes (or, with
// --check, compares) whatever generateClient returns, so the CLI's output and
// generateClient's output are identical by construction -- there is no second generator
// here to drift from the first.
//
// --check (recommended CI default for a committed generated file): instead of writing
// --out, reads its current content and diffs it against a fresh generateClient(--url)
// call -- catching schema drift (an endpoint stayed but a field was renamed) before
// deploy, not just the route-set drift the runtime itself already surfaces.

import { readFile, writeFile } from "node:fs/promises";
import { pathToFileURL } from "node:url";

import { diffGeneratedSource } from "./check-drift.ts";
import { generateClient } from "./generate-client.ts";

export interface CliArgs {
  url: string;
  out: string;
  check: boolean;
}

export function parseArgs(argv: string[]): CliArgs {
  let url: string | undefined;
  let out: string | undefined;
  let check = false;
  for (let i = 0; i < argv.length; i += 1) {
    const arg = argv[i];
    if (arg === "--url") {
      url = argv[i + 1];
      i += 1;
    } else if (arg === "--out") {
      out = argv[i + 1];
      i += 1;
    } else if (arg === "--check") {
      check = true;
    } else {
      throw new Error(`Unknown argument: ${arg}`);
    }
  }
  if (!url) throw new Error("Missing required --url <manifest-url>");
  if (!out) throw new Error("Missing required --out <path>");
  return { url, out, check };
}

export async function main(argv: string[]): Promise<void> {
  const args = parseArgs(argv);
  const source = await generateClient(args.url);
  if (args.check) {
    await runCheck(args.out, source);
    return;
  }
  await writeFile(args.out, source, "utf8");
  console.log(`aoa-codegen: wrote ${args.out} from ${args.url}`);
}

async function runCheck(outPath: string, freshSource: string): Promise<void> {
  let committedSource: string;
  try {
    committedSource = await readFile(outPath, "utf8");
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") {
      throw new Error(`${outPath} does not exist -- run aoa-codegen --url <manifest> --out ${outPath} to create it`);
    }
    throw error;
  }
  const drift = diffGeneratedSource(committedSource, freshSource);
  if (drift === null) {
    console.log(`aoa-codegen --check: ${outPath} is up to date`);
    return;
  }
  throw new Error(`${outPath} is out of date:\n${drift}`);
}

const isMainModule = process.argv[1] !== undefined && import.meta.url === pathToFileURL(process.argv[1]).href;
if (isMainModule) {
  main(process.argv.slice(2)).catch((error: unknown) => {
    console.error(`aoa-codegen: ${error instanceof Error ? error.message : String(error)}`);
    process.exitCode = 1;
  });
}
