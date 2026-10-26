// packages/aoa-maxitor/client/scripts/measure-full-graph.ts
/**
 * measure-full-graph — open the full-graph page in Chromium and report what it costs.
 *
 * A development tool, run by hand: the check run has no browser and does not run it.
 * Everything is read from what any browser exposes to any page (network events, long
 * tasks, the canvas, worker targets); no hook is added to the client for it.
 *
 * Command line, report shape and the rules for the first pixel and the settled frame
 * are in `specs/026-full-graph-fast-open/contracts/measurement-report.md`.
 */

import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { chromium } from "playwright";
import type { Browser, BrowserContext, CDPSession, Locator, Page } from "playwright";

const TOOL = "measure-full-graph/1";
const VIEWPORT = { width: 1600, height: 900 };
const FALLBACK_MESSAGES = ["fallback to main thread", "the background layout is unavailable"];
const FIRST_PIXEL_TIMEOUT_MS = 60_000;
const SETTLE_INTERVAL_MS = 200;
const SETTLE_IDENTICAL = 5;
const SETTLE_TIMEOUT_MS = 10_000;
const PIXEL_PROBE = 16;

let measuredCanvasSize: [number, number] = [0, 0];

type Args = {
  maxitor: string;
  source: string;
  view: string;
  conditions: string[];
  runs: number;
  out: string | null;
  canvas: string | null;
  compareCanvas: string | null;
  noPixelProbe: boolean;
  interactionProbe: boolean;
  noWorker: boolean;
  noStorage: boolean;
};

type Resource = {
  url: string;
  type: string;
  startMs: number;
  encodedBytes: number;
  decodedBytes: number;
  contentEncoding: string | null;
  cacheControl: string | null;
  status: number;
  fromCache: boolean;
};

type OpenReport = {
  totalBytes: number;
  longestTaskMs: number;
  firstGraphPixelMs: number | null;
  mainScriptingMs: number;
  workers: { url: string; cpuMs: number }[];
  longTasks: { startMs: number; durationMs: number }[];
  resources: Resource[];
};

type ConditionReport = { first: OpenReport; repeat: OpenReport };

type Report = {
  tool: string;
  commit: string;
  maxitor: string;
  source: string;
  viewport: [number, number];
  canvasSize: [number, number];
  conditions: Record<string, ConditionReport>;
  consoleFailures: string[];
  canvas: string | null;
};

type NetworkRecord = {
  url: string;
  type: string;
  startMs: number;
  status: number;
  contentEncoding: string | null;
  cacheControl: string | null;
  fromCache: boolean;
  encodedBytes: number;
};

/** Parsed command line. */
function parseArgs(argv: string[]): Args {
  const args: Args = {
    maxitor: "",
    source: "",
    view: "full-graph",
    conditions: ["cpu1x", "cpu4x", "slow4g"],
    runs: 3,
    out: null,
    canvas: null,
    compareCanvas: null,
    noPixelProbe: false,
    interactionProbe: false,
    noWorker: false,
    noStorage: false,
  };
  for (let i = 0; i < argv.length; i += 1) {
    const name = argv[i];
    const value = () => {
      const next = argv[i + 1];
      if (next === undefined || next.startsWith("--")) throw new Error(`${name} needs a value`);
      i += 1;
      return next;
    };
    switch (name) {
      case "--maxitor":
        args.maxitor = value();
        break;
      case "--source":
        args.source = value();
        break;
      case "--view":
        args.view = value();
        break;
      case "--conditions":
        args.conditions = value().split(",").map((c) => c.trim()).filter(Boolean);
        break;
      case "--runs":
        args.runs = Number(value());
        break;
      case "--out":
        args.out = value();
        break;
      case "--canvas":
        args.canvas = value();
        break;
      case "--compare-canvas":
        args.compareCanvas = value();
        break;
      case "--no-pixel-probe":
        args.noPixelProbe = true;
        break;
      case "--interaction-probe":
        args.interactionProbe = true;
        break;
      case "--no-worker":
        args.noWorker = true;
        break;
      case "--no-storage":
        args.noStorage = true;
        break;
      case "--help":
      case "-h":
        printUsage();
        process.exit(0);
        break;
      default:
        throw new Error(`unknown option ${name}`);
    }
  }
  if (!args.maxitor || !args.source) throw new Error("--maxitor and --source are required");
  if (!Number.isInteger(args.runs) || args.runs < 1) throw new Error("--runs must be a positive integer");
  return args;
}

