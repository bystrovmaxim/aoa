// packages/maxitor/front/client/scripts/check-layout-determinism.ts
/**
 * check-layout-determinism — prove that every diagram is laid out to the same bits in Chromium,
 * Firefox and WebKit, on a phone-sized and a desktop-sized screen (spec 028, FR-006). The engines,
 * and both screen sizes within each engine, lay out at the same time.
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
 * Beside it, it proves SC-003 in a real room: in each engine a desktop page opens a room on the ERD
 * of all domains and a phone page joins it. The desktop's mouse rests on a node's centre, and the
 * phone must draw that arrow within 2 px of the same node's centre on its own screen, before and
 * after either page zooms. A phone has no cursor, only touches: its tap on a node must show on the
 * desktop as a ring centred on the same node, within the same 2 px.
 *
 * After both, following in every directed pair of engines (spec 029, FR-015), all six pairs at
 * once, each in its own room: one browser opens a room, a browser of another engine joins and
 * follows it. The leader drags the ERD and stops; the follower's screen must then be centred on the
 * leader's diagram point within 2 px. The leader rests the mouse on a table; the follower must
 * light the same table within half a second (SC-002). There, too, the leader's circles must not
 * touch (spec 029, FR-051): its own ring, the count of its follower and a focus ring on the
 * follower's circle all drawn at once. The leader's name is 40 characters, the longest a name may
 * be, and the follower's card for it must keep its buttons inside the card without one running into
 * another (FR-052).
 *
 * Last, following on every kind of diagram (spec 038) — the full graph, the ERD of all domains, one
 * domain's ERD, a use case and a lifecycle — in every directed pair of four browsers: the three
 * engines and the real Safari, driven through `safaridriver` (`browserTab.ts`), since Playwright's
 * WebKit paints in software and never shows what Safari's compositor does to a large drawing. The
 * leader goes to each page and zooms in; the follower must draw the same page, take the same zoom and
 * the same top-left corner within 2 px, and show the diagram on screen: its share of drawn pixels
 * (`pngInk.ts`) at least 60 % of the leader's. Safari runs one session at a time, so its pairs run one
 * after another, with Chromium only, both ways. Safari only paints in a window on screen, so it runs when asked:
 * MAXITOR_CHECK_SAFARI=1 adds it here, =full to every change in one frame too; asked for, it must be drivable —
 * Develop → "Allow remote automation" — and its window uncovered. Not asked for, a line says it was skipped.
 *
 * Then every change of the picture in one frame (spec 038): in a room, on the ERD of all domains and on a
 * use case, the leader turns a domain off and on, paints by kinds and by domains, changes the layout mode,
 * turns 1-hop off and on, and the use case's direction and boundary. Each browser records, frame by frame,
 * what its diagram shows — the drawing and the camera. After each change the leader and the follower must
 * each show at most one new picture, the follower one whenever the leader does — no blank, no new drawing at
 * an old view, no fit to its own screen and then a glide — and the follower must never be told its pointers
 * are off.
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

import { playwrightTab, safariTab, safariUnavailable, waitInPage } from "./browserTab.ts";
import { cardMechanics, type CardCase } from "./cardMechanics.ts";
import type { BrowserTab } from "./browserTab.ts";
import { decodePng, inkOf } from "./pngInk.ts";

const CLIENT = process.cwd();
const REPO = resolve(CLIENT, "../../../..");
const DIST = join(CLIENT, "dist");
const FIXTURE = join(REPO, "packages/maxitor/front/tests/fixtures/ref-graph-2026-10-26.json.gz");

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
/** How soon a follower must show the leader's hover (spec 029, SC-002). */
const FOLLOW_HOVER_MS = 500;
/** The least share of the leader's drawn pixels a follower must show on the same diagram (spec 038). */
const FOLLOW_INK_SHARE = 0.6;
/** A leader's screen with less ink than this has nothing to compare: an empty diagram. */
const EMPTY_INK = 0.002;
/** How much a follower's zoom may differ from its leader's, as a share. */
const ZOOM_TOLERANCE = 0.002;
/** Time for a camera to settle and be written to the address (the client waits 250 ms). */
const SETTLE_MS = 1500;
/** How a value that must have stopped moving is read: this far apart, at most so many times. */
const HASH_STABLE_MS = 250;
const HASH_STABLE_READS = 8;
const CAMERA_REST_READS = 40;

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
    ["run", "--extra", "dev", "uvicorn", "maxitor.front.api.app:app", "--host", "127.0.0.1", "--port", String(port)],
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
    else if (row.type === "erd_all") {
      targets.push({ label: "ERD, all domains", query: { view: "domain-erd" } });
      // Collapsing changes the tables' sizes, so it is laid out again and must agree too (spec 043, FR-030).
      targets.push({ label: "ERD, all domains, collapsed", query: { view: "domain-erd", collapsed: "1" } });
    }
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
  // A hash read while a drawing is being replaced may be a passing one: the one that stays is the page's.
  let settled = (await handle.jsonValue()) as string;
  for (let reads = 0; reads < HASH_STABLE_READS; reads += 1) {
    await page.waitForTimeout(HASH_STABLE_MS);
    const now = await page.evaluate(() => document.querySelector("[data-layout-hash]")?.getAttribute("data-layout-hash") ?? null);
    if (now === settled) return settled;
    if (now) settled = now;
  }
  return settled;
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

/** The name of one engine's run at one viewport, as the report shows it: "firefox 1600x900". */
function runName(engine: string, viewport: { name: string }): string {
  return `${engine} ${viewport.name}`;
}

