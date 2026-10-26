// The evidence drawer's feedback row (ticket 32) at seam 4: "Was this the right passage?" with "Wrong passage" and
// "Not useful" grouped at the end of the drawer as ghost buttons, an optional reason, one report sent, and what
// became of it. The answer is the showcase stream (tests/fixtures/api/ask-p130164-rebidding.sse), whose evidence
// events carry the server's feedback block, and the report answers are the server's (tests/record_retrieval_api.py).
// The words are the ticket's and the 32 design brief's, copied here so the test checks the copy file.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { askFromTheBox, drawer, ICR_54, landed, marker } from "./answer-page";
import { expect, mockApi, recorded, test, viewAnswers } from "./mocked";

const REASON = "It is about estimates in general, not why these contracts were advertised again.";

async function openAnswer(page: Page, width = 1440, { preview = false, mine = "feedback-mine-waiting.json", sent = "feedback-sent.json", limit = 0 } = {}) {
  const posted: unknown[] = [];
  let stream = await recorded("ask-p130164-rebidding.sse");
  if (preview) stream = stream.replaceAll('"allowed": true, "why_not": null', '"allowed": false, "why_not": "preview"');
  // The server's reason limit (config/thresholds.toml, retrieval.reason_max_chars), changed to show the row reads it.
  if (limit) stream = stream.replaceAll('"reason_max_chars": 500', `"reason_max_chars": ${limit}`);
  await page.setViewportSize({ width, height: 900 });
  await mockApi(page, {
    ...(await viewAnswers()),
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    "/api/projects/P130164/summary": { body: await recorded("summary-p130164.json") },
    "/api/ask": { body: stream },
    "/api/evidence": { body: await recorded("evidence-icr-p130164-54.json") },
    "/api/evidence/opened": { body: '{"opened":[],"recorded":true}' },
    "/api/feedback": { body: await recorded(mine) },
  });
  await page.route("**/api/feedback", async (route) => {
    if (route.request().method() !== "POST") return route.fallback();
    posted.push(route.request().postDataJSON());
    const answer = JSON.parse(await recorded(sent));
    return answer.status && answer.body
      ? route.fulfill({ status: answer.status, contentType: "application/json", body: JSON.stringify(answer.body) })
      : route.fulfill({ contentType: "application/json", body: JSON.stringify(answer) });
  });
  await page.goto(preview ? "/projects/P130164?view=piu" : "/projects/P130164");
  await expect(page.locator("main h1")).toBeVisible();
  await askFromTheBox(page);
  await landed(page);
  await marker(page, 1).click();
  await expect(drawer(page).locator("[data-feedback-row]")).toBeVisible();
  return posted;
}

const row = (page: Page) => drawer(page).locator("[data-feedback-row]");
const kind = (page: Page, name: string) => row(page).getByRole("button", { name, exact: true });

// The sheet slides in below 768 px: measure once it has stopped.
async function settle(page: Page) {
  await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
}

async function axe(page: Page) {
  await settle(page);
  const results = await scan(page, "[data-evidence-drawer]");
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
}

test("Wrong passage and Not useful sit together at the end of the drawer, after the paragraph, as ghost buttons", async ({ page }) => {
  await openAnswer(page);

  await expect(row(page).getByRole("heading", { level: 3 })).toHaveText("Was this the right passage?");
  for (const name of ["Wrong passage", "Not useful"]) {
    await expect(kind(page, name)).toHaveAttribute("data-toggle", "ghost");
    await expect(kind(page, name)).toHaveAttribute("aria-pressed", "false");
    const box = (await kind(page, name).boundingBox())!;
    expect(box.height).toBe(44);
  }
  const wrong = (await kind(page, "Wrong passage").boundingBox())!;
  const notUseful = (await kind(page, "Not useful").boundingBox())!;
  // Grouped on one line, 8 px apart, under the paragraph and its "Open at page" link, and never sticky.
  expect(Math.abs(wrong.y - notUseful.y)).toBeLessThan(1);
  expect(Math.round(notUseful.x - (wrong.x + wrong.width))).toBe(8);
  const link = (await drawer(page).getByRole("link", { name: "Open at page 23", exact: true }).boundingBox())!;
  expect(wrong.y).toBeGreaterThan(link.y + link.height);
  // The first label starts on the heading's edge, as a flush ghost button's does; only its 2 px border is between.
  const heading = (await row(page).getByRole("heading", { level: 3 }).boundingBox())!;
  const label = (await kind(page, "Wrong passage").locator("span").last().boundingBox())!;
  expect(Math.abs(label.x - heading.x)).toBeLessThanOrEqual(2);
  expect(await row(page).evaluate((el) => getComputedStyle(el).position)).toBe("static");
  expect(await axe(page)).toEqual([]);
});

