// Ticket 112's copy keys at seam 4, one page load per place: after the STEP reference in the package head, after the
// P-code in a project's header line, and in the evidence drawer's head. A press, Enter or Space puts exactly the ID or
// the source line on the clipboard; the icon becomes a check and the tooltip says "Copied" for 2 seconds; a polite
// status says it once; focus stays on the key; and nothing on its line moves. The words are the ticket's, copied here.
import type { Locator, Page } from "@playwright/test";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";
import { animationsDone, fontsLoaded } from "./settled";

const REF = "KE-NWWDA-541055-CW-RFB";
const ICR_54 = "strata.gold.passage:31525018/v1/54";

// The page's clipboard: every write is kept on the page, and a write fails while refuseCopy is set. The page's clock
// is installed, so a test runs it through the 2 seconds without waiting.
async function watchClipboard(page: Page) {
  await page.clock.install();
  await page.addInitScript(() => {
    const kept = window as unknown as { copied: string[]; refuseCopy: boolean };
    kept.copied = [];
    kept.refuseCopy = false;
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: async (text: string) => {
          if (kept.refuseCopy) throw new DOMException("The page may not write to the clipboard.", "NotAllowedError");
          kept.copied.push(text);
        },
      },
    });
  });
}

const boxes = (line: Locator[]) => Promise.all(line.map((part) => part.boundingBox()));

async function copiesThreeWays(page: Page, key: Locator, text: string, what: string, line: Locator[]) {
  const tooltip = page.getByRole("tooltip");
  // Measured once the page has come to rest: its fonts loaded and the drawer's slide ended.
  await fontsLoaded(page);
  await animationsDone(page);
  const before = await boxes(line);
  await key.hover();
  await expect(tooltip).toHaveText("Copy");
  await expect(key.locator("svg")).toHaveClass(/lucide-copy/);
  // From here the page's clock stands still, so "Copied" stays however slowly a busy computer runs the checks, until
  // the test moves the clock on.
  await page.clock.pauseAt(await page.evaluate(() => Date.now() + 1000));

  for (const press of ["click", "Enter", "Space"]) {
    if (press === "click") await key.click();
    else await page.keyboard.press(press);

    await expect(key, press).toBeFocused();
    await expect(key.locator("svg"), press).toHaveClass(/lucide-check/);
    await expect(tooltip, press).toHaveText("Copied");
    await expect(page.getByRole("status").filter({ hasText: `Copied ${what}.` }), press).toHaveCount(1);
    expect(await boxes(line), press).toEqual(before);
    await page.clock.fastForward(1900);
    await expect(tooltip, press).toHaveText("Copied");
    await page.clock.fastForward(200);
    await expect(key.locator("svg"), press).toHaveClass(/lucide-copy/);
    await expect(tooltip, press).toHaveText("Copy");
    // Said once: the status empties, so the next press says it again.
    await expect(page.getByRole("status").filter({ hasText: `Copied ${what}.` }), press).toHaveCount(0);
  }
  expect(await page.evaluate(() => (window as unknown as { copied: string[] }).copied)).toEqual([text, text, text]);

  await page.evaluate(() => ((window as unknown as { refuseCopy: boolean }).refuseCopy = true));
  await page.keyboard.press("Enter");
  await expect(tooltip).toHaveText("I couldn't copy it. Select the text instead.");
  await expect(key.locator("svg")).toHaveClass(/lucide-copy/);
  await expect(key).toBeFocused();
  await page.clock.resume();
}

// 24 by 24 px at 1440 and 390 px, and at 320 px on the same line as the ID's last characters.
async function keepsItsSizeAndItsId(page: Page, key: Locator, id: Locator) {
  for (const width of [1440, 390]) {
    await page.setViewportSize({ width, height: 900 });
    const size = (await key.boundingBox())!;
    expect([size.width, size.height], `${width} px`).toEqual([24, 24]);
  }
  await page.setViewportSize({ width: 320, height: 900 });
  const last = await id.evaluate((element) => {
    const rects = element.getClientRects();
    const { top, bottom } = rects[rects.length - 1];
    return { top, bottom };
  });
  const box = (await key.boundingBox())!;
  const middle = box.y + box.height / 2;
  expect(middle, "the key's middle lies on the ID's last line").toBeGreaterThan(last.top);
  expect(middle, "the key's middle lies on the ID's last line").toBeLessThan(last.bottom);
  // The page's charts follow the new width a frame later.
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
}

test("the package head's copy key copies the STEP reference", async ({ page }) => {
  await watchClipboard(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`/api/packages/${REF}`]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`/api/packages/${REF}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
  });
  await page.goto(`/packages/${REF}`);
  const head = page.locator("[data-package-header]");
  const key = head.getByRole("button", { name: "Copy the STEP reference" });
  await expect(key).toBeVisible();
  const id = head.locator("p").getByText(REF, { exact: true });

  await copiesThreeWays(page, key, REF, "the STEP reference", [head.locator("h1"), id, key]);
  await keepsItsSizeAndItsId(page, key, id);
});

test("a project's copy key after its P-code copies the P-code", async ({ page }) => {
  await watchClipboard(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    "/api/projects/P130164/summary": { body: await recorded("summary-p130164.json") },
  });
  await page.goto("/projects/P130164");
  const h1 = page.getByRole("main").getByRole("heading", { level: 1 });
  const key = h1.getByRole("button", { name: "Copy the project ID" });
  await expect(key).toBeVisible();
  // The header line reads as before: the key adds no words to it.
  await expect(h1).toHaveText("Rajasthan Road Sector Modernization · P130164 · India · closed");
  const id = h1.getByRole("link", { name: "P130164" });

  await copiesThreeWays(page, key, "P130164", "the project ID", [h1, id, key, h1.getByText("India", { exact: false })]);
  await keepsItsSizeAndItsId(page, key, id);
});

test("the evidence drawer's copy key, before its close, copies the source as one line", async ({ page }) => {
  await watchClipboard(page);
  await page.setViewportSize({ width: 1440, height: 900 });
  await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    "/api/projects/P130164/summary": { body: await recorded("summary-p130164.json") },
    "/api/evidence": { body: await recorded("evidence-icr-p130164-54.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
  });
  await page.goto(`/projects/P130164?evidence=${encodeURIComponent(ICR_54)}`);
  const drawer = page.getByRole("dialog");
  const key = drawer.getByRole("button", { name: "Copy the source" });
  const close = drawer.getByRole("button", { name: "Close the source" });
  await expect(key).toBeVisible();
  // Before the close button, on the heading's line.
  expect((await key.boundingBox())!.x).toBeLessThan((await close.boundingBox())!.x);
  const size = (await key.boundingBox())!;
  expect([size.width, size.height]).toEqual([24, 24]);

  await copiesThreeWays(
    page,
    key,
    "Rajasthan Road Sector Modernization, paragraph 54, Implementation Completion and Results Report, Rajasthan Road Sector Modernization (P130164), October 10, 2019, Section III.B, ¶54, PDF page 23 of 66",
    "the source",
    [drawer.getByRole("heading", { level: 2 }), key, close],
  );
});