/**
 * Lay out every page in one engine at every viewport — both viewports at once, each in its own
 * fresh context — keyed "page | mode" → run → hash. ``seen`` records, per run and per page, the
 * keys in the order the page listed its modes, so the report's order never depends on timing.
 */
async function runEngine(
  name: string,
  engine: BrowserType,
  front: string,
  source: string,
  targets: Target[],
  results: Map<string, Map<string, string>>,
  seen: Map<string, string[][]>,
): Promise<void> {
  const browser: Browser = await engine.launch();
  try {
    await allEnded(
      VIEWPORTS.map(async (viewport) => {
        // A fresh context per viewport: no remembered arrangement, so every full graph is laid out.
        const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height } });
        const page = await context.newPage();
        const run = runName(name, viewport);
        // A page that never lays out throws only a timeout; surface what the page itself said so a
        // failure names its cause (a missing asset, a console error) instead of only "Timeout".
        page.on("pageerror", (error) => console.error(`[${run}] page error: ${error.message}`));
        page.on("console", (message) => {
          if (message.type() === "error") console.error(`[${run}] console error: ${message.text()}`);
        });
        page.on("response", async (response) => {
          if (response.status() >= 400) {
            const body = await response.text().catch(() => "");
            console.error(`[${run}] ${response.status()} ${response.url()} ${body.slice(0, 500)}`);
          }
        });
        const keysByTarget: string[][] = [];
        seen.set(run, keysByTarget);
        for (const target of targets) {
          const query = new URLSearchParams({ source, ...target.query });
          const hashes = await hashesOfPage(page, `${front}/?${query.toString()}`);
          const keys: string[] = [];
          for (const [mode, hash] of Object.entries(hashes)) {
            const key = `${target.label} | ${mode}`;
            keys.push(key);
            if (!results.has(key)) results.set(key, new Map());
            results.get(key)!.set(run, hash);
          }
          keysByTarget.push(keys);
        }
        await context.close();
      }),
    );
  } finally {
    await browser.close();
  }
}

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

/** The diagram point at the centre of a page's diagram element, and the page's pixels per diagram unit. */
async function diagramCentre(page: Page): Promise<{ x: number; y: number; scale: number }> {
  return page.evaluate(() => {
    const view = document.querySelector("[data-layout-hash]")!.getBoundingClientRect();
    const svg = document.querySelector("[data-layout-hash] svg")! as SVGSVGElement;
    const ctm = svg.getScreenCTM()!;
    const p = new DOMPoint(view.left + view.width / 2, view.top + view.height / 2).matrixTransform(ctm.inverse());
    return { x: p.x, y: p.y, scale: Math.hypot(ctm.a, ctm.b) };
  });
}

/**
 * The least gap between two circles of the room bar, everything each one draws included — its ring,
 * a focus ring, a follower count; negative when two of them overlap.
 */
async function circleGap(page: Page): Promise<number> {
  return page.evaluate(() => {
    const boxes = [...document.querySelectorAll('[aria-label="People in this room"] > button')].map((button) => {
      const parts = [button, ...button.querySelectorAll("*")].map((e) => e.getBoundingClientRect()).filter((r) => r.width > 0);
      const style = getComputedStyle(button);
      // An outline beyond the box (a positive offset) is part of what the circle draws.
      const out = style.outlineStyle !== "none" ? Math.max(0, parseFloat(style.outlineOffset) + parseFloat(style.outlineWidth)) : 0;
      return {
        left: Math.min(...parts.map((r) => r.left)) - out,
        right: Math.max(...parts.map((r) => r.right)) + out,
      };
    });
    let least = Infinity;
    boxes.forEach((a, i) => boxes.slice(i + 1).forEach((b) => (least = Math.min(least, Math.max(a.left, b.left) - Math.min(a.right, b.right)))));
    return least;
  });
}

/** The longest name a room accepts, in one word: a card must still fit its buttons. */
const LONG_NAME = "Leader" + "x".repeat(34);

/** How far the open card's buttons run past the card or into each other, in px (0 when they fit). */
async function cardButtonsOverlap(page: Page): Promise<number> {
  return page.evaluate(() => {
    const card = document.querySelector('[role="dialog"]')!.getBoundingClientRect();
    const buttons = [...document.querySelectorAll('[role="dialog"] button')].map((b) => b.getBoundingClientRect());
    let worst = 0;
    for (const b of buttons) worst = Math.max(worst, card.left - b.left, b.right - card.right);
    buttons.forEach((a, i) =>
      buttons.slice(i + 1).forEach((b) => {
        const across = Math.min(a.right, b.right) - Math.max(a.left, b.left);
        const down = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
        if (across > 0 && down > 0) worst = Math.max(worst, Math.min(across, down));
      }),
    );
    return worst;
  });
}