test("a choice opens an optional reason field, Escape closes it before the drawer, and Send the report writes one report", async ({ page }) => {
  const posted = await openAnswer(page);

  await kind(page, "Wrong passage").click();
  await expect(kind(page, "Wrong passage")).toHaveAttribute("aria-pressed", "true");
  const field = row(page).getByRole("textbox", { name: "What was wrong with it? (optional)" });
  await expect(field).toBeFocused();
  await expect(row(page).getByText("A reviewer sees your question, the sentence that cited this paragraph, the paragraph and your reason.")).toBeVisible();
  await field.fill("Too general");
  // Switching kind keeps the text and changes the label.
  await kind(page, "Not useful").click();
  await expect(row(page).getByRole("textbox", { name: "What did you need that it didn't give? (optional)" })).toHaveValue("Too general");
  await row(page).getByRole("textbox").focus();
  await page.keyboard.press("Escape");
  await expect(row(page).getByRole("textbox")).toHaveCount(0);
  await expect(drawer(page)).toBeVisible();
  await expect(kind(page, "Not useful")).toBeFocused();
  expect(posted).toEqual([]);

  await kind(page, "Wrong passage").click();
  await expect(row(page).getByRole("textbox")).toHaveValue("Too general");
  await row(page).getByRole("textbox").fill(REASON);
  await row(page).getByRole("button", { name: "Send the report" }).click();

  const panel = row(page).locator("[data-outcome-panel]");
  await expect(panel).toBeFocused();
  await expect(panel).toContainText("You marked this as the wrong passage.");
  await expect(panel).toContainText("A person reviews every report before I rank a passage differently.");
  await expect(panel).toContainText(`Your reason: "${REASON}"`);
  await expect(panel.getByRole("button", { name: "Withdraw the report" })).toBeVisible();
  expect(posted).toEqual([{ evidence_id: ICR_54, run_id: "run-0001", sentence_id: expect.any(Number), kind: "wrong_passage", reason: REASON, view: "staff" }]);
  expect(await axe(page)).toEqual([]);
});

test("the reason field takes as many characters as the server allows", async ({ page }) => {
  await openAnswer(page, 1440, { limit: 200 });
  await kind(page, "Wrong passage").click();
  await expect(row(page).getByRole("textbox")).toHaveAttribute("maxlength", "200");
});

test("a report already sent from another tab shows that report, not a failure", async ({ page }) => {
  await openAnswer(page, 1440, { sent: "feedback-already-sent.json" });
  await kind(page, "Not useful").click();
  await row(page).getByRole("button", { name: "Send the report" }).click();

  const panel = row(page).locator("[data-outcome-panel]");
  await expect(panel).toBeVisible();
  await expect(panel).toContainText("You marked this as the wrong passage.");
  await expect(row(page).getByText("I couldn't send your report just now.")).toHaveCount(0);
});

test("reopening the passage for the same answer shows what a reviewer decided, with their reason", async ({ page }) => {
  await openAnswer(page, 1440, { mine: "feedback-mine-ranked-lower.json" });
  await kind(page, "Wrong passage").click();
  await row(page).getByRole("button", { name: "Send the report" }).click();
  await expect(row(page).locator("[data-outcome-panel]")).toBeVisible();

  await page.keyboard.press("Escape");
  await expect(drawer(page)).toHaveCount(0);
  await marker(page, 1).click();
  const panel = row(page).locator("[data-outcome-panel=success]");
  await expect(panel).toContainText("You marked this as the wrong passage on October 23, 2026.");
  await expect(panel).toContainText(
    "A reviewer agreed on October 23, 2026, so I now rank this paragraph lower for questions about rebidding and bid prices. I still show it when it is the only source.",
  );
  await expect(panel).toContainText('Their reason: "The paragraph is about estimates in general. Questions about these contracts need paragraph 55."');
  await expect(panel.getByRole("button", { name: "Withdraw the report" })).toHaveCount(0);
});

for (const width of [1024, 390]) {
  test(`at ${width} px both buttons fit on one line, the form fits the drawer, and axe finds no violations`, async ({ page }) => {
    await openAnswer(page, width);
    await settle(page);
    const wrong = (await kind(page, "Wrong passage").boundingBox())!;
    const notUseful = (await kind(page, "Not useful").boundingBox())!;
    expect(Math.abs(wrong.y - notUseful.y)).toBeLessThan(1);
    expect(await axe(page)).toEqual([]);
    await kind(page, "Not useful").click();
    const form = (await row(page).locator("form").boundingBox())!;
    const sheet = (await drawer(page).boundingBox())!;
    expect(form.x + form.width).toBeLessThanOrEqual(sheet.x + sheet.width);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
    expect(await axe(page)).toEqual([]);
    if (width === 390) {
      // Down to 320 px the two buttons stay on one line (the 32 brief, section 2.9).
      await page.setViewportSize({ width: 320, height: 900 });
      const narrowWrong = (await kind(page, "Wrong passage").boundingBox())!;
      const narrowNotUseful = (await kind(page, "Not useful").boundingBox())!;
      expect(Math.abs(narrowWrong.y - narrowNotUseful.y)).toBeLessThan(1);
    }
  });
}

test("in a preview the row shows with both buttons disabled and says why, and a bare link shows no row", async ({ page }) => {
  await openAnswer(page, 1440, { preview: true });
  for (const name of ["Wrong passage", "Not useful"]) {
    await expect(kind(page, name)).toHaveAttribute("aria-disabled", "true");
    await expect(kind(page, name)).toHaveAccessibleDescription(
      "This is a preview, so I'm not recording the sources you open, and you can't report a passage.",
    );
  }
  // Held, each is a bare label in the caption's ink-muted, so neither looks pressable.
  const muted = await row(page).getByText("This is a preview, so I'm not recording").evaluate((el) => getComputedStyle(el).color);
  expect(await kind(page, "Wrong passage").evaluate((el) => getComputedStyle(el).color)).toBe(muted);
  // A disabled button stays focusable and does nothing when pressed.
  await kind(page, "Wrong passage").focus();
  await page.keyboard.press("Enter");
  await expect(row(page).getByRole("textbox")).toHaveCount(0);
  // The old preview line gives way to the row's own.
  await expect(drawer(page).getByText("The address asks for a preview, so I'm not recording the sources you open.")).toHaveCount(0);

  await page.goto(`/projects/P130164?evidence=${encodeURIComponent(ICR_54)}`);
  await expect(drawer(page).getByRole("heading", { level: 2 })).toBeVisible();
  await expect(drawer(page).locator("[data-feedback-row]")).toHaveCount(0);
});
