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
 *
 * It then proves SC-003 in a real room: in each engine a desktop page opens a room on the ERD of all
 * domains and a phone page joins it. The desktop's mouse rests on a node's centre, and the phone must
 * draw that arrow within 2 px of the same node's centre on its own screen, before and after either
 * page zooms. A phone has no cursor, only touches: its tap on a node must show on the desktop as a
 * ring centred on the same node, within the same 2 px.
 */
import { spawn } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import { readFileSync } from "node:fs";
import { createServer, request as httpRequest } from "node:http";
import { connect } from "node:net";
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
/** The largest distance between a pointer and the point it marks on another screen (SC-003). */
const POINTER_TOLERANCE_PX = 2;
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
  // Room connections pass through untouched, with the page's own Host, as the stand's nginx does.
  server.on("upgrade", (req: IncomingMessage, socket, head: Buffer) => {
    const upstream = connect(apiPort(), "127.0.0.1", () => {
      const headers = Object.entries(req.headers).flatMap(([name, value]) =>
        (Array.isArray(value) ? value : [value]).map((v) => `${name}: ${v}`),
      );
      upstream.write(`${req.method} ${req.url} HTTP/1.1\r\n${headers.join("\r\n")}\r\n\r\n`);
      upstream.write(head);
      upstream.pipe(socket);
      socket.pipe(upstream);
    });
    upstream.on("error", () => socket.destroy());
    socket.on("error", () => upstream.destroy());
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

/** Enter a name in the room dialog and confirm it. */
async function confirmName(page: Page, name: string): Promise<void> {
  await page.locator("#room-name-input").fill(name);
  await domClick(page, 'form button[type="submit"]');
}

/** The client centre of the ``index``-th Graphviz node of the diagram on screen. */
async function nodeCentre(page: Page, index: number): Promise<{ x: number; y: number }> {
  return page.evaluate((i) => {
    const box = document.querySelectorAll("[data-layout-hash] svg g.node")[i].getBoundingClientRect();
    return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
  }, index);
}

/** The node nearest the middle of the diagram's element, so it stays in view when zooming in. */
async function middleNode(page: Page): Promise<number> {
  return page.evaluate(() => {
    const view = document.querySelector("[data-layout-hash]")!.getBoundingClientRect();
    const mx = view.left + view.width / 2;
    const my = view.top + view.height / 2;
    let best = 0;
    let bestDistance = Infinity;
    document.querySelectorAll("[data-layout-hash] svg g.node").forEach((node, i) => {
      const box = node.getBoundingClientRect();
      const d = Math.hypot(box.left + box.width / 2 - mx, box.top + box.height / 2 - my);
      if (d < bestDistance) [best, bestDistance] = [i, d];
    });
    return best;
  });
}

/** The client point a drawn pointer marks: an arrow's tip, 2 px inside its box, or a ring's centre. */
async function markedPoint(watcher: Page, participant: string, kind: "mouse" | "touch") {
  return watcher.evaluate(
    ([id, k]) => {
      const box = document.querySelector(`[data-participant="${id}"]`)?.getBoundingClientRect();
      if (!box) return null;
      return k === "touch" ? { x: box.left + box.width / 2, y: box.top + box.height / 2 } : { x: box.left + 2, y: box.top + 2 };
    },
    [participant, kind] as const,
  );
}

/** How far ``watcher`` draws ``participant``'s pointer from the centre of node ``index``, once it settles. */
async function pointerOffset(watcher: Page, participant: string, index: number, kind: "mouse" | "touch" = "mouse"): Promise<number> {
  let last = Infinity;
  for (let attempt = 0; attempt < 20; attempt += 1) {
    await watcher.waitForTimeout(kind === "touch" ? 100 : 250);
    const tip = await markedPoint(watcher, participant, kind);
    if (!tip) continue;
    const centre = await nodeCentre(watcher, index);
    const offset = Math.hypot(tip.x - centre.x, tip.y - centre.y);
    if (Math.abs(offset - last) < 0.01) return offset;
    last = offset;
  }
  return last;
}

/** Zoom a page in twice with its own zoom button. */
async function zoomIn(page: Page): Promise<void> {
  for (let i = 0; i < 2; i += 1) {
    await page.locator("button", { hasText: /^\+$/ }).first().evaluate((button) => (button as HTMLElement).click());
    await page.waitForTimeout(300);
  }
}

/** SC-003 in one engine: the largest offset of a desktop's arrow on the phone, and of a phone's tap on the desktop. */
async function pointerCase(engine: BrowserType, front: string, source: string): Promise<number[]> {
  const browser: Browser = await engine.launch();
  try {
    // Two contexts: two browsers, two participants.
    const desk = await (await browser.newContext({ viewport: { width: 1600, height: 900 } })).newPage();
    const phone = await (await browser.newContext({ viewport: { width: 375, height: 812 }, hasTouch: true })).newPage();
    await desk.goto(`${front}/?${new URLSearchParams({ source, view: "domain-erd" }).toString()}`);
    await nextHash(desk, null);
    await domClick(desk, 'button:has-text("Open room")');
    await confirmName(desk, "Desk");
    await desk.waitForURL(/room=/, { timeout: HASH_TIMEOUT_MS });
    // The invite card greets a new room; its backdrop would take the mouse.
    await desk.locator(".MuiPopover-paper").waitFor({ timeout: HASH_TIMEOUT_MS });
    await desk.keyboard.press("Escape");
    await desk.locator(".MuiPopover-paper").waitFor({ state: "detached", timeout: HASH_TIMEOUT_MS });
    const deskId = await desk.evaluate(() => {
      const room = new URL(window.location.href).searchParams.get("room");
      return window.localStorage.getItem(`maxitor.room.${room}.participant`);
    });
    await phone.goto(desk.url());
    await confirmName(phone, "Phone");
    await nextHash(phone, null);
    await desk.locator('[aria-label^="Phone"]').first().waitFor({ timeout: HASH_TIMEOUT_MS });
    await desk.waitForTimeout(1000);

    const node = await middleNode(phone);
    const offsets: number[] = [];
    const point = async () => {
      const centre = await nodeCentre(desk, node);
      await desk.mouse.move(centre.x + 1, centre.y);
      await desk.mouse.move(centre.x, centre.y);
      offsets.push(await pointerOffset(phone, deskId ?? "", node));
    };
    await point();
    await zoomIn(phone);
    offsets.push(await pointerOffset(phone, deskId ?? "", node));
    await zoomIn(desk);
    await point();

    // The other way: the phone touches the node, the desktop shows the ring there.
    const phoneId = await phone.evaluate(() => {
      const room = new URL(window.location.href).searchParams.get("room");
      return window.localStorage.getItem(`maxitor.room.${room}.participant`);
    });
    // A phone opens with the left panel over the diagram; close it as a person would.
    await phone.keyboard.press("Escape");
    await phone.locator(".MuiDrawer-root .MuiPaper-root").first().waitFor({ state: "hidden", timeout: HASH_TIMEOUT_MS });
    const touched = await nodeCentre(phone, node);
    await phone.touchscreen.tap(touched.x, touched.y);
    offsets.push(await pointerOffset(desk, phoneId ?? "", node, "touch"));
    return offsets;
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
    const offsets = await Promise.all(ENGINES.map(([, engine]) => pointerCase(engine, frontUrl, source)));
    // Steps: arrow; arrow after the phone zooms; arrow after the desktop zooms; the phone's tap.
    ENGINES.forEach(([name], i) => {
      const largest = Math.max(...offsets[i]);
      const fits = largest <= POINTER_TOLERANCE_PX;
      ok &&= fits;
      const steps = offsets[i].map((o) => o.toFixed(3)).join(" / ");
      console.log(`${fits ? "ok  " : "DIFF"}  pointer in a room | ${name}  largest offset ${largest.toFixed(3)} px (${steps})`);
    });
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
