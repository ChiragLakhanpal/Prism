// Ticket 126: each screen carries what the step needs, and the rest is tucked away (the design lead's inventory,
// docs/design/notes-2026-10-29/tuck-away-inventory.md). These tests check the inventory's first changes on the screens,
// at 1440 and 390 px: no byline words over an answer while every data-byline stays; one made-by window for each "No
// model wrote it" line, with its date kept as a number; the Documents tab's "Not read" note in the Pages read window;
// and the answer panel's check block, with "Checked" and "Judged by a model" on first sight and the rest in "How was
// that checked?". The sentences are the inventory's and the copy file's, copied here so the test checks the screen
// against an independent source. The pages' purposes are checked where each page's own tests open it
// (tests/shell.spec.ts walks the sidebar's sections and a project's tabs).
import type { Locator, Page } from "@playwright/test";
import { askFromTheBox, landed, open as openAnswer, panel } from "./answer-page";
import { hubApi } from "./hub-api";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

const WIDTHS = [1440, 390];

// Whether a reader sees these words: an element whose own text holds them, with a box larger than one pixel, so a
// screen-reader-only heading (1 by 1 px, clipped) does not count.
async function seen(page: Page, words: string): Promise<boolean> {
  return page.evaluate((words) => {
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    for (let node = walker.nextNode(); node; node = walker.nextNode()) {
      const element = node.parentElement;
      if (!element || !(node.textContent ?? "").includes(words)) continue;
      const box = element.getBoundingClientRect();
      if (box.width > 1 && box.height > 1 && getComputedStyle(element).visibility !== "hidden") return true;
    }
    return false;
  }, words);
}

// A window's trigger opens it on a press at every width, as a tap does (DefinitionWindow).
async function openWindow(trigger: Locator) {
  await trigger.click();
  return trigger.page().getByRole("dialog");
}

for (const width of WIDTHS) {
  test(`at ${width} px the answer opens on its sentences, with its byline for screen readers only, and its check block shows Checked and Judged by a model`, async ({ page }) => {
    await openAnswer(page, { stream: "ask-ke-nwwda-541055-past-range.sse", width });
    await askFromTheBox(page);
    await landed(page);

    // No byline words on screen; the answer's h3 keeps them for a screen reader, with its data-byline.
    for (const words of ["Prism, in short", "Prism found", "Prism held back"]) expect(await seen(page, words), words).toBe(false);
    const byline = panel(page).getByRole("heading", { level: 3, name: "Prism, in short" });
    await expect(byline).toHaveAttribute("data-byline", "inShort");
    const size = await byline.evaluate((element) => element.getBoundingClientRect());
    expect(size.width * size.height).toBeLessThanOrEqual(1);
    // "Asked within P130164." said what the question's heading names.
    await expect(panel(page).locator("[data-asked]")).toHaveCount(0);

    // The check block: Checked and Judged by a model on first sight; nothing else.
    const line = panel(page).locator("[data-check-line]");
    await expect(line.locator("[data-check-part=checked]")).toHaveText("Checked: 5 of 5 numbers match records.");
    await expect(line.locator("[data-check-part=judged]")).toHaveText("Judged by a model: 1 of 1 sentence follows from its sources.");
    await expect(line.locator("[data-check-part=not-checked]")).toHaveCount(0);
    // Nothing was removed, so there is no removed box to say so.
    await expect(panel(page).locator("[data-removed-box]")).toHaveCount(0);

    // The rest is in "How was that checked?": what was not checked, and the sentences that needed no model.
    await panel(page).getByRole("button", { name: "How was that checked?" }).click();
    const window = page.getByRole("dialog", { name: "How I checked this answer" });
    await expect(window.locator("[data-how-not-checked]")).toHaveText("Not checked: whether these are the right comparables.");
    await expect(window).toContainText("The other two needed no model, because every number, date and quote in them matched a record or a page.");
  });

  test(`at ${width} px the Summary's made-by line is in its window at the end of the finding, with its date, and the Documents tab's Not read note is in the Pages read window`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page, await hubApi());
    await page.goto("/projects/P130164");
    await expect(page.locator("[data-summary-lead]")).toBeVisible();

    expect(await seen(page, "No model wrote it")).toBe(false);
    const madeBy = page.locator("[data-summary-lead] [data-made-by]").getByRole("button", { name: "How I built this summary" });
    const box = (await madeBy.boundingBox())!;
    expect([box.width, box.height]).toEqual([24, 24]);
    const window = await openWindow(madeBy);
    await expect(window.getByRole("heading", { name: "How I built this summary" })).toBeVisible();
    await expect(window.locator("[data-made-by-sentence]")).toHaveText("I built this summary from World Bank records as of October 23, 2026. No model wrote it.");
    await expect(window.locator("[data-made-by-sentence] [data-num]")).toHaveText("October 23, 2026");
    await page.keyboard.press("Escape");

    await page.goto("/projects/P130164/documents");
    await expect(page.locator("[data-documents=ready]")).toBeVisible();
    // No purpose over the grouped table, no count line, and no note under it.
    expect(await seen(page, "These are the documents the World Bank published")).toBe(false);
    expect(await seen(page, "Showing")).toBe(false);
    expect(await seen(page, "means I list the document but haven't read its pages")).toBe(false);
    // The Pages read window says it: in the table's head from 768 px, on a card that says Not read below it.
    const pagesRead = page.locator(width >= 768 ? "[data-view=table] thead" : "[data-view=cards]").getByRole("button", { name: "Pages read" }).first();
    const definition = await openWindow(pagesRead);
    await expect(definition).toContainText("\"Not read\" means I list the document but haven't read its pages.");
  });

  test(`at ${width} px Data readiness, Following and Home each say who made them in one made-by window, with their dates`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await mockApi(page, {
      ...(await viewAnswers()),
      "/api/me": { body: await recorded("me-staff.json") },
      "/api/freshness": { body: await recorded("freshness.json") },
      "/api/home": { body: await recorded("home.json") },
      "/api/data/readiness": { body: await recorded("data-readiness.json") },
      "/api/following": { body: await recorded("following-p156634.json") },
    });

    await page.goto("/data");
    await expect(page.locator("[data-headline]")).toBeVisible();
    expect(await seen(page, "No model wrote it")).toBe(false);
    let window = await openWindow(page.locator("[data-headline] [data-made-by]").getByRole("button", { name: "How I built this headline" }));
    await expect(window).toContainText("I built this from the measures below, taken October 23, 2026. No model wrote it.");
    await page.keyboard.press("Escape");

    await page.goto("/projects/following");
    await expect(page.locator("[data-following-page=ready]")).toBeVisible();
    expect(await seen(page, "No model wrote this list")).toBe(false);
    window = await openWindow(page.locator("[data-made-by]").getByRole("button", { name: "How I made this list" }));
    await expect(window).toContainText("I ran these seven checks on October 22, 2026, on public records through October 22, 2026. No model wrote this list.");
    await page.keyboard.press("Escape");

    await page.goto("/");
    await expect(page.locator("[data-home=ready]")).toBeVisible();
    expect(await seen(page, "Fixed checks, no model")).toBe(false);
    window = await openWindow(page.locator("[data-worth] [data-made-by]").getByRole("button", { name: "How I wrote these lines" }));
    await expect(window).toContainText("I wrote these lines from fixed checks on public records. No model wrote them.");
  });
}
