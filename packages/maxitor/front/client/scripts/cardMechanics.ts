// packages/maxitor/front/client/scripts/cardMechanics.ts
/**
 * cardMechanics — the card and the collapsing with a real mouse, in a real browser (spec 043).
 *
 * What a unit test cannot do lives here: a hover needs trusted events, a drag needs the pan's own listeners, a place on
 * screen needs a layout. Each case once broke by hand on the way here, or could: a chart stuck to the pointer after a collapse,
 * a card lost on the way to it, a card blinking between rows, a card opening during a drag, a follower's card that
 * showed less than its leader's. ``check-layout-determinism.ts`` runs them in the check run and exits 1 on any ``DIFF``.
 */
import type { Browser, BrowserType, Page } from "playwright";

export type CardCase = { name: string; ok: boolean; detail: string };

/** What the caller's check run already knows how to do. */
export type CardHelpers = {
  drawn: (page: Page) => Promise<unknown>;
  openRoom: (leader: Page, follower: Page) => Promise<void>;
};

const CARD = '[data-testid="element-card"]';
const READABLE_ROW_PX = 14;
const AFTER_REST_MS = 700;
const AFTER_LEAVE_MS = 500;
const NOT_YET_MS = 120;
/** The most a kept header may stand off, and a collapsed table's width may differ, in screen pixels. */
const KEPT_PX = 1.5;

type Point = { x: number; y: number };

/** Whether a card shows: one may be on the page, unseen, while it waits for what it reads. */
function cardShown(page: Page): Promise<boolean> {
  return page.evaluate((selector) => {
    const card = document.querySelector(selector);
    return card !== null && getComputedStyle(card).visibility === "visible";
  }, CARD);
}

function cardText(page: Page): Promise<string> {
  return page.evaluate((selector) => document.querySelector<HTMLElement>(selector)?.innerText ?? "", CARD);
}

function transform(page: Page): Promise<string> {
  return page.evaluate(() => document.querySelector<HTMLElement>(".erd-svg-panner")!.style.transform);
}

/** Press + until a row reads, or - until it does not. */
async function zoomUntil(page: Page, readable: boolean): Promise<void> {
  await page.evaluate(
    async ({ readable, least }) => {
      const button = document.querySelector<HTMLElement>(`button[aria-label="Zoom ${readable ? "in" : "out"}"]`)!;
      const height = () => document.querySelector(`g[id^="a_fn"]`)?.getBoundingClientRect().height ?? 0;
      for (let step = 0; step < 40 && (readable ? height() < least : height() >= 10); step += 1) {
        button.click();
        await new Promise((resolve) => setTimeout(resolve, 40));
      }
    },
    { readable, least: READABLE_ROW_PX },
  );
  await page.waitForTimeout(300);
}

/** The centres of what ``selector`` finds that the pointer can reach now, in the order of the drawing. */
function reachable(page: Page, selector: string): Promise<(Point & { id: string; name: string; table: string })[]> {
  return page.evaluate((wanted) => {
    const found = [...document.querySelectorAll(wanted)].flatMap((cell) => {
      const box = cell.getBoundingClientRect();
      const [x, y] = [box.left + box.width / 2, box.top + box.height / 2];
      const hit = document.elementFromPoint(x, y);
      const same = hit !== null && (hit === cell || cell.contains(hit));
      return same ? [{ x, y, id: cell.id, name: cell.textContent?.trim().replace(/^[+−~] /, "") ?? "", table: cell.closest("g.node")?.id ?? "" }] : [];
    });
    return found;
  }, selector);
}

/** An empty corner of the diagram: the pointer on nothing. */
async function emptySpot(page: Page): Promise<Point> {
  return page.evaluate(() => {
    const box = document.querySelector(".erd-svg-viewport")!.getBoundingClientRect();
    for (let y = box.bottom - 70; y > box.top; y -= 23) {
      for (let x = box.right - 12; x > box.left; x -= 31) {
        const hit = document.elementFromPoint(x, y);
        if (hit?.closest(".erd-svg-viewport") && !hit.closest("g.node, g.edge")) return { x, y };
      }
    }
    return { x: box.left + 2, y: box.bottom - 70 };
  });
}

