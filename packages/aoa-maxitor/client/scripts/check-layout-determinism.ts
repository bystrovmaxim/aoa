// packages/aoa-maxitor/client/scripts/check-layout-determinism.ts
/**
 * check-layout-determinism — prove that every diagram is laid out to the same bits in Chromium,
 * Firefox and WebKit, on a phone-sized and a desktop-sized screen (spec 028, FR-006).
 *
 * The check run runs it after the client's build. It serves the built client and the frozen
 * reference graph, proxies the API to a real Maxitor started for the purpose, opens every page
 * the left panel lists — the full graph, every ERD, every use-case diagram, every lifecycle —
 * in every layout mode of that page, and reads the layout hash each viewer writes on its diagram
 * element (`data-layout-hash`, contracts/layout-determinism.md). One line is printed per page
 * and mode; the exit code is 1 as soon as one page and mode has two different hashes, or none.
 *
 * Nothing is added to the client for it: the hash on the element is the one the room reads.
 */
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { readFileSync } from "node:fs";
import { createServer, request as httpRequest } from "node:http";
import type { IncomingMessage, Server, ServerResponse } from "node:http";
import type { AddressInfo } from "node:net";
import { extname, join, resolve } from "node:path";
import { gunzipSync } from "node:zlib";

import { chromium, firefox, webkit } from "playwright";
import type { Browser, BrowserType, Page } from "playwright";

const CLIENT = process.cwd();
const REPO = resolve(CLIENT, "../../..");
const DIST = join(CLIENT, "dist");
const FIXTURE = join(REPO, "packages/aoa-maxitor/tests/fixtures/ref-graph-2026-10-26.json.gz");

const ENGINES: [string, BrowserType][] = [
  ["chromium", chromium],
  ["firefox", firefox],
  ["webkit", webkit],
];
const VIEWPORTS: { name: string; width: number; height: number }[] = [
  { name: "375x812", width: 375, height: 812 },
  { name: "1600x900", width: 1600, height: 900 },
];
const HASH_TIMEOUT_MS = 60_000;
const API_START_TIMEOUT_MS = 60_000;

const CONTENT_TYPES: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".wasm": "application/wasm",
  ".svg": "image/svg+xml",
  ".png": "image/png",
  ".json": "application/json",
};

/** One diagram page as the address names it. */
type Target = { label: string; query: Record<string, string> };

/** A sidebar row, as `GET /api/sidebar` returns it. */
type SidebarRow = { id: string; parent_id: string | null; label: string; type: string };

/** Serve the built client and the reference graph, and pass `/api` on to Maxitor. */
function startFrontServer(graphJson: Buffer, apiPort: () => number): Promise<Server> {
  const server = createServer((req: IncomingMessage, res: ServerResponse) => {
    const url = new URL(req.url ?? "/", "http://localhost");
    if (url.pathname === "/graph-json") {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(graphJson);
      return;
    }
    if (url.pathname.startsWith("/api/")) {
      const upstream = httpRequest(
        { host: "127.0.0.1", port: apiPort(), path: req.url, method: req.method, headers: req.headers },
        (answer) => {
          res.writeHead(answer.statusCode ?? 502, answer.headers);
          answer.pipe(res);
        },
      );
      upstream.on("error", (error) => {
        res.writeHead(502);
        res.end(String(error));
      });
      req.pipe(upstream);
      return;
    }
    const file = url.pathname === "/" ? "index.html" : url.pathname.slice(1);
    let body: Buffer;
    try {
      body = readFileSync(join(DIST, file));
    } catch {
      body = readFileSync(join(DIST, "index.html"));
    }
    res.writeHead(200, { "Content-Type": CONTENT_TYPES[extname(file)] ?? "application/octet-stream" });
    res.end(body);
  });
  return new Promise((done) => server.listen(0, "127.0.0.1", () => done(server)));
}

/** A free TCP port on the loopback interface. */
async function freePort(): Promise<number> {
  const probe = createServer();
  await new Promise<void>((done) => probe.listen(0, "127.0.0.1", () => done()));
  const { port } = probe.address() as AddressInfo;
  await new Promise<void>((done) => probe.close(() => done()));
  return port;
}