/** Print the options the tool takes. */
function printUsage(): void {
  process.stderr.write(
    [
      "measure-full-graph — bytes, headers, long tasks and the first graph pixel of the full graph.",
      "",
      "  --maxitor <url>          base URL of a Maxitor serving its built client (required)",
      "  --source <url>           the graph-json URL put into ?source= (required)",
      "  --view <slug>            view to open (default full-graph; use domain-erd for SC-008)",
      "  --conditions <list>      cpu1x,cpu4x,slow4g (default all three)",
      "  --runs <n>               runs per condition, times reported as the median (default 3)",
      "  --out <file>             write the JSON report here (default stdout)",
      "  --canvas <file>          save the settled canvas of cpu1x/first here",
      "  --compare-canvas <file>  fail if any pixel of that settled canvas differs",
      "  --no-pixel-probe         turn the first-pixel sampler off (used to price it)",
      "  --interaction-probe      hover a node, drag it, fail if the picture moved",
      "  --no-worker              delete window.Worker; the fallback warning is then expected",
      "  --no-storage             delete window.indexedDB; a repeat open must lay out again",
      "",
    ].join("\n"),
  );
}

/** Median of a list of numbers. */
function median(values: number[]): number {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 === 0 ? (sorted[middle - 1] + sorted[middle]) / 2 : sorted[middle];
}

/** Short commit of the build being measured. */
function shortCommit(): string {
  try {
    return execFileSync("git", ["rev-parse", "--short", "HEAD"], { encoding: "utf8" }).trim();
  } catch {
    return "unknown";
  }
}

/** The URL the page is opened on. */
function pageUrl(args: Args): string {
  const url = new URL(args.maxitor);
  url.searchParams.set("view", args.view);
  url.searchParams.set("source", args.source);
  return url.toString();
}

/** Script installed before the page's own code: long tasks, the load mark, the first pixel. */
function measurementScript(probePixels: boolean): string {
  const probe = probePixels
    ? `
  const off = document.createElement("canvas");
  off.width = ${PIXEL_PROBE};
  off.height = ${PIXEL_PROBE};
  const ctx = off.getContext("2d", { willReadFrequently: true });
  const sample = () => {
    if (state.firstGraphPixelMs !== null) return;
    for (const canvas of pickCanvases()) {
      if (!ctx || canvas.width === 0 || canvas.height === 0) continue;
      ctx.clearRect(0, 0, off.width, off.height);
      ctx.drawImage(canvas, 0, 0, off.width, off.height);
      const pixels = ctx.getImageData(0, 0, off.width, off.height).data;
      for (let i = 3; i < pixels.length; i += 4) {
        if (pixels[i] > 0) {
          state.firstGraphPixelMs = performance.now();
          return;
        }
      }
    }
    requestAnimationFrame(sample);
  };
  requestAnimationFrame(sample);
`
    : "";
  return `
(() => {
  if (window.__measure) return;
  try {
  const state = { longTasks: [], firstGraphPixelMs: null, loadMs: null };
  Object.defineProperty(window, "__measure", { value: state, configurable: true });
  const pickCanvases = () => {
    const viewport = document.querySelector(".ix-interchange-viewport");
    if (!viewport) return [];
    return Array.from(viewport.querySelectorAll("canvas"));
  };
  new PerformanceObserver((list) => {
    for (const entry of list.getEntries()) {
      state.longTasks.push({ startMs: entry.startTime, durationMs: entry.duration });
    }
  }).observe({ type: "longtask", buffered: true });
  window.addEventListener("load", () => {
    state.loadMs = performance.now();
  });
${probe}
  } catch (error) {
    window.__measureError = String((error && error.stack) || error);
  }
})();
`;
}

/** Remove a global the run must do without. */
function blockingScript(name: "Worker" | "indexedDB"): string {
  return `Object.defineProperty(window, "${name}", { value: undefined, configurable: true });`;
}

type WorkerRecord = { sessionId: string; url: string; cpuMs: number | null };

/**
 * Profiles worker targets over a browser-level CDP session.
 *
 * `Target.setAutoAttach` pauses every new target until it is resumed; the profiler starts
 * on each worker before resuming it, and stops it when the open ends. `cpuMs` is the
 * sampled CPU time: hit counts times the 1 ms sampling interval.
 */
class WorkerProfiler {
  private session: CDPSession;
  private nextId = 1;
  private pending = new Map<number, (result: Record<string, unknown> | null) => void>();
  private workers: WorkerRecord[] = [];