async function rest(page: Page, point: Point): Promise<void> {
  await page.mouse.move(point.x, point.y);
  await page.waitForTimeout(AFTER_REST_MS);
}

async function leave(page: Page): Promise<void> {
  const spot = await emptySpot(page);
  await page.mouse.move(spot.x, spot.y);
  await page.waitForTimeout(AFTER_LEAVE_MS);
}

/** The hover itself, with the pointer on one row, then on another and into the card. */
async function hoverCases(page: Page, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const rows = await reachable(page, 'g[id^="a_fn"]');
  const [first, second, third] = rows;
  if (!first || !second || !third) {
    say("rows to hover", false, `${rows.length} in reach`);
    return;
  }

  await page.mouse.move(first.x, first.y);
  await page.waitForTimeout(NOT_YET_MS);
  say("a card waits for the pointer to rest", !(await cardShown(page)));
  await page.waitForTimeout(AFTER_REST_MS);
  say("a resting pointer opens it, with its element's name", (await cardShown(page)) && (await cardText(page)).startsWith(first.name), await cardText(page));
  const label = await page.evaluate(() => [...document.querySelectorAll<HTMLElement>("[data-own-tooltip]")].some((each) => each.style.display === "block"));
  say("no old label beside it", !label);

  // Past another row, onto the card: the row passed over must not take the card away.
  const box = (await page.locator(CARD).boundingBox())!;
  const before = await cardText(page);
  await page.mouse.move(second.x, second.y);
  await page.waitForTimeout(100);
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 4 });
  await page.waitForTimeout(AFTER_REST_MS);
  say("the pointer reaches the card and it stays", (await cardShown(page)) && (await cardText(page)) === before, await cardText(page));

  await leave(page);
  say("it closes when the pointer has left", !(await cardShown(page)));

  await page.keyboard.press("Escape");
  await rest(page, first);
  await page.keyboard.press("Escape");
  await page.waitForTimeout(100);
  say("Escape closes it", !(await cardShown(page)));
  await leave(page);

  // Along the rows, without resting: nothing opens.
  let opened = false;
  for (const row of rows.slice(0, 8)) {
    await page.mouse.move(row.x, row.y);
    await page.waitForTimeout(40);
    opened ||= await cardShown(page);
  }
  say("a pointer passing by opens nothing", !opened);
  await leave(page);

  // From one row to the next: the old card stands until the new one takes its place.
  await rest(page, first);
  await page.mouse.move(third.x, third.y);
  let gap = false;
  for (let wait = 0; wait < 25; wait += 1) {
    gap ||= !(await cardShown(page));
    await page.waitForTimeout(20);
  }
  say("going to the next row never blinks", !gap && (await cardText(page)).startsWith(third.name), await cardText(page));
  await leave(page);

  await rest(page, first);
  await page.evaluate(() => document.querySelector<HTMLElement>('button[aria-label="Zoom in"]')!.click());
  await page.waitForTimeout(150);
  say("moving the picture closes the card", !(await cardShown(page)));
  await page.evaluate(() => document.querySelector<HTMLElement>('button[aria-label="Zoom out"]')!.click());
  await leave(page);
}

