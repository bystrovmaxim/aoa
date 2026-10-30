// packages/maxitor/front/client/scripts/browserTab.ts
/**
 * browserTab — one browser tab, driven the same way whether Playwright opened it (Chromium, Firefox,
 * WebKit) or Safari itself did, through `safaridriver` and the W3C WebDriver protocol (spec 038).
 *
 * Playwright's WebKit is Safari's engine but not Safari: it paints in software, so it never shows what
 * the real browser's compositor does to a large drawing. The cross-engine check therefore drives the
 * real Safari as a fourth browser. `safaridriver` ships with macOS; it needs Safari's Develop menu
 * setting "Allow remote automation" turned on once, and runs one Safari session at a time.
 *
 * Only what the check needs is here: open an address, run a function in the page, type into a field,
 * press a key, move and press the mouse, take a screenshot. Nothing is added to the client for it.
 */
import { spawn, spawnSync } from "node:child_process";
import type { ChildProcess } from "node:child_process";
import type { Page } from "playwright";

/** A function the page runs: self-contained, one argument, a JSON-serialisable answer. */
export type InPage<A, R> = (arg: A) => R;

export interface BrowserTab {
  readonly name: string;
  goto(url: string): Promise<void>;
  url(): Promise<string>;
  evaluate<A, R>(fn: InPage<A, R>, arg: A): Promise<R>;
  /** Type ``text`` into the field ``selector`` names. */
  fill(selector: string, text: string): Promise<void>;
  /** Press ``key`` — ``Enter`` or ``Escape`` — on whatever has the focus. */
  press(key: "Enter" | "Escape"): Promise<void>;
  mouse(steps: { x: number; y: number; down?: boolean; up?: boolean }[]): Promise<void>;
  /** The visible part of the page as PNG bytes. */
  screenshot(): Promise<Buffer>;
  close(): Promise<void>;
}