  constructor(session: CDPSession) {
    this.session = session;
  }

  /** Start auto-attaching to new targets. */
  async init(): Promise<void> {
    this.session.on("Target.attachedToTarget", (event: Record<string, unknown>) => {
      void this.onAttached(event);
    });
    this.session.on("Target.receivedMessageFromTarget", (event: Record<string, unknown>) => {
      this.onMessage(event);
    });
    await this.session.send("Target.setAutoAttach", {
      autoAttach: true,
      waitForDebuggerOnStart: true,
      flatten: false,
    });
  }

  /** Forget the workers of the previous open. */
  beginOpen(): void {
    this.workers = [];
  }

  /** Stop profiling the open's workers and report their CPU time. */
  async endOpen(): Promise<{ url: string; cpuMs: number }[]> {
    const result: { url: string; cpuMs: number }[] = [];
    for (const worker of this.workers) {
      let cpuMs = 0;
      try {
        const stopped = await this.send(worker.sessionId, "Profiler.stop", {});
        const profile = (
          stopped as { profile?: { nodes?: { hitCount?: number; callFrame?: { functionName?: string } }[] } }
        )?.profile;
        // Samples on the idle node are the worker waiting for a message, not working.
        const samples = (profile?.nodes ?? []).reduce(
          (sum, node) => (node.callFrame?.functionName === "(idle)" ? sum : sum + (node.hitCount ?? 0)),
          0,
        );
        cpuMs = samples;
      } catch {
        cpuMs = worker.cpuMs ?? 0;
      }
      result.push({ url: worker.url, cpuMs });
    }
    this.workers = [];
    return result;
  }

  private async onAttached(event: Record<string, unknown>): Promise<void> {
    const sessionId = String(event.sessionId);
    const targetInfo = (event.targetInfo ?? {}) as { type?: string; url?: string };
    if (targetInfo.type !== "worker") {
      await this.send(sessionId, "Runtime.runIfWaitingForDebugger", {});
      return;
    }
    const worker: WorkerRecord = { sessionId, url: targetInfo.url ?? "", cpuMs: null };
    this.workers.push(worker);
    try {
      await this.send(sessionId, "Profiler.enable", {});
      await this.send(sessionId, "Profiler.setSamplingInterval", { interval: 1000 });
      await this.send(sessionId, "Profiler.start", {});
    } catch {
      /* a worker that cannot be profiled is still resumed below */
    }
    await this.send(sessionId, "Runtime.runIfWaitingForDebugger", {});
  }

  private onMessage(event: Record<string, unknown>): void {
    const message = event.message;
    if (typeof message !== "string") return;
    let parsed: { id?: number; result?: Record<string, unknown> };
    try {
      parsed = JSON.parse(message);
    } catch {
      return;
    }
    if (parsed.id === undefined) return;
    const resolvePending = this.pending.get(parsed.id);
    if (!resolvePending) return;
    this.pending.delete(parsed.id);
    resolvePending(parsed.result ?? null);
  }

  private send(sessionId: string, method: string, params: Record<string, unknown>): Promise<unknown> {
    const id = this.nextId;
    this.nextId += 1;
    return new Promise((resolvePromise) => {
      this.pending.set(id, resolvePromise);
      this.session
        .send("Target.sendMessageToTarget", { sessionId, message: JSON.stringify({ id, method, params }) })
        .catch(() => {
          this.pending.delete(id);
          resolvePromise(null);
        });
    });
  }
}

/** Compare two PNGs pixel by pixel through Chromium, so no image library is needed. */
class PixelComparator {
  private page: Page | null = null;
  private browser: Browser;

  constructor(browser: Browser) {
    this.browser = browser;
  }