/** A card opens in one place: it never moves once seen. */
async function oneFrameCase(page: Page, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const [row] = await reachable(page, 'g[id^="a_fn"]');
  await page.evaluate((selector) => {
    const places = new Set<string>();
    (window as unknown as { cardPlaces: Set<string> }).cardPlaces = places;
    const watch = () => {
      const card = document.querySelector(selector);
      if (card && getComputedStyle(card).visibility === "visible") {
        const box = card.getBoundingClientRect();
        places.add(`${Math.round(box.left)},${Math.round(box.top)}`);
      }
      requestAnimationFrame(watch);
    };
    watch();
  }, CARD);
  await rest(page, row!);
  const places = await page.evaluate(() => [...(window as unknown as { cardPlaces: Set<string> }).cardPlaces]);
  say("a card appears in its place, in one frame", places.length === 1, places.join(" "));
  const fits = await page.evaluate((selector) => {
    const card = document.querySelector(selector)!.getBoundingClientRect();
    const stage = document.querySelector(".erd-svg-viewport")!.getBoundingClientRect();
    return card.top >= stage.top && card.bottom <= stage.bottom && card.left >= stage.left && card.right <= stage.right;
  }, CARD);
  say("a card stays on the stage", fits);
  await leave(page);
}

async function clickCase(page: Page, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const [row] = await reachable(page, 'g[id^="a_fn"]');
  await rest(page, row!);
  await page.mouse.down();
  await page.mouse.up();
  await page.waitForTimeout(150);
  const message = await page.evaluate(() => document.querySelector(".MuiSnackbarContent-message")?.textContent ?? "");
  say("a click copies the name and opens no card", message.includes(row!.name) && !(await cardShown(page)), message);
  await leave(page);
}

/** A drag: nothing opens under it, and it ends when the button is let go. */
async function dragCase(page: Page, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const [row] = await reachable(page, 'g[id^="a_fn"]');
  const start = await transform(page);
  await page.mouse.move(row!.x, row!.y);
  await page.mouse.down();
  await page.mouse.move(row!.x + 90, row!.y + 40, { steps: 6 });
  await page.waitForTimeout(AFTER_REST_MS);
  say("a drag moves the picture and opens no card", (await transform(page)) !== start && !(await cardShown(page)));
  await page.mouse.up();
  const dropped = await transform(page);
  await page.mouse.move(row!.x + 30, row!.y + 90, { steps: 4 });
  await page.waitForTimeout(100);
  say("letting go ends it", (await transform(page)) === dropped);
  await page.mouse.move(row!.x, row!.y, { steps: 4 });
  await page.mouse.down();
  await page.mouse.move(row!.x - 90, row!.y - 40, { steps: 6 });
  await page.mouse.up();
  await leave(page);
}

type Header = { left: number; top: number; width: number };

function header(page: Page, id: string): Promise<Header | null> {
  return page.evaluate((cell) => {
    const box = document.querySelector(`[id="${cell}"]`)?.getBoundingClientRect();
    return box ? { left: box.left, top: box.top, width: box.width } : null;
  }, id);
}

/** Collapsing one table: the chart stays free, the header stays put, the table keeps its width. */
async function collapseCases(page: Page, drawn: CardHelpers["drawn"], say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const [control] = await reachable(page, 'g[id^="a_cl"]');
  if (!control) {
    say("a control to collapse by", false);
    return;
  }
  const headerId = control.id.replace("a_cl", "a_hd");
  const before = (await header(page, headerId))!;
  await page.mouse.move(control.x, control.y);
  await page.mouse.down();
  await page.mouse.up();
  await drawn(page);
  await page.waitForTimeout(400);
  const after = await header(page, headerId);
  const hidden = await page.evaluate(() => document.body.textContent?.includes("hidden") ?? false);
  say("the control collapses its table", hidden && page.url().includes("except="));
  say("its header stays where it was", after !== null && Math.hypot(after.left - before.left, after.top - before.top) <= KEPT_PX, JSON.stringify({ before, after }));
  say("it keeps its width", after !== null && Math.abs(after.width - before.width) <= KEPT_PX, JSON.stringify({ before, after }));
  const placed = await transform(page);
  await page.mouse.move(control.x + 120, control.y + 80, { steps: 5 });
  await page.mouse.move(control.x - 80, control.y + 30, { steps: 5 });
  await page.waitForTimeout(100);
  const stuck = await page.evaluate(() => document.querySelector(".erd-svg-viewport")!.classList.contains("erd-panning"));
  say("the chart is not stuck to the pointer", (await transform(page)) === placed && !stuck);
  const [again] = (await reachable(page, 'g[id^="a_cl"]')).filter((each) => each.id === control.id);
  if (again) {
    await page.mouse.move(again.x, again.y);
    await page.mouse.down();
    await page.mouse.up();
    await drawn(page);
    await page.waitForTimeout(400);
  }
  say("the control opens it again", !(await page.evaluate(() => document.body.textContent?.includes("hidden") ?? false)));
  await leave(page);

  await page.evaluate(() => document.querySelector<HTMLElement>('[data-testid="collapse-all"]')!.click());
  await drawn(page);
  await page.waitForTimeout(400);
  const all = await page.evaluate(() => document.querySelector('[data-testid="collapse-all"]')!.getAttribute("aria-label"));
  say("the toolbar collapses all", all === "Expand all tables" && page.url().includes("collapsed=1"), all ?? "");
  await page.evaluate(() => document.querySelector<HTMLElement>('[data-testid="collapse-all"]')!.click());
  await drawn(page);
  await page.waitForTimeout(400);
}

