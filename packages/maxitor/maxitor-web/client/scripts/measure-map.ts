// scripts/measure-map.ts
/**
 * The map's measured session (spec 040, SC-001 – SC-006): opens a graph, zooms, pans, opens a domain and switches a
 * filter, and prints each number beside its threshold. Thresholds depend on the machine, so this runs by hand and not
 * in the check run. Measure a production build: the development server is about twice as slow.
 *
 *   node scripts/generate-large-graph.ts <stand graph> <folder>
 *   node scripts/measure-map.ts <graph-json URL> [front URL]
 */
import { chromium } from "playwright";
import type { Page } from "playwright";

const source = process.argv[2];
const front = process.argv[3] ?? "http://localhost:5173";
const WIDTH = 1600;
const HEIGHT = 900;

function line(name: string, value: number, threshold: number): void {
  console.log(`${value <= threshold ? "ok  " : "MISS"}  ${name.padEnd(44)} ${String(Math.round(value)).padStart(6)} ms   threshold ${threshold} ms`);
}

/** The longest frame while ``act`` runs. */
async function worstFrame(page: Page, act: () => Promise<void>): Promise<number> {
  await page.evaluate(() => {
    const seen = window as unknown as { frames_: number[]; going_: boolean };
    seen.frames_ = [];
    seen.going_ = true;
    let last = performance.now();
    const tick = (now: number) => {
      seen.frames_.push(now - last);
      last = now;
      if (seen.going_) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  });
  await act();
  return page.evaluate(() => {
    const seen = window as unknown as { frames_: number[]; going_: boolean };
    seen.going_ = false;
    return Math.max(...seen.frames_);
  });
}

/** From a click on a filter row to the second frame after it. */
function filterClick(page: Page, label: string): Promise<number> {
  return page.evaluate(async (name) => {
    const row = document.querySelector<HTMLElement>(`[data-testid=erd-filter-panel] button[aria-label="${name}"]`);
    const start = performance.now();
    row?.click();
    await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
    return performance.now() - start;
  }, label);
}

const browser = await chromium.launch({ headless: false, args: ["--use-angle=metal", "--ignore-gpu-blocklist"] });
const page = await browser.newPage({ viewport: { width: WIDTH, height: HEIGHT } });
await page.addInitScript(() => performance.setResourceTimingBufferSize(20_000));
const address = `${front}/?${new URLSearchParams({ source, view: "full-graph" }).toString()}`;
const opened = () => page.waitForFunction(() => document.querySelector("[data-layout-hash]")?.getAttribute("data-layout-hash"), null, { timeout: 170_000, polling: 50 });

await page.goto(address);
await opened();
await page.waitForTimeout(1500);
const started = Date.now();
await page.goto(address);
await opened();
line("SC-001 the overview on screen", Date.now() - started, 1000);
await page.waitForTimeout(2000);

const stage = await page.locator(".ix-interchange-viewport").boundingBox();
if (!stage) throw new Error("the map is not on screen");
await page.mouse.move(stage.x + stage.width * 0.6, stage.y + stage.height * 0.5);
line(
  "SC-002 worst frame, zooming in",
  await worstFrame(page, async () => {
    await page.keyboard.down("Control");
    for (let step = 0; step < 40; step += 1) {
      await page.mouse.wheel(0, -60);
      await page.waitForTimeout(40);
    }
    await page.keyboard.up("Control");
  }),
  100,
);
await page.waitForTimeout(1500);
line(
  "SC-002 worst frame, panning",
  await worstFrame(page, async () => {
    for (let step = 0; step < 60; step += 1) {
      await page.mouse.wheel(30, 0);
      await page.waitForTimeout(16);
    }
  }),
  100,
);
await page.waitForTimeout(800);

const areaReads = await page.evaluate(() => performance.getEntriesByType("resource").filter((each) => each.name.includes("/api/v1/map/area")).map((each) => each.duration));
line("SC-004 the longest domain read", Math.max(...areaReads), 200);

const panel = page.locator("[data-testid=erd-filter-panel]");
await panel.getByRole("button", { name: "Node types", exact: true }).first().click();
await page.waitForTimeout(300);
for (const name of ["Entity", "Entity", "Action", "Action"]) {
  line(`SC-003 filter ${name}, close`, await filterClick(page, name), 50);
  await page.waitForTimeout(600);
}
await page.goto(address);
await opened();
await page.waitForTimeout(2000);
await page.locator("[data-testid=erd-filter-panel]").getByRole("button", { name: "Node types", exact: true }).first().click();
await page.waitForTimeout(300);
for (const name of ["Entity", "Entity"]) {
  line(`SC-003 filter ${name}, far`, await filterClick(page, name), 50);
  await page.waitForTimeout(600);
}
await browser.close();