  /** True when both images have the same size and the same pixels. */
  async equal(a: Buffer, b: Buffer): Promise<boolean> {
    if (a.equals(b)) return true;
    const page = await this.ensurePage();
    const result = await page.evaluate(
      async ([first, second]: [string, string]) => {
        const load = (dataUrl: string) =>
          new Promise<HTMLImageElement>((resolve, reject) => {
            const image = new Image();
            image.onload = () => resolve(image);
            image.onerror = () => reject(new Error("image did not load"));
            image.src = dataUrl;
          });
        const [imageA, imageB] = await Promise.all([load(first), load(second)]);
        if (imageA.width !== imageB.width || imageA.height !== imageB.height) return false;
        const draw = (image: HTMLImageElement) => {
          const canvas = document.createElement("canvas");
          canvas.width = image.width;
          canvas.height = image.height;
          const context = canvas.getContext("2d", { willReadFrequently: true });
          if (!context) throw new Error("no 2d context");
          context.drawImage(image, 0, 0);
          return context.getImageData(0, 0, canvas.width, canvas.height).data;
        };
        const dataA = draw(imageA);
        const dataB = draw(imageB);
        for (let i = 0; i < dataA.length; i += 1) {
          if (dataA[i] !== dataB[i]) return false;
        }
        return true;
      },
      [`data:image/png;base64,${a.toString("base64")}`, `data:image/png;base64,${b.toString("base64")}`] as [
        string,
        string,
      ],
    );
    return result;
  }

  /** Close the helper page. */
  async close(): Promise<void> {
    await this.page?.close().catch(() => undefined);
    this.page = null;
  }

  private async ensurePage(): Promise<Page> {
    if (!this.page || this.page.isClosed()) {
      this.page = await this.browser.newPage();
      await this.page.goto("about:blank");
    }
    return this.page;
  }
}

/** A fresh page in its own context, with the run's flags installed before navigation. */
async function openPage(
  context: BrowserContext,
  args: Args,
  condition: string,
  consoleFailures: string[],
): Promise<{
  page: Page;
  cdp: CDPSession;
  profiler: WorkerProfiler;
  network: Map<string, NetworkRecord>;
  requests: Map<string, string>;
  pending: Set<string>;
}> {
  const page = await context.newPage();
  const cdp = await context.newCDPSession(page);
  const network = new Map<string, NetworkRecord>();
  const requests = new Map<string, string>();
  const pending = new Set<string>();
  const startedAt = new Map<string, number>();

  page.on("console", (message) => {
    const text = message.text();
    if (FALLBACK_MESSAGES.some((needle) => text.includes(needle))) {
      consoleFailures.push(text);
    }
  });

  await cdp.send("Network.enable");
  await cdp.send("Performance.enable");
  if (condition === "cpu4x") await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
  if (condition === "slow4g") {
    await cdp.send("Network.emulateNetworkConditions", {
      offline: false,
      latency: 150,
      downloadThroughput: 1_600_000 / 8,
      uploadThroughput: 750_000 / 8,
    });
  }

  let navigationStartedAt: number | null = null;
  cdp.on("Network.requestWillBeSent", (event: Record<string, unknown>) => {
    const requestId = String(event.requestId);
    requests.set(requestId, String((event.request as { url?: string })?.url ?? ""));
    const timestamp = Number(event.timestamp ?? 0);
    if (navigationStartedAt === null) navigationStartedAt = timestamp;
    startedAt.set(requestId, Math.max(0, Math.round((timestamp - navigationStartedAt) * 1000)));
  });
  cdp.on("Network.responseReceived", (event: Record<string, unknown>) => {
    const response = (event.response ?? {}) as Record<string, unknown>;
    const headers = (response.headers ?? {}) as Record<string, string>;
    const requestId = String(event.requestId);
    pending.add(requestId);
    const previous = network.get(requestId);
    network.set(requestId, {
      url: String(response.url ?? requests.get(requestId) ?? ""),
      type: String(event.type ?? "Other"),
      startMs: startedAt.get(requestId) ?? 0,
      status: Number(response.status ?? 0),
      contentEncoding: headers["content-encoding"] ?? headers["Content-Encoding"] ?? null,
      cacheControl: headers["cache-control"] ?? headers["Cache-Control"] ?? null,
      fromCache: Boolean(response.fromDiskCache ?? response.fromPrefetchCache ?? false),
      encodedBytes: previous?.encodedBytes ?? 0,
    });
  });
  cdp.on("Network.loadingFinished", (event: Record<string, unknown>) => {
    const requestId = String(event.requestId);
    pending.delete(requestId);
    const record = network.get(requestId);
    if (record) record.encodedBytes = Number(event.encodedDataLength ?? 0);
  });
  cdp.on("Network.loadingFailed", (event: Record<string, unknown>) => {
    pending.delete(String(event.requestId));
  });

  await page.addInitScript(measurementScript(probesFirstPixel(args)));
  if (args.noWorker) await page.addInitScript(blockingScript("Worker"));
  if (args.noStorage) await page.addInitScript(blockingScript("indexedDB"));

  const profiler = new WorkerProfiler(cdp);
  await profiler.init();
  return { page, cdp, profiler, network, requests, pending };
}

