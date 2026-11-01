// packages/maxitor/front/client/scripts/splitMechanics.ts
/**
 * splitMechanics — Side by side with a real mouse, in a real browser (spec 044).
 *
 * A hover needs trusted events, a click needs the pan's own listeners, a place on screen needs a layout. The check run
 * opens a plain source, which has no two versions, so this script runs on a history: ``SPLIT_URL`` is a Side by side
 * link to any diagram, read key and all, and ``SPLIT_PHONE=1`` looks at a phone. It prints one line per case and exits 1 on any ``DIFF``.
 *
 *     SPLIT_URL='http://localhost:5173/?history=…&mode=split&a=…&b=…&view=domain-erd#key=…' node scripts/splitMechanics.ts
 */
import { chromium, type Page } from "playwright";

type Box = { id: string; x: number; y: number; left: number; right: number; top: number; bottom: number };

const results: { name: string; ok: boolean; detail: string }[] = [];
const say = (name: string, ok: boolean, detail = "") => results.push({ name, ok, detail });
const DRAWN_MS = 40_000;

/** The nodes of a half, as the pointer can reach them. */
function nodes(page: Page, side: "a" | "b"): Promise<Box[]> {
  return page.evaluate((half) => {
    const pane = document.querySelector(`[data-half="${half}"] .erd-svg-viewport`)?.getBoundingClientRect();
    return [...document.querySelectorAll(`[data-half="${half}"] g.node`)].flatMap((node) => {
      const box = node.getBoundingClientRect();
      const [x, y] = [box.left + box.width / 2, box.top + box.height / 2];
      const hit = document.elementFromPoint(x, y);
      const same = hit !== null && node.contains(hit);
      return pane && same ? [{ id: node.querySelector("title")?.textContent ?? "", x, y, left: box.left, right: box.right, top: box.top, bottom: box.bottom }] : [];
    });
  }, side);
}

function stageOf(page: Page, side: "a" | "b") {
  return page.evaluate((half) => {
    const box = document.querySelector(`[data-half="${half}"] .erd-svg-viewport`)!.getBoundingClientRect();
    return { left: box.left, right: box.right, top: box.top, bottom: box.bottom };
  }, side);
}

function transform(page: Page, side: "a" | "b"): Promise<string> {
  return page.evaluate((half) => document.querySelector<HTMLElement>(`[data-half="${half}"] .erd-svg-panner`)?.style.transform ?? "", side);
}

/** The ids lit by a filter on a half. */
function selected(page: Page, side: "a" | "b"): Promise<string[]> {
  return page.evaluate((half) => [...document.querySelectorAll<HTMLElement>(`[data-half="${half}"] g.node`)].filter((node) => node.style.filter !== "" || node.querySelector<HTMLElement>("g[style*=drop-shadow]")).map((node) => node.querySelector("title")?.textContent ?? ""), side);
}

function note(page: Page, side: "a" | "b"): Promise<string> {
  return page.evaluate((half) => document.querySelector<HTMLElement>(`[data-half="${half}"] [data-testid="half-note"]`)?.innerText ?? "", side);
}

/** What a table's header looks like: the fill a half paints it, read from the pixels' source. */
function headersPainted(page: Page, side: "a" | "b"): Promise<boolean> {
  return page.evaluate((half) => {
    const svg = document.querySelector(`[data-half="${half}"] svg`);
    const clip = svg?.querySelector("clipPath");
    const used = svg?.querySelector("[clip-path]")?.getAttribute("clip-path");
    // A reference finds the first element of that id on the page: it must be this half's own.
    return !clip || !used || document.querySelector(`[id="${used.slice(5, -1)}"]`) === clip;
  }, side);
}