/** Following, led in one engine and watched in another: how far apart the screens stop (px), and how soon the hover shows (ms). */
async function followCase(lead: BrowserType, follow: BrowserType, front: string, source: string): Promise<{ apartPx: number; hoverMs: number; gapPx: number; cardPx: number }> {
  const leadBrowser: Browser = await lead.launch();
  const followBrowser: Browser = await follow.launch();
  try {
    const leader = await (await leadBrowser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
    const follower = await (await followBrowser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
    await leader.goto(`${front}/?${new URLSearchParams({ source, view: "domain-erd" }).toString()}`);
    await nextHash(leader, null);
    await domClick(leader, 'button:has-text("Open room")');
    await confirmName(leader, LONG_NAME);
    await leader.waitForURL(/room=/, { timeout: HASH_TIMEOUT_MS });
    await leader.locator(".MuiPopover-paper").waitFor({ timeout: HASH_TIMEOUT_MS });
    await leader.keyboard.press("Escape");
    await leader.locator(".MuiPopover-paper").waitFor({ state: "detached", timeout: HASH_TIMEOUT_MS });
    await follower.goto(leader.url());
    await confirmName(follower, "Follower");
    await nextHash(follower, null);
    // Enter on a circle opens its card; Follow there starts following.
    await follower.locator('[aria-label^="Leader"]').first().focus();
    await follower.keyboard.press("Enter");
    await follower.locator('[role="dialog"] button').first().waitFor({ timeout: HASH_TIMEOUT_MS });
    const cardPx = await cardButtonsOverlap(follower);
    await domClick(follower, 'button:has-text("Follow")');
    await follower.getByText("Following Leader").waitFor({ timeout: HASH_TIMEOUT_MS });
    // The leader now shows its ring and a follower count; a focus ring joins them on the follower's circle.
    await leader.getByLabel("1 following you").waitFor({ timeout: HASH_TIMEOUT_MS });
    await leader.locator('[aria-label^="Follower"]').first().focus();
    await leader.keyboard.press("Shift");
    const gapPx = await circleGap(leader);
    await leader.locator("[data-layout-hash]").first().click({ position: { x: 5, y: 5 } });

    const view = await leader.locator("[data-layout-hash]").first().boundingBox();
    const start = { x: view!.x + view!.width / 2, y: view!.y + view!.height / 2 };
    await leader.mouse.move(start.x, start.y);
    await leader.mouse.down();
    for (let i = 1; i <= 30; i += 1) {
      await leader.mouse.move(start.x - i * 8, start.y - i * 3);
      await leader.waitForTimeout(30);
    }
    await leader.mouse.up();
    await follower.waitForTimeout(1000);
    const [a, b] = [await diagramCentre(leader), await diagramCentre(follower)];
    const apartPx = Math.hypot(a.x - b.x, a.y - b.y) * b.scale;

    // A browser that reports a move under a resting pointer has opened a card there, which may cover the next node.
    await leader.keyboard.press("Escape");
    const node = await middleNode(leader);
    const centre = await nodeCentre(leader, node);
    const hoveredAt = Date.now();
    await leader.mouse.move(centre.x, centre.y);
    // A hover that never shows is reported, not waited for: four times the limit is enough to know.
    const shown = await follower
      .waitForFunction(
        (i) => {
          const nodes = document.querySelectorAll<HTMLElement>("[data-layout-hash] svg g.node");
          return nodes[i]?.style.opacity === "1" && [...nodes].some((n) => n.style.opacity === "0.35");
        },
        node,
        { timeout: FOLLOW_HOVER_MS * 4, polling: 20 },
      )
      .then(
        () => true,
        () => false,
      );
    return { apartPx, hoverMs: shown ? Date.now() - hoveredAt : Infinity, gapPx, cardPx };
  } finally {
    await leadBrowser.close();
    await followBrowser.close();
  }
}

/** A room with two people, the second following the first. */
async function openPlainRoom(leader: Page, follower: Page): Promise<void> {
  await domClick(leader, 'button:has-text("Open room")');
  await confirmName(leader, "Leader");
  await leader.waitForURL(/room=/, { timeout: HASH_TIMEOUT_MS });
  await leader.locator(".MuiPopover-paper").waitFor({ timeout: HASH_TIMEOUT_MS });
  await leader.keyboard.press("Escape");
  await leader.locator(".MuiPopover-paper").waitFor({ state: "detached", timeout: HASH_TIMEOUT_MS });
  await follower.goto(leader.url());
  await confirmName(follower, "Follower");
  await nextHash(follower, null);
  await follower.locator('[aria-label^="Leader"]').first().focus();
  await follower.keyboard.press("Enter");
  await follower.locator('[role="dialog"] button').first().waitFor({ timeout: HASH_TIMEOUT_MS });
  await domClick(follower, 'button:has-text("Follow")');
  await follower.getByText("Following Leader").waitFor({ timeout: HASH_TIMEOUT_MS });
}

/** One page of each kind the left panel lists, in its order: full graph, ERD of all domains, a domain's ERD, a use case, a lifecycle. */
function oneOfEachKind(targets: Target[]): Target[] {
  const kinds = ["full graph", "ERD, all domains", "ERD ", "use case ", "lifecycle "];
  return kinds.flatMap((kind) => targets.filter((target) => target.label.startsWith(kind)).slice(0, 1));
}

/** How a follower drew one page against its leader. */
type PageFollow = { label: string; same: boolean; apartPx: number; zoomOff: number; inkShare: number | null };

/** The diagram's camera as the address says it — its zoom and the diagram point at the screen's top-left — and where the diagram stands. */
const cameraInPage = () => {
  const params = new URLSearchParams(location.search);
  const zoom = Number(params.get("zoom"));
  const [x, y] = (params.get("at") ?? "").split(",").map(Number);
  // ``data-layout-hash`` is absent for a moment while a new drawing is hashed: no camera to read then.
  const element = document.querySelector("[data-layout-hash]");
  if (!element) return null;
  const view = element.getBoundingClientRect();
  // A map's y grows upward: the top of its screen stands above the centre by a larger y, not a smaller one.
  const up = element.querySelector("canvas") ? 1 : -1;
  return { zoom, left: x - view.width / (2 * zoom), top: y + (up * view.height) / (2 * zoom), view: { x: view.left, y: view.top, width: view.width, height: view.height }, inner: innerWidth };
};
const hashInPage = () => document.querySelector("[data-layout-hash]")?.getAttribute("data-layout-hash") ?? null;
const clickButtonInPage = (text: string) => {
  const button = [...document.querySelectorAll<HTMLElement>("button, [role=button]")].find((each) => each.textContent?.trim() === text || each.getAttribute("aria-label") === text);
  button?.click();
  return Boolean(button);
};

/**
 * The share of ``tab``'s diagram on screen that is drawn on — the diagram alone: for the screenshot every panel, button,
 * banner and pointer over it is hidden, so a follower with an empty diagram cannot pass on the panels both screens show.
 */
async function inkOfDiagram(tab: BrowserTab): Promise<number> {
  await tab.evaluate(() => {
    const style = document.createElement("style");
    style.id = "ink-only-the-diagram";
    style.textContent =
      "[data-layout-hash] * { visibility: hidden !important; }" +
      "[data-layout-hash] svg:not(.MuiSvgIcon-root), [data-layout-hash] svg:not(.MuiSvgIcon-root) *, [data-layout-hash] canvas { visibility: visible !important; }" +
      "[data-testid=pointer-layer], [data-follow-tooltip], [data-own-tooltip] { display: none !important; }";
    document.head.appendChild(style);
    return true;
  }, null);
  try {
    const camera = await waitInPage(tab, cameraInPage, null, HASH_TIMEOUT_MS, "the diagram");
    const image = decodePng(await tab.screenshot());
    const scale = image.width / camera.inner;
    // A few pixels in from the edge, past the frame a follower's screen wears.
    const inset = 6;
    return inkOf(image, { x: (camera.view.x + inset) * scale, y: (camera.view.y + inset) * scale, width: (camera.view.width - 2 * inset) * scale, height: (camera.view.height - 2 * inset) * scale });
  } finally {
    await tab.evaluate(() => (document.getElementById("ink-only-the-diagram")?.remove(), true), null);
  }
}

/** The leader opens ``url`` and a room there; the follower joins it and follows the leader. */
async function openRoomAndFollow(leader: BrowserTab, follower: BrowserTab, url: string): Promise<void> {
  await leader.goto(url);
  await waitInPage(leader, hashInPage, null, HASH_TIMEOUT_MS, "the leader's first diagram");
  await waitInPage(leader, clickButtonInPage, "Open room", HASH_TIMEOUT_MS, "Open room");
  await leader.fill("#room-name-input", "Leader");
  await waitInPage(leader, (selector: string) => (document.querySelector<HTMLElement>(selector)?.click(), true), 'form button[type="submit"]', HASH_TIMEOUT_MS, "the name's button");
  await waitInPage(leader, () => location.search.includes("room=") && Boolean(document.querySelector(".MuiPopover-paper")), null, HASH_TIMEOUT_MS, "the room and its invite");
  await leader.press("Escape");
  await waitInPage(leader, () => !document.querySelector(".MuiPopover-paper"), null, HASH_TIMEOUT_MS, "the invite to close");

  await follower.goto(await leader.url());
  await waitInPage(follower, hashInPage, null, HASH_TIMEOUT_MS, "the follower's first diagram");
  await follower.fill("#room-name-input", "Follower");
  await waitInPage(follower, (selector: string) => (document.querySelector<HTMLElement>(selector)?.click(), true), 'form button[type="submit"]', HASH_TIMEOUT_MS, "the name's button");
  // A click with no pointer — Enter — opens the leader's card; Follow there starts following.
  await waitInPage(follower, () => Boolean(document.querySelector('[aria-label^="Leader"]')), null, HASH_TIMEOUT_MS, "the leader's circle");
  await waitInPage(
    follower,
    () => {
      const follow = [...document.querySelectorAll<HTMLElement>('[role="dialog"] button')].find((button) => button.textContent?.trim() === "Follow");
      if (follow) follow.click();
      else document.querySelector<HTMLElement>('[aria-label^="Leader"]')?.click();
      return Boolean(follow);
    },
    null,
    HASH_TIMEOUT_MS,
    "Follow on the leader's card",
  );
  await waitInPage(follower, () => document.body.textContent?.includes("Following Leader") ?? false, null, HASH_TIMEOUT_MS, "following");
}

/** The leader goes to ``page`` in the room; whether the follower then draws the same picture. */
async function goTo(leader: BrowserTab, follower: BrowserTab, page: Target): Promise<boolean> {
  const before = await leader.evaluate(hashInPage, null);
  await leader.evaluate((query: Record<string, string>) => {
    const url = new URL(location.href);
    for (const name of ["view", "domain", "node", "host", "zoom", "at"]) url.searchParams.delete(name);
    for (const [name, value] of Object.entries(query)) url.searchParams.set(name, value);
    history.pushState(null, "", url);
    dispatchEvent(new PopStateEvent("popstate"));
    return true;
  }, page.query);
  const hash = await waitInPage(leader, (previous: string | null) => {
    const now = document.querySelector("[data-layout-hash]")?.getAttribute("data-layout-hash") ?? null;
    return now && now !== previous ? now : null;
  }, before, HASH_TIMEOUT_MS, `the leader on ${page.label}`).catch(() => before);
  const same = await waitInPage(follower, (wanted: string | null) => document.querySelector("[data-layout-hash]")?.getAttribute("data-layout-hash") === wanted, hash, HASH_TIMEOUT_MS, `the follower on ${page.label}`).then(
    () => true,
    () => false,
  );
  return same;
}

/** The follower's camera once its glide has ended: a loaded machine glides slowly, and a stuck one still reads wrong. */
async function restingCamera(follower: BrowserTab): Promise<Awaited<ReturnType<typeof readCamera>>> {
  let camera = await readCamera(follower);
  for (let reads = 0; reads < CAMERA_REST_READS; reads += 1) {
    await new Promise((resolve) => setTimeout(resolve, HASH_STABLE_MS));
    const now = await readCamera(follower);
    if (Math.abs(now.zoom - camera.zoom) < ZOOM_TOLERANCE / 10 && Math.hypot(now.left - camera.left, now.top - camera.top) < 0.5) return now;
    camera = now;
  }
  return camera;
}

function readCamera(tab: BrowserTab) {
  return waitInPage(tab, cameraInPage, null, HASH_TIMEOUT_MS, "the follower's diagram");
}

/**
 * The leader opens a room, the follower joins and follows; then the leader goes to each page and zooms in,
 * and the follower is measured against it there.
 */
async function followEveryDiagram(openLead: () => Promise<BrowserTab>, openFollow: () => Promise<BrowserTab>, front: string, source: string, pages: Target[]): Promise<PageFollow[]> {
  const leader = await openLead();
  const follower = await openFollow().catch(async (error: unknown) => {
    await leader.close();
    throw error;
  });
  try {
    await openRoomAndFollow(leader, follower, `${front}/?${new URLSearchParams({ source, ...pages[0].query }).toString()}`);

    const outcomes: PageFollow[] = [];
    for (const page of pages) {
      const same = await goTo(leader, follower, page);
      await leader.evaluate(clickButtonInPage, "Zoom in");
      await new Promise((resolve) => setTimeout(resolve, SETTLE_MS));
      const a = await waitInPage(leader, cameraInPage, null, HASH_TIMEOUT_MS, "the leader's diagram");
      const b = await restingCamera(follower);
      const [leaderInk, followerInk] = [await inkOfDiagram(leader), await inkOfDiagram(follower)];
      outcomes.push({
        label: page.label,
        same,
        apartPx: Math.hypot(a.left - b.left, a.top - b.top) * a.zoom,
        zoomOff: Math.abs(b.zoom / a.zoom - 1),
        inkShare: leaderInk < EMPTY_INK ? null : followerInk / leaderInk,
      });
    }
    return outcomes;
  } finally {
    await follower.close();
    await leader.close();
  }
}

/**
 * One change of the picture the leader makes, and how it is made on its page. ``newPage``: it opens another diagram,
 * and the blank while it loads is not counted — what is, is any picture between the old one and the new one's first.
 */
type VisualChange = { label: string; act: (tab: BrowserTab) => Promise<void>; newPage?: boolean };

/** The leader opens ``target`` in the room, as the left panel does: the follower is led there. */
const openPage = (target: Target): VisualChange => ({
  label: `to ${target.label}`,
  newPage: true,
  act: async (tab) =>
    void (await tab.evaluate((query: Record<string, string>) => {
      const url = new URL(location.href);
      for (const name of ["view", "domain", "node", "host", "zoom", "at"]) url.searchParams.delete(name);
      for (const [name, value] of Object.entries(query)) url.searchParams.set(name, value);
      history.pushState(null, "", url);
      dispatchEvent(new PopStateEvent("popstate"));
      return true;
    }, target.query)),
});

const clickInPage = (selector: string) => {
  const element = document.querySelector<HTMLElement>(selector);
  element?.click();
  return Boolean(element);
};
const clickLabelInPage = (text: string) => {
  const label = [...document.querySelectorAll<HTMLElement>("label")].find((each) => each.textContent?.trim() === text);
  label?.querySelector<HTMLElement>("input")?.click();
  return Boolean(label);
};
const clickFirstFilterRowInPage = () => {
  const row = document.querySelector<HTMLElement>('[aria-label="Filter"] button[aria-pressed]');
  row?.click();
  return Boolean(row);
};

const click = (selector: string) => async (tab: BrowserTab) => void (await waitInPage(tab, clickInPage, selector, HASH_TIMEOUT_MS, selector));
const ERD_CHANGES: VisualChange[] = [
  // With 1-hop on, a domain switched off may come back whole as its neighbours' neighbours; off, it surely goes.
  { label: "1-hop off", act: async (tab) => void (await waitInPage(tab, clickLabelInPage, "1-hop", HASH_TIMEOUT_MS, "1-hop")) },
  { label: "a domain off", act: async (tab) => void (await waitInPage(tab, clickFirstFilterRowInPage, null, HASH_TIMEOUT_MS, "a filter row")) },
  { label: "the domain on", act: async (tab) => void (await waitInPage(tab, clickFirstFilterRowInPage, null, HASH_TIMEOUT_MS, "a filter row")) },
  { label: "paint by kinds", act: click('[aria-label="Paint by Kinds"]') },
  { label: "paint by domains", act: click('[aria-label="Paint by Domains"]') },
  { label: "top to bottom", act: click('[aria-label="Dot — top to bottom"]') },
  { label: "left to right", act: click('[aria-label="Dot — left to right"]') },
  { label: "1-hop on", act: async (tab) => void (await waitInPage(tab, clickLabelInPage, "1-hop", HASH_TIMEOUT_MS, "1-hop")) },
];
const ONE_DOMAIN_CHANGES: VisualChange[] = [
  { label: "1-hop off", act: async (tab) => void (await waitInPage(tab, clickLabelInPage, "1-hop", HASH_TIMEOUT_MS, "1-hop")) },
  { label: "1-hop on", act: async (tab) => void (await waitInPage(tab, clickLabelInPage, "1-hop", HASH_TIMEOUT_MS, "1-hop")) },
];
const USE_CASE_CHANGES: VisualChange[] = [
  { label: "top to bottom", act: click('[aria-label="Dot — top to bottom"]') },
  { label: "left to right", act: click('[aria-label="Dot — left to right"]') },
  { label: "boundary off", act: async (tab) => void (await waitInPage(tab, clickLabelInPage, "Boundary", HASH_TIMEOUT_MS, "Boundary")) },
  { label: "boundary on", act: async (tab) => void (await waitInPage(tab, clickLabelInPage, "Boundary", HASH_TIMEOUT_MS, "Boundary")) },
];

/**
 * Start recording, once a frame, what the diagram shows: its drawing — the view box, the number of nodes, the first
 * node's fill — and the camera, the pan and zoom rounded to half a pixel; a new entry each time it changes. Whether
 * the page told of pointers off is kept too.
 */
const startFramesInPage = () => {
  const w = window as unknown as { __frames?: { states: string[]; pointersOff: boolean; stop: boolean } };
  if (w.__frames) w.__frames.stop = true;
  const record = { states: [] as string[], pointersOff: false, stop: false };
  w.__frames = record;
  let last: { drawing: string; camera: number[] } | null = null;
  const tick = () => {
    if (record.stop) return;
    // The drawing is the SVG its pan and zoom move — not found through ``data-layout-hash``, which is absent for a
    // moment while a new drawing is hashed, though the drawing stays on screen.
    const svg = [...document.querySelectorAll<SVGSVGElement>("svg:not(.MuiSvgIcon-root)")].find((each) => each.parentElement?.style.transform.startsWith("matrix"));
    let drawing = "nothing";
    let camera: number[] = [];
    if (svg) {
      let fill = 0;
      for (const element of svg.querySelectorAll("[fill]")) for (const char of element.getAttribute("fill") ?? "") fill = (fill * 31 + char.charCodeAt(0)) | 0;
      drawing = [svg.getAttribute("viewBox"), svg.querySelectorAll("g.node").length, fill].join("|");
      camera = (svg.parentElement?.style.transform.match(/-?[\d.]+(e-?\d+)?/g) ?? []).map(Number);
    }
    // A new picture: another drawing, or the camera moved by a pixel or more — a hundredth of a pixel is no frame.
    const moved = !last || camera.length < 6 || last.camera.length < 6 || Math.abs(camera[0] / last.camera[0] - 1) > 0.001 || Math.abs(camera[4] - last.camera[4]) >= 1 || Math.abs(camera[5] - last.camera[5]) >= 1;
    if (!last || drawing !== last.drawing || moved) {
      record.states.push(`${drawing}|${camera.map((n) => n.toFixed(3)).join(",")}`);
      last = { drawing, camera };
    }
    if (document.body.textContent?.includes("Pointers are off")) record.pointersOff = true;
    requestAnimationFrame(tick);
  };
  tick();
  return true;
};
const readFramesInPage = () => {
  const record = (window as unknown as { __frames?: { states: string[]; pointersOff: boolean } }).__frames;
  return record ? { pictures: record.states.length - 1, states: record.states, pointersOff: record.pointersOff } : { pictures: -1, states: [], pointersOff: false };
};

/** How one change showed on both screens: the number of new pictures each drew, and whether pointers went off. */
type ChangeFrames = { page: string; change: string; leader: number; follower: number; pointersOff: boolean; followerStates: string[] };

/** The leader makes every change on each page; both screens are recorded frame by frame. */
async function everyChangeInOneFrame(openLead: () => Promise<BrowserTab>, openFollow: () => Promise<BrowserTab>, front: string, source: string, pages: { target: Target; changes: VisualChange[] }[]): Promise<ChangeFrames[]> {
  const leader = await openLead();
  const follower = await openFollow().catch(async (error: unknown) => {
    await leader.close();
    throw error;
  });
  try {
    await openRoomAndFollow(leader, follower, `${front}/?${new URLSearchParams({ source, ...pages[0].target.query }).toString()}`);
    const outcomes: ChangeFrames[] = [];
    for (const { target, changes } of pages) {
      await goTo(leader, follower, target);
      await new Promise((resolve) => setTimeout(resolve, SETTLE_MS));
      for (const change of changes) {
        await leader.evaluate(startFramesInPage, null);
        await follower.evaluate(startFramesInPage, null);
        await change.act(leader);
        await new Promise((resolve) => setTimeout(resolve, SETTLE_MS * 2));
        const [a, b] = [await leader.evaluate(readFramesInPage, null), await follower.evaluate(readFramesInPage, null)];
        const pictures = (frames: { pictures: number; states: string[] }) => (change.newPage ? frames.states.filter((state) => !state.startsWith("nothing")).length - 1 : frames.pictures);
        outcomes.push({ page: target.label, change: change.label, leader: pictures(a), follower: pictures(b), pointersOff: b.pointersOff || a.pointersOff, followerStates: b.states });
      }
    }
    return outcomes;
  } finally {
    await follower.close();
    await leader.close();
  }
}

/** Whether a follower drew a page as its leader did. */
function followFits(outcome: PageFollow): boolean {
  const zoomFits = outcome.zoomOff <= ZOOM_TOLERANCE;
  return outcome.same && zoomFits && outcome.apartPx <= POINTER_TOLERANCE_PX && (outcome.inkShare === null || outcome.inkShare >= FOLLOW_INK_SHARE);
}

/** Check every page and mode; print one line each; return whether all of them agree. */
/**
 * Print one line per page and mode — pages in the left panel's order, modes in the order the
 * page lists them — and, for a difference, every run in engine-then-viewport order.
 */
function report(results: Map<string, Map<string, string>>, seen: Map<string, string[][]>, targetCount: number): boolean {
  const runs = ENGINES.flatMap(([name]) => VIEWPORTS.map((viewport) => runName(name, viewport)));
  const keys: string[] = [];
  for (let target = 0; target < targetCount; target++) {
    for (const run of runs) {
      for (const key of seen.get(run)?.[target] ?? []) if (!keys.includes(key)) keys.push(key);
    }
  }
  let ok = true;
  for (const key of keys) {
    const byRun = results.get(key)!;
    const distinct = new Set(byRun.values());
    if (distinct.size === 1 && byRun.size === runs.length) {
      console.log(`ok    ${key}  ${[...distinct][0].slice(0, 16)}`);
      continue;
    }
    ok = false;
    console.log(`DIFF  ${key}`);
    for (const run of runs) if (byRun.has(run)) console.log(`        ${run}: ${byRun.get(run)!.slice(0, 16)}`);
    if (byRun.size !== runs.length) console.log(`        ${runs.length - byRun.size} run(s) gave no hash`);
  }
  return ok;
}

/**
 * Wait until every promise has settled, then return their values in order — or throw the first
 * failure. Nothing is left running when the step stops on an error.
 */
async function allEnded<T>(promises: Promise<T>[]): Promise<T[]> {
  const settled = await Promise.allSettled(promises);
  const failed = settled.find((result): result is PromiseRejectedResult => result.status === "rejected");
  if (failed) throw failed.reason;
  return settled.map((result) => (result as PromiseFulfilledResult<T>).value);
}

/** Run ``work`` and return its value with how long it took, in seconds to a tenth. */
async function timed<T>(work: () => Promise<T>): Promise<{ value: T; seconds: string }> {
  const since = Date.now();
  const value = await work();
  return { value, seconds: seconds(since) };
}

/** Seconds since ``since``, to a tenth. */
function seconds(since: number): string {
  return ((Date.now() - since) / 1000).toFixed(1);
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
    const seen = new Map<string, string[][]>();
    // Layout hashes and the pointer cases run at once; following runs after them, because its 500 ms
    // hover limit was missed with every part's browsers open together. Each part opens its own
    // browsers and rooms, and all print afterwards in their fixed order.
    const pairs = ENGINES.flatMap(([leadName, leadEngine]) =>
      ENGINES.filter(([followName]) => followName !== leadName).map(([followName, followEngine]) => ({
        leadName,
        followName,
        leadEngine,
        followEngine,
      })),
    );
    const layoutRun = timed(() =>
      allEnded(ENGINES.map(([name, engine]) => runEngine(name, engine, frontUrl, source, targets, results, seen))),
    );
    const pointerRun = timed(() => allEnded(ENGINES.map(([, engine]) => pointerCase(engine, frontUrl, source))));
    await allEnded<unknown>([layoutRun, pointerRun]);
    const [layout, pointers] = [await layoutRun, await pointerRun];
    // Following in every directed pair of engines, all pairs at once — each opens its own room.
    const following = await timed(() =>
      allEnded(pairs.map((pair) => followCase(pair.leadEngine, pair.followEngine, frontUrl, source))),
    );
    // Following on every kind of diagram, in every directed pair of four browsers. Playwright's pairs run at
    // once; Safari's one after another, since Safari drives one session at a time.
    const pages = oneOfEachKind(targets);
    // The real Safari only paints in a window on screen, so it runs when asked: MAXITOR_CHECK_SAFARI=1 adds it to
    // following on every diagram, =full to every change in one frame too. Its window must stay uncovered meanwhile.
    const safariAsked = process.env.MAXITOR_CHECK_SAFARI ?? "";
    const safariPort = await freePort();
    const safariWhy = safariAsked ? await safariUnavailable(safariPort) : "not asked for (MAXITOR_CHECK_SAFARI=1 or full)";
    const openers: [string, () => Promise<BrowserTab>][] = [
      ...ENGINES.map(([name, engine]): [string, () => Promise<BrowserTab>] => [
        name,
        async () => {
          const browser = await engine.launch();
          const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
          return playwrightTab(name, page, () => browser.close());
        },
      ]),
      ...(safariWhy === null ? [["safari", () => safariTab(safariPort, 1440, 900)] as [string, () => Promise<BrowserTab>]] : []),
    ];
    const everyPair = openers
      .flatMap(([leadName, lead]) => openers.filter(([followName]) => followName !== leadName).map(([followName, follow]) => ({ leadName, followName, lead, follow })))
      .filter((pair) => !(pair.leadName === "safari" || pair.followName === "safari") || pair.leadName === "chromium" || pair.followName === "chromium");
    const isSafari = (pair: { leadName: string; followName: string }) => pair.leadName === "safari" || pair.followName === "safari";
    // Safari's pairs run one after another, so it pairs with Chromium only, both ways: the engine whose difference
    // from Safari matters, at a third of the time.
    const everyDiagram = await timed(async () => {
      const byPair = new Map<string, PageFollow[]>();
      const parallel = everyPair.filter((pair) => !isSafari(pair));
      const outcomes = await allEnded(parallel.map((pair) => followEveryDiagram(pair.lead, pair.follow, frontUrl, source, pages)));
      parallel.forEach((pair, i) => byPair.set(`${pair.leadName} → ${pair.followName}`, outcomes[i]));
      for (const pair of everyPair.filter(isSafari)) byPair.set(`${pair.leadName} → ${pair.followName}`, await followEveryDiagram(pair.lead, pair.follow, frontUrl, source, pages));
      return byPair;
    });
    // Every change of the picture in one frame, in the same pairs: Playwright's at once, Safari's one after another.
    const byLabel = (prefix: string) => pages.find((page) => page.label.startsWith(prefix));
    // Going to another diagram counts too: the follower opens it at the leader's view at once.
    const opened = ["use case ", "ERD, all domains", "lifecycle ", "ERD "].flatMap((prefix) => (byLabel(prefix) ? [openPage(byLabel(prefix)!)] : []));
    const changePages = [
      { target: byLabel("ERD, all domains"), changes: ERD_CHANGES },
      { target: byLabel("ERD "), changes: [...ONE_DOMAIN_CHANGES, ...opened] },
      { target: byLabel("use case "), changes: USE_CASE_CHANGES },
    ].filter((page): page is { target: Target; changes: VisualChange[] } => page.target !== undefined);
    const oneFrame = await timed(async () => {
      const byPair = new Map<string, ChangeFrames[]>();
      const parallel = everyPair.filter((pair) => !isSafari(pair));
      const outcomes = await allEnded(parallel.map((pair) => everyChangeInOneFrame(pair.lead, pair.follow, frontUrl, source, changePages)));
      parallel.forEach((pair, i) => byPair.set(`${pair.leadName} → ${pair.followName}`, outcomes[i]));
      if (safariAsked === "full") for (const pair of everyPair.filter(isSafari)) byPair.set(`${pair.leadName} → ${pair.followName}`, await everyChangeInOneFrame(pair.lead, pair.follow, frontUrl, source, changePages));
      return byPair;
    });
    const cards = await timed(() => cardMechanics(chromium, `${frontUrl}/?${new URLSearchParams({ source, view: "domain-erd" }).toString()}`, { drawn: (page) => nextHash(page, null), openRoom: openPlainRoom }));
    const [partASeconds, partBSeconds, partCSeconds] = [layout.seconds, pointers.seconds, following.seconds];
    ok = report(results, seen, targets.length);
    const offsets = pointers.value;
    // Steps: arrow; arrow after the phone zooms; arrow after the desktop zooms; the phone's tap.
    ENGINES.forEach(([name], i) => {
      const largest = Math.max(...offsets[i]);
      const fits = largest <= POINTER_TOLERANCE_PX;
      ok &&= fits;
      const steps = offsets[i].map((o) => o.toFixed(3)).join(" / ");
      console.log(`${fits ? "ok  " : "DIFF"}  pointer in a room | ${name}  largest offset ${largest.toFixed(3)} px (${steps})`);
    });
    const outcomes = following.value;
    pairs.forEach(({ leadName, followName }, i) => {
      const { apartPx, hoverMs, gapPx, cardPx } = outcomes[i];
      const fits = apartPx <= POINTER_TOLERANCE_PX && hoverMs <= FOLLOW_HOVER_MS && gapPx > 0 && cardPx <= 0.5;
      ok &&= fits;
      console.log(
        `${fits ? "ok  " : "DIFF"}  following | ${leadName} → ${followName}  screens apart ${apartPx.toFixed(3)} px, hover after ${hoverMs} ms, circles ${gapPx.toFixed(1)} px apart, card buttons overrun ${cardPx.toFixed(1)} px`,
      );
    });
    for (const [pair, outcomes] of everyDiagram.value) {
      for (const outcome of outcomes) {
        const fits = followFits(outcome);
        ok &&= fits;
        const ink = outcome.inkShare === null ? "nothing drawn" : `${Math.round(outcome.inkShare * 100)} % of the leader's ink`;
        console.log(
          `${fits ? "ok  " : "DIFF"}  following ${outcome.label} | ${pair}  ${outcome.same ? "same diagram" : "ANOTHER diagram"}, corners ${outcome.apartPx.toFixed(3)} px apart, zoom off ${(outcome.zoomOff * 100).toFixed(2)} %, ${ink}`,
        );
      }
    }
    for (const [pair, outcomes] of oneFrame.value) {
      for (const outcome of outcomes) {
        // At most one new picture each: none when a change happens to leave the picture as it was.
        const fits = outcome.leader <= 1 && outcome.follower <= 1 && outcome.follower >= outcome.leader && !outcome.pointersOff;
        ok &&= fits;
        console.log(
          `${fits ? "ok  " : "DIFF"}  one frame | ${outcome.page}: ${outcome.change} | ${pair}  leader ${outcome.leader} picture(s), follower ${outcome.follower} picture(s)${outcome.pointersOff ? ", POINTERS OFF" : ""}`,
        );
        // A follower that drew more than one picture shows each, so the frame in between can be read.
        if (!fits) for (const state of outcome.followerStates) console.log(`        ${state}`);
      }
    }
    for (const outcome of cards.value satisfies CardCase[]) {
      ok &&= outcome.ok;
      console.log(`${outcome.ok ? "ok  " : "DIFF"}  card | ${outcome.name}${outcome.ok ? "" : `  ${outcome.detail}`}`);
    }
    if (safariWhy !== null) {
      // Asked for on macOS, Safari must answer; not asked for, or elsewhere, it is skipped with a line saying so.
      const required = Boolean(safariAsked) && process.platform === "darwin";
      ok &&= !required;
      console.log(`${required ? "DIFF" : "skip"}  Safari | ${safariWhy}`);
    }
    console.log(`part A (layout hashes) ${partASeconds} s`);
    console.log(`part B (pointer in a room) ${partBSeconds} s`);
    console.log(`part C (following) ${partCSeconds} s`);
    console.log(`part D (following on every diagram) ${everyDiagram.seconds} s`);
    console.log(`part E (every change in one frame) ${oneFrame.seconds} s`);
    console.log(`part F (the card and collapsing) ${cards.seconds} s`);
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