/** The canvas the graph is drawn on, or null when nothing was drawn. */
async function canvasHandle(page: Page): Promise<Locator | null> {
  const canvases = page.locator(".ix-interchange-viewport canvas");
  try {
    await canvases.first().waitFor({ state: "attached", timeout: 10_000 });
  } catch {
    return null;
  }
  const count = await canvases.count();
  for (let index = 0; index < count; index += 1) {
    const locator = canvases.nth(index);
    const drawn = await locator.evaluate((element) => {
      const canvas = element as HTMLCanvasElement;
      if (canvas.width === 0 || canvas.height === 0) return false;
      const off = document.createElement("canvas");
      off.width = 32;
      off.height = 32;
      const context = off.getContext("2d", { willReadFrequently: true });
      if (!context) return false;
      context.drawImage(canvas, 0, 0, 32, 32);
      const pixels = context.getImageData(0, 0, 32, 32).data;
      for (let i = 3; i < pixels.length; i += 4) if (pixels[i] > 0) return true;
      return false;
    });
    if (drawn) return locator;
  }
  return canvases.first();
}

/** Wait until the canvas has not changed for SETTLE_IDENTICAL screenshots. */
async function settledCanvas(
  page: Page,
  locator: Locator,
  comparator: PixelComparator,
): Promise<Buffer> {
  await page.evaluate(
    () =>
      new Promise<void>((resolvePromise) => {
        requestAnimationFrame(() => requestAnimationFrame(() => resolvePromise()));
      }),
  );
  let previous = await locator.screenshot();
  let identical = 1;
  const started = Date.now();
  while (Date.now() - started < SETTLE_TIMEOUT_MS) {
    await page.waitForTimeout(SETTLE_INTERVAL_MS);
    const current = await locator.screenshot();
    if (await comparator.equal(previous, current)) {
      identical += 1;
      if (identical >= SETTLE_IDENTICAL) return current;
    } else {
      identical = 1;
    }
    previous = current;
  }
  throw new Error("the canvas did not settle within 10 s");
}

/** The CSS size of the canvas. */
async function canvasCssSize(locator: Locator): Promise<[number, number]> {
  return locator.evaluate((element) => {
    const canvas = element as HTMLCanvasElement;
    return [canvas.clientWidth, canvas.clientHeight] as [number, number];
  });
}

/** Read the long tasks and the scripting time of the open. */
async function readTimings(
  page: Page,
  cdp: CDPSession,
  windowEndMs: number,
): Promise<{ longTasks: { startMs: number; durationMs: number }[]; longestTaskMs: number; mainScriptingMs: number }> {
  const longTasks = await page.evaluate((end: number) => {
    const state = (window as unknown as { __measure?: { longTasks: { startMs: number; durationMs: number }[] } }).__measure;
    return (state?.longTasks ?? []).filter((task) => task.startMs < end);
  }, windowEndMs);
  const metrics = (await cdp.send("Performance.getMetrics")) as { metrics?: { name: string; value: number }[] };
  const scriptDuration = (metrics.metrics ?? []).find((metric) => metric.name === "ScriptDuration")?.value ?? 0;
  const durations = longTasks.map((task) => task.durationMs);
  return {
    longTasks,
    longestTaskMs: durations.length > 0 ? Math.max(...durations) : 0,
    mainScriptingMs: scriptDuration * 1000,
  };
}

/** Wait for the graph's first pixel, then for the measured window to close. */
async function waitForWindow(page: Page, probePixels: boolean): Promise<number> {
  if (probePixels) {
    const started = Date.now();
    for (;;) {
      const first = await page.evaluate(
        () => (window as unknown as { __measure?: { firstGraphPixelMs: number | null } }).__measure?.firstGraphPixelMs ?? null,
      );
      if (typeof first === "number") return first;
      if (Date.now() - started > FIRST_PIXEL_TIMEOUT_MS) {
        const diagnostic = await page
          .evaluate(() => ({
            error: (window as unknown as { __measureError?: string }).__measureError ?? null,
            measure: typeof (window as unknown as { __measure?: unknown }).__measure,
            canvases: document.querySelectorAll("canvas").length,
            viewport: document.querySelectorAll(".ix-interchange-viewport").length,
          }))
          .catch(() => null);
        throw new Error(
          `no graph pixel within ${FIRST_PIXEL_TIMEOUT_MS / 1000} s (${JSON.stringify(diagnostic)})`,
        );
      }
      await page.waitForTimeout(100);
    }
  }
  await page.waitForFunction(() => document.readyState === "complete", undefined, { timeout: FIRST_PIXEL_TIMEOUT_MS });
  const loadMs = await page.evaluate(
    () => (window as unknown as { __measure?: { loadMs: number | null } }).__measure?.loadMs ?? null,
  );
  if (typeof loadMs !== "number") throw new Error("the load mark was not recorded");
  return loadMs;
}