/** Wait until ``fn`` answers something truthy in ``tab``, and return it. */
export async function waitInPage<A, R>(tab: BrowserTab, fn: InPage<A, R>, arg: A, timeoutMs: number, what: string): Promise<R> {
  const until = Date.now() + timeoutMs;
  for (;;) {
    const answer = await tab.evaluate(fn, arg);
    if (answer) return answer;
    if (Date.now() > until) throw new Error(`${tab.name}: timed out after ${timeoutMs} ms waiting for ${what}`);
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
}

/** A tab Playwright opened. */
export function playwrightTab(name: string, page: Page, close: () => Promise<void>): BrowserTab {
  return {
    name,
    goto: async (url) => void (await page.goto(url)),
    url: async () => page.url(),
    evaluate: (fn, arg) => page.evaluate(fn as (arg: unknown) => never, arg),
    fill: (selector, text) => page.locator(selector).first().fill(text),
    press: (key) => page.keyboard.press(key),
    mouse: async (steps) => {
      for (const step of steps) {
        await page.mouse.move(step.x, step.y);
        if (step.down) await page.mouse.down();
        if (step.up) await page.mouse.up();
        await page.waitForTimeout(30);
      }
    },
    screenshot: () => page.screenshot(),
    close,
  };
}

const KEYS = { Enter: "", Escape: "" } as const;

/** Why Safari cannot be driven here, or ``null`` when it can: macOS only, with remote automation allowed. */
export async function safariUnavailable(port: number): Promise<string | null> {
  if (process.platform !== "darwin") return "Safari runs on macOS only";
  const driver = await startSafariDriver(port).catch((error: unknown) => error as Error);
  if (driver instanceof Error) return driver.message;
  try {
    const answer = await webdriver(port, "POST", "/session", { capabilities: { alwaysMatch: { browserName: "safari" } } });
    const session = (answer as { sessionId?: string }).sessionId;
    if (!session) return String((answer as { message?: string }).message ?? "no session");
    await webdriver(port, "DELETE", `/session/${session}`);
    return null;
  } finally {
    driver.kill();
  }
}

function startSafariDriver(port: number): Promise<ChildProcess> {
  const driver = spawn("safaridriver", ["-p", String(port)], { stdio: "ignore" });
  return new Promise((resolve, reject) => {
    const until = Date.now() + 10_000;
    driver.once("error", reject);
    const poll = () =>
      fetch(`http://127.0.0.1:${port}/status`).then(
        () => resolve(driver),
        () => (Date.now() > until ? reject(new Error("safaridriver did not start")) : setTimeout(poll, 150)),
      );
    poll();
  });
}

async function webdriver(port: number, method: string, path: string, body?: unknown): Promise<unknown> {
  const answer = await fetch(`http://127.0.0.1:${port}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const { value } = (await answer.json()) as { value: unknown };
  return value;
}

/** Open Safari in a window of ``width`` × ``height``; the tab closes the window and the driver. */
export async function safariTab(port: number, width: number, height: number): Promise<BrowserTab> {
  const driver = await startSafariDriver(port);
  const created = (await webdriver(port, "POST", "/session", { capabilities: { alwaysMatch: { browserName: "safari" } } })) as { sessionId?: string; message?: string };
  if (!created.sessionId) {
    driver.kill();
    throw new Error(`Safari: ${created.message ?? "no session"}`);
  }
  const at = `/session/${created.sessionId}`;
  const call = async (method: string, path: string, body?: unknown) => {
    const value = await webdriver(port, method, `${at}${path}`, body);
    if (value && typeof value === "object" && "error" in value) throw new Error(`Safari ${path}: ${(value as { message?: string }).message}`);
    return value;
  };
  const actions = (list: unknown[]) => call("POST", "/actions", { actions: list });
  await call("POST", "/window/rect", { x: 0, y: 0, width, height });
  // Safari stops painting, and its animation frames, in a window other windows cover: the check would read an empty,
  // still picture. Its window is brought to the front; nobody may cover it while the check runs.
  spawnSync("osascript", ["-e", 'tell application "Safari" to activate']);
  return {
    name: "safari",
    goto: async (url) => void (await call("POST", "/url", { url })),
    url: async () => String(await call("GET", "/url")),
    evaluate: async (fn, arg) => (await call("POST", "/execute/sync", { script: `return (${fn.toString()})(arguments[0]);`, args: [arg] })) as never,
    fill: async (selector, text) => {
      // As Playwright does, wait for the field to be there — a dialog opens a moment after the click that asks for it —
      // and type into it the way React hears: the value through the input's own setter, then an ``input`` event.
      // Safari's element search missed a field inside a dialog's portal.
      const typed = (arg: { selector: string; text: string }) => {
        const input = document.querySelector<HTMLInputElement>(arg.selector);
        if (!input) return false;
        Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value")?.set?.call(input, arg.text);
        input.dispatchEvent(new Event("input", { bubbles: true }));
        return true;
      };
      const until = Date.now() + 30_000;
      while (!(await call("POST", "/execute/sync", { script: `return (${typed.toString()})(arguments[0]);`, args: [{ selector, text }] }))) {
        if (Date.now() > until) throw new Error(`Safari: no ${selector} after 30 s`);
        await new Promise((resolve) => setTimeout(resolve, 150));
      }
    },
    press: async (key) => {
      await actions([{ type: "key", id: "keyboard", actions: [{ type: "keyDown", value: KEYS[key] }, { type: "keyUp", value: KEYS[key] }] }]);
    },
    mouse: async (steps) => {
      const moves = steps.flatMap((step) => [
        { type: "pointerMove", x: Math.round(step.x), y: Math.round(step.y), origin: "viewport", duration: 30 },
        ...(step.down ? [{ type: "pointerDown", button: 0 }] : []),
        ...(step.up ? [{ type: "pointerUp", button: 0 }] : []),
      ]);
      await actions([{ type: "pointer", id: "mouse", parameters: { pointerType: "mouse" }, actions: moves }]);
    },
    screenshot: async () => Buffer.from(String(await call("GET", "/screenshot")), "base64"),
    close: async () => {
      await webdriver(port, "DELETE", at).catch(() => undefined);
      driver.kill();
    },
  };
}