/** Start Maxitor's API with the repository's environment and wait until it answers. */
async function startApi(port: number): Promise<ChildProcess> {
  const child = spawn(
    "uv",
    ["run", "--extra", "dev", "uvicorn", "aoa.maxitor.api.app:app", "--host", "127.0.0.1", "--port", String(port)],
    { cwd: REPO, stdio: ["ignore", "ignore", "pipe"] },
  );
  let stderr = "";
  child.stderr?.on("data", (chunk: Buffer) => {
    stderr += chunk.toString();
  });
  const deadline = Date.now() + API_START_TIMEOUT_MS;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) throw new Error(`Maxitor exited early:\n${stderr}`);
    try {
      const answer = await fetch(`http://127.0.0.1:${port}/api/health`);
      if (answer.ok) return child;
    } catch {
      /* not listening yet */
    }
    await new Promise((done) => setTimeout(done, 250));
  }
  child.kill();
  throw new Error(`Maxitor did not answer within ${API_START_TIMEOUT_MS} ms:\n${stderr}`);
}

/** Every diagram page the left panel lists for the source, in the panel's order. */
async function listTargets(front: string, source: string): Promise<Target[]> {
  const answer = await fetch(`${front}/api/sidebar?source=${encodeURIComponent(source)}`);
  if (!answer.ok) throw new Error(`the sidebar answered ${answer.status}`);
  const sidebar = (await answer.json()) as Record<string, SidebarRow[]>;
  const rows = [...(sidebar.level2_diagrams ?? []), ...(sidebar.level3_diagrams ?? [])];
  const targets: Target[] = [];
  for (const row of rows) {
    if (row.type === "graph") targets.push({ label: "full graph", query: { view: "full-graph" } });
    else if (row.type === "erd_all") targets.push({ label: "ERD, all domains", query: { view: "domain-erd" } });
    else if (row.type === "erd_domain" && row.parent_id)
      targets.push({ label: `ERD ${row.parent_id}`, query: { view: "domain-erd", domain: row.parent_id } });
    else if (row.type === "use_case_domain" && row.parent_id)
      targets.push({ label: `use case ${row.parent_id}`, query: { view: "use-case", domain: row.parent_id } });
    else if (row.type === "lifecycle_state_diagram" && row.parent_id)
      targets.push({
        label: `lifecycle ${row.id}`,
        query: { view: "lifecycle-fsm", node: row.id, host: row.parent_id },
      });
  }
  return targets;
}

/** Wait until the diagram carries a layout hash other than ``previous``, and return it. */
async function nextHash(page: Page, previous: string | null): Promise<string> {
  const handle = await page.waitForFunction(
    (before) => {
      const hash = document.querySelector("[data-layout-hash]")?.getAttribute("data-layout-hash");
      return hash && hash !== before ? hash : null;
    },
    previous,
    { timeout: HASH_TIMEOUT_MS, polling: 100 },
  );
  return (await handle.jsonValue()) as string;
}

/** Click an element through the DOM: on a phone the open left panel covers the toolbar. */
async function domClick(page: Page, selector: string): Promise<void> {
  await page.locator(selector).first().evaluate((element) => {
    (element as HTMLElement).click();
  });
}

/** The hash of every layout mode on screen, by mode value ("default" when there is none). */
async function hashesOfModes(page: Page, current: string, suffix: string): Promise<Record<string, string>> {
  let hash = current;
  const buttons = page.locator('[aria-label="View controls"] button[value]');
  const values = await buttons.evaluateAll((elements) => elements.map((element) => element.getAttribute("value") ?? ""));
  if (values.length === 0) return { [`default${suffix}`]: hash };
  const pressed = await buttons.evaluateAll((elements) =>
    elements.findIndex((element) => element.getAttribute("aria-pressed") === "true"),
  );
  const result: Record<string, string> = {};
  if (pressed >= 0) result[`${values[pressed]}${suffix}`] = hash;
  for (const value of values) {
    if (`${value}${suffix}` in result) continue;
    await domClick(page, `[aria-label="View controls"] button[value="${value}"]`);
    hash = await nextHash(page, hash);
    result[`${value}${suffix}`] = hash;
  }
  return result;
}