/** Wait until every request the open started has finished, so its bytes are final. */
async function drainNetwork(pending: Set<string>): Promise<void> {
  const started = Date.now();
  let quietSince: number | null = null;
  while (Date.now() - started < 5_000) {
    if (pending.size === 0) {
      quietSince ??= Date.now();
      if (Date.now() - quietSince >= 500) return;
    } else {
      quietSince = null;
    }
    await new Promise((resolvePromise) => setTimeout(resolvePromise, 100));
  }
}

/** Build the resource list of an open. */
async function readResources(
  cdp: CDPSession,
  network: Map<string, NetworkRecord>,
): Promise<Resource[]> {
  const resources: Resource[] = [];
  for (const [requestId, record] of network) {
    let decodedBytes = 0;
    if (!record.fromCache) {
      try {
        const body = (await cdp.send("Network.getResponseBody", { requestId })) as {
          body?: string;
          base64Encoded?: boolean;
        };
        decodedBytes = body.base64Encoded
          ? Buffer.from(body.body ?? "", "base64").length
          : Buffer.byteLength(body.body ?? "", "utf8");
      } catch {
        decodedBytes = 0;
      }
    }
    resources.push({
      url: record.url,
      type: record.type,
      startMs: record.startMs,
      encodedBytes: record.encodedBytes,
      decodedBytes,
      contentEncoding: record.contentEncoding,
      cacheControl: record.cacheControl,
      status: record.status,
      fromCache: record.fromCache,
    });
  }
  return resources.sort((a, b) => b.encodedBytes - a.encodedBytes);
}

/** Measure one open: first or repeat. */
async function measureOpen(
  args: Args,
  context: BrowserContext,
  condition: string,
  phase: "first" | "repeat",
  comparator: PixelComparator,
  canvasSink: (buffer: Buffer, size: [number, number]) => void,
  consoleMessages: string[],
  failures: string[],
): Promise<OpenReport> {
  const { page, cdp, profiler, network, pending } = await openPage(context, args, condition, consoleMessages);
  try {
    await page.goto(pageUrl(args), { waitUntil: "commit", timeout: 90_000 });
    const windowStart = await waitForWindow(page, probesFirstPixel(args));
    await page.waitForTimeout(3000);
    const windowEnd = windowStart + 3000;
    const timings = await readTimings(page, cdp, windowEnd);
    const workers = await profiler.endOpen();

    if (phase === "first" && condition === "cpu1x" && args.view === "full-graph") {
      const locator = await canvasHandle(page);
      if (!locator) {
        failures.push("the graph canvas was not found");
      } else {
        const size = await canvasCssSize(locator);
        measuredCanvasSize = size;
        try {
          const buffer = await settledCanvas(page, locator, comparator);
          canvasSink(buffer, size);
          if (args.interactionProbe) await interactionProbe(page, locator, buffer, comparator);
        } catch (error) {
          failures.push(`the canvas check failed: ${(error as Error).message}`);
        }
      }
    }

    await drainNetwork(pending);
    const resources = await readResources(cdp, network);
    return {
      totalBytes: resources.reduce((sum, resource) => sum + resource.encodedBytes, 0),
      longestTaskMs: timings.longestTaskMs,
      firstGraphPixelMs: probesFirstPixel(args) ? windowStart : null,
      mainScriptingMs: timings.mainScriptingMs,
      workers,
      longTasks: timings.longTasks,
      resources,
    };
  } finally {
    await page.close().catch(() => undefined);
  }
}