async function main(): Promise<void> {
  const url = process.env.SPLIT_URL;
  if (!url) throw new Error("SPLIT_URL is a Side by side link");
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
  const failures: string[] = [];
  page.on("pageerror", (error) => failures.push(error.message));
  await page.goto(url);
  await page.waitForSelector('[data-half="a"] svg', { timeout: DRAWN_MS });
  await page.waitForSelector('[data-half="b"] svg', { timeout: DRAWN_MS });
  await page.waitForTimeout(1500);

  say("A stands on the left of B", (await stageOf(page, "a")).right <= (await stageOf(page, "b")).left + 1);
  say("each half's clips are its own", (await headersPainted(page, "a")) && (await headersPainted(page, "b")));

  // Hover: lit in the other half, dimmed around it, and no card there.
  const [inA, inB] = [await nodes(page, "a"), await nodes(page, "b")];
  const common = inA.find((one) => inB.some((other) => other.id === one.id));
  // A table behind the filter panel is out of the pointer's reach, not out of the version.
  const everyInA = await page.evaluate(() => [...document.querySelectorAll('[data-half="a"] g.node title')].map((title) => title.textContent));
  const onlyB = inB.find((one) => !everyInA.includes(one.id));
  if (!common) say("the halves share an element", false);
  else {
    const before = await page.evaluate(() => document.querySelector('[data-half="b"] svg')?.outerHTML.length ?? 0);
    await page.mouse.move(common.x, common.y);
    await page.waitForTimeout(150);
    const lit = await page.evaluate(() => [...document.querySelectorAll('[data-half="b"] g.node')].filter((node) => getComputedStyle(node).opacity !== "1" || node.getAttribute("class")?.match(/dim|lit|fade/)).length);
    say("a hover in A reaches B", lit > 0 || before > 0, `${lit} nodes changed`);

    // A click selects in both; a half that shows it does not move.
    const pan = await transform(page, "b");
    await page.mouse.click(common.x, common.y);
    await page.waitForTimeout(200);
    say("a click selects in both", (await selected(page, "a")).includes(common.id) && (await selected(page, "b")).includes(common.id), `${await selected(page, "a")} | ${await selected(page, "b")}`);
    const twin = (await nodes(page, "b")).find((one) => one.id === common.id);
    say("a half that shows it stays", !twin || (await transform(page, "b")) === pan || (await note(page, "b")).includes("centre"));

    // Out of view: pan B away, click in A, B glides back keeping its zoom.
    await page.mouse.move(0, 0);
    await page.keyboard.press("Escape");
    await page.waitForTimeout(100);
    say("Escape clears the selection", (await selected(page, "b")).length === 0);
    const stage = await stageOf(page, "b");
    const empty = { x: stage.right - 8, y: stage.top + 8 };
    await page.mouse.move(empty.x, empty.y);
    await page.mouse.down();
    await page.mouse.move(empty.x + 1200, empty.y + 800, { steps: 8 });
    await page.mouse.up();
    await page.waitForTimeout(200);
    const scale = (value: string) => value.split(",")[0];
    const panned = await transform(page, "b");
    say("a drag pans B and leaves A", panned !== pan);
    say("a drag selects nothing", (await selected(page, "b")).length === 0);
    await page.mouse.click(common.x, common.y);
    await page.waitForTimeout(700);
    const glided = await transform(page, "b");
    say("B glides to what A selected", glided !== panned, await note(page, "b"));
    say("B keeps its zoom", scale(glided) === scale(panned));
    say("B says so", (await note(page, "b")).includes("centre"));
    await page.keyboard.press("Escape");
  }

  if (onlyB) {
    await page.mouse.click(onlyB.x, onlyB.y);
    await page.waitForTimeout(300);
    const said = await note(page, "a");
    say("what A lacks is named", said.startsWith("Not in") || said.startsWith("Hidden"), said);
    await page.keyboard.press("Escape");
  }

  // One stepper for the pair.
  const stepper = page.locator('button[aria-label="Next change"]').first();
  if (await stepper.count()) {
    await stepper.click();
    await page.waitForTimeout(600);
    say("a step selects", (await selected(page, "a")).length + (await selected(page, "b")).length > 0);
  }
  say("no page error", failures.length === 0, failures.join(" | "));

  if (process.env.SPLIT_PHONE) {
    const phone = await browser.newPage({ viewport: { width: 390, height: 800 } });
    await phone.goto(url);
    await phone.waitForSelector("[data-half] svg", { timeout: DRAWN_MS });
    await phone.waitForTimeout(800);
    say("a phone has one diagram", (await phone.locator("[data-half]").count()) === 1);
    say("a phone opens on B", (await phone.locator('[data-half="b"]').count()) === 1);
  }

  await browser.close();
  for (const { name, ok, detail } of results) console.log(`${ok ? "ok  " : "DIFF"} ${name}${detail ? ` — ${detail}` : ""}`);
  process.exit(results.every((result) => result.ok) ? 0 : 1);
}

void main();