/**
 * The hash of every layout mode of one page. A use-case diagram offers Neato and FDP only with
 * its Boundary switched off, so those pages are walked a second time that way.
 */
async function hashesOfPage(page: Page, url: string): Promise<Record<string, string>> {
  await page.goto(url);
  const first = await nextHash(page, null);
  const result = await hashesOfModes(page, first, "");
  const boundary = page.locator('label:has-text("Boundary") input[type="checkbox"]');
  if ((await boundary.count()) > 0 && (await boundary.first().isChecked())) {
    const last = (await page.locator("[data-layout-hash]").getAttribute("data-layout-hash")) ?? first;
    await domClick(page, 'label:has-text("Boundary") input[type="checkbox"]');
    Object.assign(result, await hashesOfModes(page, await nextHash(page, last), " · no boundary"));
  }
  return result;
}

/** Lay out every page in one engine at every viewport, keyed "page | mode" → "engine viewport" → hash. */
async function runEngine(
  name: string,
  engine: BrowserType,
  front: string,
  source: string,
  targets: Target[],
  results: Map<string, Map<string, string>>,
): Promise<void> {
  const browser: Browser = await engine.launch();
  try {
    for (const viewport of VIEWPORTS) {
      // A fresh context per viewport: no remembered arrangement, so every full graph is laid out.
      const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
      const page = await context.newPage();
      for (const target of targets) {
        const query = new URLSearchParams({ source, ...target.query });
        const hashes = await hashesOfPage(page, `${front}/?${query.toString()}`);
        for (const [mode, hash] of Object.entries(hashes)) {
          const key = `${target.label} | ${mode}`;
          if (!results.has(key)) results.set(key, new Map());
          results.get(key)!.set(`${name} ${viewport.name}`, hash);
        }
      }
      await context.close();
    }
  } finally {
    await browser.close();
  }
}

/** Check every page and mode; print one line each; return whether all of them agree. */
function report(results: Map<string, Map<string, string>>): boolean {
  const expected = ENGINES.length * VIEWPORTS.length;
  let ok = true;
  for (const [key, byRun] of results) {
    const distinct = new Set(byRun.values());
    if (distinct.size === 1 && byRun.size === expected) {
      console.log(`ok    ${key}  ${[...distinct][0].slice(0, 16)}`);
      continue;
    }
    ok = false;
    console.log(`DIFF  ${key}`);
    for (const [run, hash] of byRun) console.log(`        ${run}: ${hash.slice(0, 16)}`);
    if (byRun.size !== expected) console.log(`        ${expected - byRun.size} run(s) gave no hash`);
  }
  return ok;
}

/** Serve, start Maxitor, lay out everywhere, compare. */
async function main(): Promise<void> {
  const started = Date.now();
  const graphJson = gunzipSync(readFileSync(FIXTURE));
  const apiPort = await freePort();
  const front = await startFrontServer(graphJson, () => apiPort);
  const frontUrl = `http://127.0.0.1:${(front.address() as AddressInfo).port}`;
  const api = await startApi(apiPort);
  let ok = false;
  try {
    const source = `${frontUrl}/graph-json`;
    const targets = await listTargets(frontUrl, source);
    const results = new Map<string, Map<string, string>>();
    await Promise.all(ENGINES.map(([name, engine]) => runEngine(name, engine, frontUrl, source, targets, results)));
    ok = report(results);
    // The pointer case of SC-003 needs rooms; it is added here together with the pointer layer (tasks T079, commit 11).
    console.log("skip  pointers in a room: not built yet (spec 028, commit 11)");
    console.log(
      `${results.size} page-modes × ${ENGINES.length} engines × ${VIEWPORTS.length} sizes in ${Math.round((Date.now() - started) / 1000)} s`,
    );
  } finally {
    api.kill();
    front.close();
  }
  process.exit(ok ? 0 : 1);
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.stack ?? error.message : String(error));
  process.exit(1);
});