/** Hover a node, drag it 80 px, and fail if the picture moved. */
async function interactionProbe(
  page: Page,
  locator: Locator,
  before: Buffer,
  comparator: PixelComparator,
): Promise<void> {
  const candidates = await locator.evaluate((element) => {
    const canvas = element as HTMLCanvasElement;
    const context = canvas.getContext("2d", { willReadFrequently: true });
    if (!context) return [] as [number, number][];
    const width = canvas.width;
    const height = canvas.height;
    const pixels = context.getImageData(0, 0, width, height).data;
    // A node is an opaque disk; an edge is a thin opaque line and a hull is a wide
    // translucent fill, so only pixels at full opacity are candidates.
    const opaque = new Uint8Array(width * height);
    for (let i = 0; i < width * height; i += 1) opaque[i] = pixels[i * 4 + 3] >= 250 ? 1 : 0;
    const found: { x: number; y: number; density: number }[] = [];
    for (let y = 2; y < height - 2; y += 1) {
      for (let x = 2; x < width - 2; x += 1) {
        if (opaque[y * width + x] === 0) continue;
        let density = 0;
        for (let dy = -2; dy <= 2; dy += 1) {
          for (let dx = -2; dx <= 2; dx += 1) density += opaque[(y + dy) * width + x + dx];
        }
        if (density >= 18) found.push({ x, y, density });
      }
    }
    found.sort((a, b) => b.density - a.density);
    const points: [number, number][] = [];
    for (const candidate of found) {
      const px = (candidate.x * canvas.clientWidth) / width;
      const py = (candidate.y * canvas.clientHeight) / height;
      if (points.every(([qx, qy]) => Math.hypot(qx - px, qy - py) > 12)) points.push([px, py]);
      if (points.length >= 40) break;
    }
    return points;
  });
  if (candidates.length === 0) throw new Error("the interaction probe found no node to hover");

  const box = await locator.boundingBox();
  if (!box) throw new Error("the interaction probe found no canvas box");
  const label = page.locator(".graph-hover-label").first();
  let hovered = false;
  for (const point of candidates) {
    await page.mouse.move(box.x + point[0], box.y + point[1]);
    try {
      await label.waitFor({ state: "visible", timeout: 600 });
      hovered = true;
      break;
    } catch {
      /* try the next candidate */
    }
  }
  if (!hovered) throw new Error("the interaction probe found no node whose hover card appears");

  await page.mouse.down();
  await page.mouse.move(box.x + candidates[0][0] + 80, box.y + candidates[0][1], { steps: 10 });
  await page.mouse.up();
  await page.mouse.move(2, 2);
  await page.evaluate(
    () =>
      new Promise<void>((resolvePromise) => {
        requestAnimationFrame(() => requestAnimationFrame(() => resolvePromise()));
      }),
  );
  const after = await settledCanvas(page, locator, comparator);
  if (!(await comparator.equal(before, after))) {
    throw new Error("a drag moved the picture: the node is still draggable");
  }
}

/** The first graph pixel is a full-graph measurement; another view reports bytes only. */
function probesFirstPixel(args: Args): boolean {
  return !args.noPixelProbe && args.view === "full-graph";
}

/** True when the report carries a drawn graph. */
function drawn(report: OpenReport): boolean {
  return report.firstGraphPixelMs !== null;
}

