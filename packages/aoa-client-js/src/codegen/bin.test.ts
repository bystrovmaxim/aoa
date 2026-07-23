// packages/aoa-client-js/src/codegen/bin.test.ts
import { execFile } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { createServer, type Server } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { promisify } from "node:util";
import { afterEach, describe, expect, it } from "vitest";

import { generateClient } from "./generate-client.ts";
import { parseArgs } from "./bin.ts";

const execFileAsync = promisify(execFile);

describe("parseArgs", () => {
  it("parses --url and --out in order", () => {
    expect(parseArgs(["--url", "https://x/client-manifest.json", "--out", "src/generated/aoa-client.ts"])).toEqual({
      url: "https://x/client-manifest.json",
      out: "src/generated/aoa-client.ts",
    });
  });

  it("parses --out before --url just as well", () => {
    expect(parseArgs(["--out", "out.ts", "--url", "https://x/m.json"])).toEqual({ url: "https://x/m.json", out: "out.ts" });
  });

  it("throws a clear error when --url is missing", () => {
    expect(() => parseArgs(["--out", "out.ts"])).toThrow(/Missing required --url/);
  });

  it("throws a clear error when --out is missing", () => {
    expect(() => parseArgs(["--url", "https://x/m.json"])).toThrow(/Missing required --out/);
  });

  it("throws on an unrecognized argument", () => {
    expect(() => parseArgs(["--url", "https://x/m.json", "--out", "out.ts", "--verbose"])).toThrow(/Unknown argument: --verbose/);
  });
});

describe("aoa-codegen CLI (real subprocess)", () => {
  const binPath = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "bin.ts");
  let server: Server | undefined;
  let tmpDir: string | undefined;

  afterEach(async () => {
    if (server) await new Promise((resolve) => server!.close(resolve));
    server = undefined;
    if (tmpDir) rmSync(tmpDir, { recursive: true, force: true });
    tmpDir = undefined;
  });

  // execFile (async), not execFileSync: the local manifest server below runs in THIS
  // same process, and a synchronous spawn would freeze this process's own event loop
  // while waiting for the child -- which would starve the very server the child is
  // trying to reach, deadlocking both sides. Async keeps this process's event loop free
  // to accept and answer the child's request while node awaits the child's exit.
  function runCli(args: string[]): Promise<{ stdout: string; stderr: string; code: number }> {
    return execFileAsync("node", [binPath, ...args]).then(
      ({ stdout, stderr }) => ({ stdout, stderr, code: 0 }),
      (error: NodeJS.ErrnoException & { stdout?: string; stderr?: string; code?: number }) => ({
        stdout: error.stdout ?? "",
        stderr: error.stderr ?? "",
        code: typeof error.code === "number" ? error.code : 1,
      }),
    );
  }

  function startManifestServer(manifest: unknown): Promise<string> {
    return new Promise((resolve) => {
      server = createServer((_req, res) => {
        res.setHeader("content-type", "application/json");
        res.end(JSON.stringify(manifest));
      });
      server.listen(0, "127.0.0.1", () => {
        const address = server!.address();
        const port = typeof address === "object" && address ? address.port : 0;
        resolve(`http://127.0.0.1:${port}/client-manifest.json`);
      });
    });
  }

  const FAKE_MANIFEST = {
    manifest_version: "sha256:abc",
    version: 1,
    manifest_schema_version: 2,
    endpoints: [
      {
        operation: "GET /orders",
        name: "ListOrdersAction",
        domain: "OrdersDomain",
        description: "List orders",
        route: { method: "GET", path: "/orders" },
        params_schema: { type: "object", properties: {} },
        result_schema: { type: "object", properties: { count: { type: "integer" } }, required: ["count"] },
      },
    ],
    schemas: {
      ResolveResponse: {
        mode: "serialization",
        json_schema: {
          $defs: { BaseVerdict: { properties: { kind: { type: "string" } }, type: "object" } },
          properties: { version: { type: "integer" }, results: { items: { $ref: "#/$defs/BaseVerdict" }, type: "array" } },
          required: ["version", "results"],
          type: "object",
        },
      },
    },
  };

  it("writes a file whose content is byte-for-byte identical to calling generateClient(url) directly", async () => {
    const url = await startManifestServer(FAKE_MANIFEST);
    tmpDir = mkdtempSync(path.join(tmpdir(), "aoa-codegen-cli-"));
    const outPath = path.join(tmpDir, "generated.ts");

    const { code } = await runCli(["--url", url, "--out", outPath]);
    expect(code).toBe(0);

    const expected = await generateClient(url);
    expect(readFileSync(outPath, "utf8")).toBe(expected);
  });

  it("prints a confirmation message naming the written file and the source url", async () => {
    const url = await startManifestServer(FAKE_MANIFEST);
    tmpDir = mkdtempSync(path.join(tmpdir(), "aoa-codegen-cli-"));
    const outPath = path.join(tmpDir, "generated.ts");

    const { stdout } = await runCli(["--url", url, "--out", outPath]);
    expect(stdout).toContain(outPath);
    expect(stdout).toContain(url);
  });

  it("exits non-zero and writes no file when a required flag is missing", async () => {
    tmpDir = mkdtempSync(path.join(tmpdir(), "aoa-codegen-cli-"));
    const outPath = path.join(tmpDir, "generated.ts");

    const { code, stderr } = await runCli(["--out", outPath]);
    expect(code).not.toBe(0);
    expect(stderr).toContain("Missing required --url");
    expect(existsSync(outPath)).toBe(false);
  });

  it("exits non-zero with a clear stderr message when the manifest server refuses the connection", async () => {
    tmpDir = mkdtempSync(path.join(tmpdir(), "aoa-codegen-cli-"));
    const outPath = path.join(tmpDir, "generated.ts");
    // Bind-and-immediately-close to get a real, guaranteed-refusing port on this host,
    // rather than a hardcoded port number that may or may not be free/reachable.
    const deadPort = await new Promise<number>((resolve) => {
      const probe = createServer();
      probe.listen(0, "127.0.0.1", () => {
        const address = probe.address();
        const port = typeof address === "object" && address ? address.port : 0;
        probe.close(() => resolve(port));
      });
    });

    const { code, stderr } = await runCli(["--url", `http://127.0.0.1:${deadPort}/client-manifest.json`, "--out", outPath]);
    expect(code).not.toBe(0);
    expect(stderr).toContain("aoa-codegen:");
    expect(existsSync(outPath)).toBe(false);
  });
});