/** A table's card: its list hidden at first, the choice kept for the next table. */
async function tableCases(page: Page, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const heads = await reachable(page, 'g[id^="a_hn"]');
  const [one, other] = heads;
  if (!one || !other) {
    say("tables to hover", false, `${heads.length} in reach`);
    return;
  }
  const count = () => page.evaluate(() => document.querySelectorAll('[data-testid="card-field"]').length);
  await rest(page, one);
  say("a table's fields start hidden", (await count()) === 0);
  const toggle = (await page.locator('[data-testid="card-fields-toggle"]').boundingBox())!;
  await page.mouse.move(toggle.x + 20, toggle.y + toggle.height / 2, { steps: 4 });
  await page.waitForTimeout(100);
  await page.mouse.down();
  await page.mouse.up();
  await page.waitForTimeout(100);
  say("the control shows them", (await count()) > 0);
  await leave(page);
  await rest(page, other);
  say("the choice holds for the next table", (await count()) > 0);
  await page.evaluate(() => localStorage.removeItem("maxitor:cardFieldsOpen"));
  await leave(page);
}

/** Switched off, cards open for nobody until switched on. */
async function switchCase(page: Page, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const [row] = await reachable(page, 'g[id^="a_fn"]');
  await page.evaluate(() => document.querySelector<HTMLElement>('[data-testid="hover-cards"]')!.click());
  await rest(page, row!);
  say("switched off, no card opens", !(await cardShown(page)));
  await leave(page);
  await page.evaluate(() => document.querySelector<HTMLElement>('[data-testid="hover-cards"]')!.click());
  await rest(page, row!);
  say("switched on, it opens again", await cardShown(page));
  await leave(page);
}

/** From afar a row cannot be aimed at: anywhere on a table is the whole table. */
async function afarCase(page: Page, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  await zoomUntil(page, false);
  const [row] = await reachable(page, 'g[id^="a_fn"]');
  if (!row) {
    say("a row from afar", false);
    return;
  }
  await rest(page, row);
  const toggle = await page.evaluate(() => document.querySelector('[data-testid="card-fields-toggle"]') !== null);
  say("from afar a row opens its table's card", toggle, await cardText(page));
  await leave(page);
  await zoomUntil(page, true);
}