/** Run one condition's runs and check that their bytes are equal. */
async function measureCondition(
  browser: Browser,
  args: Args,
  condition: string,
  comparator: PixelComparator,
  consoleMessages: string[],
  failures: string[],
): Promise<ConditionReport> {
  const runs: { first: OpenReport; repeat: OpenReport }[] = [];
  for (let run = 0; run < args.runs; run += 1) {
    const context = await browser.newContext({ viewport: VIEWPORT });
    try {
      let firstCanvas: Buffer | null = null;
      let firstSize: [number, number] = [0, 0];
      const first = await measureOpen(
        args,
        context,
        condition,
        "first",
        comparator,
        (buffer, size) => {
          firstCanvas = buffer;
          firstSize = size;
        },
        consoleMessages,
        failures,
      );
      const repeat = await measureOpen(args, context, condition, "repeat", comparator, () => undefined, consoleMessages, failures);
      runs.push({ first, repeat });
      if (condition === "cpu1x" && run === 0 && firstCanvas) {
        if (args.canvas) {
          mkdirSync(dirname(resolve(args.canvas)), { recursive: true });
          writeFileSync(resolve(args.canvas), firstCanvas);
        }
        if (args.compareCanvas) {
          try {
            const reference = readFileSync(resolve(args.compareCanvas));
            if (!(await comparator.equal(reference, firstCanvas))) {
              failures.push(`the settled canvas differs from ${args.compareCanvas}`);
            }
          } catch (error) {
            failures.push(`the canvas comparison failed: ${(error as Error).message}`);
          }
        }
        if (firstSize[0] === 0) failures.push("the canvas has no size");
      }
      if (args.noStorage && repeat.workers.length === 0) {
        failures.push("--no-storage: the repeat open did not lay out in a worker");
      }
      if (args.noWorker) {
        const warned = consoleMessages.some((message) => message.includes(FALLBACK_MESSAGES[1]));
        if (!warned) failures.push("--no-worker: the fallback warning is missing");
        if (!drawn(first)) failures.push("--no-worker: the graph was not drawn");
      }
    } finally {
      await context.close().catch(() => undefined);
    }
  }

  for (const phase of ["first", "repeat"] as const) {
    const bytes = runs.map((run) => run[phase].totalBytes);
    if (new Set(bytes).size > 1) {
      failures.push(`${condition}/${phase}: bytes differed between runs (${bytes.join(", ")})`);
    }
  }

  const pick = runs[0];
  const aggregate = (phase: "first" | "repeat"): OpenReport => ({
    totalBytes: pick[phase].totalBytes,
    longestTaskMs: median(runs.map((run) => run[phase].longestTaskMs)),
    firstGraphPixelMs:
      pick[phase].firstGraphPixelMs === null ? null : median(runs.map((run) => run[phase].firstGraphPixelMs ?? 0)),
    mainScriptingMs: median(runs.map((run) => run[phase].mainScriptingMs)),
    workers: pick[phase].workers,
    longTasks: pick[phase].longTasks,
    resources: pick[phase].resources,
  });
  return { first: aggregate("first"), repeat: aggregate("repeat") };
}

/** Measure every condition and write the report. */
async function main(): Promise<void> {
  let args: Args;
  try {
    args = parseArgs(process.argv.slice(2));
  } catch (error) {
    process.stderr.write(`${(error as Error).message}\n\n`);
    printUsage();
    process.exit(2);
  }

  const failures: string[] = [];
  const consoleMessages: string[] = [];
  const browser = await chromium.launch();
  const comparator = new PixelComparator(browser);
  let report: Report | null = null;
  try {
    const conditions: Record<string, ConditionReport> = {};
    for (const condition of args.conditions) {
      if (!["cpu1x", "cpu4x", "slow4g"].includes(condition)) throw new Error(`unknown condition ${condition}`);
      process.stderr.write(`measure: ${condition}\n`);
      conditions[condition] = await measureCondition(browser, args, condition, comparator, consoleMessages, failures);
      const result = conditions[condition];
      process.stderr.write(
        `  first: ${result.first.totalBytes} B, longest task ${Math.round(result.first.longestTaskMs)} ms, ` +
          `first pixel ${result.first.firstGraphPixelMs === null ? "n/a" : Math.round(result.first.firstGraphPixelMs) + " ms"}\n`,
      );
      process.stderr.write(
        `  repeat: ${result.repeat.totalBytes} B, first pixel ` +
          `${result.repeat.firstGraphPixelMs === null ? "n/a" : Math.round(result.repeat.firstGraphPixelMs) + " ms"}\n`,
      );
    }

    report = {
      tool: TOOL,
      commit: shortCommit(),
      maxitor: args.maxitor,
      source: args.source,
      viewport: [VIEWPORT.width, VIEWPORT.height],
      canvasSize: measuredCanvasSize,
      conditions,
      // With --no-worker the viewer's fallback warning is the point of the run, not a failure.
      consoleFailures: [
        ...new Set([
          ...consoleMessages.filter(
            (message) => !(args.noWorker && message.includes(FALLBACK_MESSAGES[1])),
          ),
          ...failures,
        ]),
      ],
      canvas: args.canvas ? resolve(args.canvas) : null,
    };
  } finally {
    await comparator.close().catch(() => undefined);
    await browser.close().catch(() => undefined);
  }

  if (!report) process.exit(1);
  const json = `${JSON.stringify(report, null, 2)}\n`;
  if (args.out) {
    mkdirSync(dirname(resolve(args.out)), { recursive: true });
    writeFileSync(resolve(args.out), json);
    process.stderr.write(`report: ${resolve(args.out)}\n`);
  } else {
    process.stdout.write(json);
  }

  if (report.consoleFailures.length > 0) {
    process.stderr.write(`failures:\n${report.consoleFailures.map((message) => `  - ${message}`).join("\n")}\n`);
    process.exit(1);
  }
  process.exit(0);
}

await main();