/** A follower sees the card and what happens inside it. */
async function roomCases(engine: BrowserType, url: string, helpers: CardHelpers, say: (name: string, ok: boolean, detail?: string) => void): Promise<void> {
  const browsers: Browser[] = [await engine.launch(), await engine.launch()];
  try {
    const sizes = [{ width: 1440, height: 900 }, { width: 1320, height: 840 }];
    const [leader, follower] = await Promise.all(browsers.map(async (browser, index) => (await browser.newContext({ viewport: sizes[index]! })).newPage()));
    await leader!.goto(url);
    await helpers.drawn(leader!);
    await helpers.openRoom(leader!, follower!);
    await zoomUntil(leader!, true);
    await leader!.waitForTimeout(800);
    // The table nearest the middle: both screens show its card whole, so the two places can be compared.
    const middle = await leader!.evaluate(() => {
      const box = document.querySelector(".erd-svg-viewport")!.getBoundingClientRect();
      return { x: box.left + box.width / 2, y: box.top + box.height / 2 };
    });
    const heads = await reachable(leader!, 'g[id^="a_hn"]');
    const [head] = heads.sort((one, other) => Math.hypot(one.x - middle.x, one.y - middle.y) - Math.hypot(other.x - middle.x, other.y - middle.y));
    await rest(leader!, head!);
    await follower!.waitForTimeout(AFTER_REST_MS);
    const title = (await cardText(leader!)).split("\n")[0];
    say("a follower sees the card", (await cardText(follower!)).split("\n")[0] === title, await cardText(follower!));
    const toggle = (await leader!.locator('[data-testid="card-fields-toggle"]').boundingBox())!;
    await leader!.mouse.move(toggle.x + 20, toggle.y + toggle.height / 2, { steps: 4 });
    await follower!.waitForTimeout(AFTER_REST_MS);
    say("a follower's card stays while the leader is on it", await cardShown(follower!));
    await leader!.mouse.down();
    await leader!.mouse.up();
    await follower!.waitForTimeout(600);
    const rows = (page: Page) => page.evaluate(() => document.querySelectorAll('[data-testid="card-field"]').length);
    say("a follower sees the list open", (await rows(follower!)) > 0 && (await rows(follower!)) === (await rows(leader!)));
    const field = (await leader!.locator('[data-testid="card-field"]').first().boundingBox())!;
    await leader!.mouse.move(field.x + 40, field.y + field.height / 2, { steps: 3 });
    await follower!.waitForTimeout(600);
    const hint = (page: Page) => page.evaluate(() => document.querySelector('[data-testid="card-field-hint"]')?.textContent ?? "");
    say("a follower sees the field pointed at", (await hint(follower!)) === (await hint(leader!)) && !(await hint(follower!)).startsWith("Hover"), await hint(follower!));
    const spot = (page: Page) =>
      page.evaluate((selector) => {
        const card = document.querySelector(selector)!.getBoundingClientRect();
        const scale = new DOMMatrix(getComputedStyle(document.querySelector(".erd-svg-panner")!).transform).a;
        const picture = document.querySelector(".erd-svg-panner")!.getBoundingClientRect();
        return { x: (card.left - picture.left) / scale, y: (card.top - picture.top) / scale };
      }, CARD);
    const [here, there] = [await spot(leader!), await spot(follower!)];
    say("a follower's card stands on the same spot of the diagram, on a smaller screen", Math.hypot(here.x - there.x, here.y - there.y) <= 4, JSON.stringify({ here, there }));
    await leave(leader!);
    await follower!.waitForTimeout(600);
    say("a follower's card closes with the leader's", !(await cardShown(follower!)));
  } finally {
    await Promise.all(browsers.map((browser) => browser.close()));
  }
}

/** Every case, on the ERD of all domains at ``url``. */
export async function cardMechanics(engine: BrowserType, url: string, helpers: CardHelpers): Promise<CardCase[]> {
  const cases: CardCase[] = [];
  const say = (name: string, ok: boolean, detail = "") => void cases.push({ name, ok, detail: detail.replace(/\s+/g, " ").slice(0, 160) });
  const browser = await engine.launch();
  try {
    const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
    await page.goto(url);
    await helpers.drawn(page);
    await zoomUntil(page, true);
    await hoverCases(page, say);
    await oneFrameCase(page, say);
    await clickCase(page, say);
    await dragCase(page, say);
    await collapseCases(page, helpers.drawn, say);
    await tableCases(page, say);
    await switchCase(page, say);
    await afarCase(page, say);
  } finally {
    await browser.close();
  }
  await roomCases(engine, url, helpers, say);
  return cases;
}
