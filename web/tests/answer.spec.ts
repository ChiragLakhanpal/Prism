// The answer panel and the evidence drawer (ticket 14) at seam 4. The panel plays the answer streams
// ticket 13's server writes, recorded byte for byte in tests/fixtures/api and checked against the server
// by tests/test_answer_stream.py, so the check line's counts on screen are the stream's. The words are
// the ticket's and the 14 design brief's, and the source's details are the ICR of October 10, 2019
// (tests/ground_truth/values.toml, icr-para-54), copied here so the test checks the screen against an
// independent source.
import AxeBuilder from "@axe-core/playwright";
import { readEvents } from "../src/lib/sse";
import { askFromTheBox, box, drawer, ICR_54, landed, marker, open, panel, QUESTION } from "./answer-page";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";

const META =
  "Implementation Completion and Results Report · Rajasthan Road Sector Modernization (P130164) · October 10, 2019 · Section III.B · ¶54 · PDF page 23 of 66";
const REMOVED = "I removed one sentence. It said bids were usually opened within 45 days, and no record supports that number.";
const CHECK_LINE =
  "Checked: 2 of 3 numbers match records; 1 of 1 date matches records; 2 of 2 quotes are on their pages. " +
  "Not checked: whether each sentence follows from its sources, or whether I found every passage that matters.";
const WCAG_22_AA = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

test("Ask this streams the answer into the panel under the band: steps one at a time, then In short, the check line and the removed box", async ({ page }) => {
  const seen = await open(page);

  await askFromTheBox(page);

  await landed(page);
  expect(seen.asked).toHaveLength(1);
  expect(seen.asked[0].postDataJSON()).toMatchObject({ question: QUESTION, scope: "P130164" });
  // Focus stays in the box, where people refine a question.
  await expect(box(page)).toBeFocused();
  await expect(panel(page).getByRole("heading", { level: 2 })).toHaveText(QUESTION);
  await expect(panel(page).getByText("Asked within P130164.")).toBeVisible();
  await expect(panel(page).getByRole("heading", { level: 3, name: "In short" })).toBeVisible();
  await expect(panel(page).locator("[data-in-short]")).toContainText("108 of 328 cases had to go through rebidding");
  await expect(marker(page, 1)).toHaveAccessibleName("Source 1: Implementation Completion and Results Report, October 10, 2019, paragraph 54");
  await expect(panel(page).locator("[data-check-line]")).toHaveText(CHECK_LINE);
  await expect(panel(page).locator("[data-removed-box]")).toHaveText(REMOVED);

  // The status line said each step once, in order, never a part of one, and then that the answer was ready.
  await expect.poll(() => page.evaluate(() => (window as unknown as { said: string[] }).said)).toEqual([
    "I'm reading your question.",
    "I'm searching the documents for P130164.",
    "I'm writing the answer.",
    "I'm checking each number and quote against the sources.",
    "The answer is ready. I removed one sentence that failed a check.",
  ]);
  await expect(panel(page)).toHaveAttribute("aria-busy", "false");
});

test("the panel sits in the page under the band, on columns 1 to 8 from 1024 px, above the page's own title", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);

  const card = (await panel(page).boundingBox())!;
  const band = (await page.locator("[data-box-band]").boundingBox())!;
  const title = (await page.locator("main h1").boundingBox())!;
  expect(card.y).toBeGreaterThanOrEqual(band.y + band.height);
  expect(card.y + card.height).toBeLessThan(title.y);
  // At 1440 px, columns 1 to 8: 8 columns of 78.67 px and 7 gutters of 32 px.
  expect(Math.round(card.width)).toBe(853);
});

test("the steps still to come are listed in muted text while the answer streams", async ({ page }) => {
  await open(page);
  await page.route("**/api/ask", () => undefined);

  await askFromTheBox(page);

  const steps = panel(page).locator("[data-steps] li");
  await expect(steps).toHaveText(["I'm reading your question.", "To do: write the answer.", "To do: check each number and quote against the sources."]);
  await expect(panel(page)).toHaveAttribute("aria-busy", "true");
  await expect(panel(page).locator("[data-check-line]")).toHaveCount(0);
});

// DESIGN.md section 3: Roboto Mono for IDs, so the P-code keeps one face from the Asked line to the steps.
test("the folded steps set the project ID in Roboto Mono, as the Asked line does", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);

  await panel(page).getByRole("button", { name: "Show the four steps I took" }).click();
  const found = panel(page).locator("[data-steps] li").filter({ hasText: "I found 10 passages for P130164." });
  await expect(found).toBeVisible();
  const faces = await panel(page).evaluate((element) =>
    Array.from(element.querySelectorAll("[data-asked] *, [data-steps] *"))
      .filter((child) => child.children.length === 0 && child.textContent === "P130164")
      .map((child) => getComputedStyle(child).fontFamily.split(",")[0].replaceAll('"', "")),
  );
  expect(faces).toEqual(["Roboto Mono", "Roboto Mono"]);

  // The answer ID under the opened steps starts on the steps' text edge, under the button's label.
  const textLeft = (element: Element) => {
    const range = document.createRange();
    range.selectNodeContents(element);
    return Math.round(range.getClientRects()[0].left);
  };
  const stepLeft = await found.locator(":scope > span").last().evaluate(textLeft);
  expect(await panel(page).locator("[data-steps] + p").evaluate(textLeft)).toBe(stepLeft);
});

test("hovering or focusing a marker shows the evidence card: stratum, title, highlighted excerpt and source line", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);

  await marker(page, 1).hover();
  const card = page.locator("[data-evidence-card]");
  await expect(card).toBeVisible();
  await expect(card).toContainText("Why · evaluation");
  await expect(card).toContainText("Rajasthan Road Sector Modernization, paragraph 54");
  await expect(card.locator("mark")).toHaveText("Highlight starts. 108 of 328 cases had to go through rebidding Highlight ends.");
  await expect(card.locator("[data-source]")).toHaveText(
    "Source: Implementation Completion and Results Report, P130164, October 10, 2019, paragraph 54, page 23.",
  );
  await page.mouse.move(5, 880);
  await expect(card).toBeHidden();

  await marker(page, 1).focus();
  await expect(card).toBeVisible();
});

test("clicking a marker opens the drawer beside the page at ICR paragraph 54, and Escape closes it and returns focus to the marker", async ({ page }) => {
  const seen = await open(page);
  await askFromTheBox(page);
  await landed(page);

  await marker(page, 1).click();

  await expect(drawer(page)).toHaveAccessibleName("Rajasthan Road Sector Modernization, paragraph 54");
  await expect(drawer(page)).toHaveAttribute("aria-modal", "false");
  await expect(drawer(page).locator("[data-meta-line]")).toHaveText(META);
  await expect(drawer(page).getByRole("heading", { level: 2 })).toBeFocused();
  await expect(drawer(page).locator("[data-passage] mark")).toContainText("108 of 328 cases had to go through rebidding");
  await expect(drawer(page).locator("[data-claim]")).toContainText("From the answer");
  await expect(drawer(page).getByRole("link", { name: /Open at page 23 in the World Bank's PDF/ })).toHaveAttribute(
    "href",
    /#page=23$/,
  );
  expect(new URL(page.url()).searchParams.get("evidence")).toBe(ICR_54);
  await expect(marker(page, 1)).toHaveAttribute("aria-expanded", "true");
  await expect(panel(page).locator("[data-sentence-text='0']")).toHaveClass(/bg-tint/);

  // The drawer is clamp(400px, 40vw, 600px) wide and the page beside it stays usable.
  const width = Math.round((await drawer(page).boundingBox())!.width);
  expect(width).toBe(576);
  expect(Math.round((await page.locator("[data-page-column]").boundingBox())!.width)).toBe(1440 - 576);
  await box(page).click();
  await expect(box(page)).toBeFocused();
  await drawer(page).getByRole("heading", { level: 2 }).focus();

  await page.keyboard.press("Escape");

  await expect(drawer(page)).toHaveCount(0);
  await expect(marker(page, 1)).toBeFocused();
  // Focus coming back from the drawer does not cover the answer with the card again; focus a
  // person moves there does.
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  expect(new URL(page.url()).searchParams.get("evidence")).toBeNull();
  // The opened source shows its visited state, and was recorded once for this viewer.
  await expect(marker(page, 1)).toHaveAccessibleName(/, opened$/);
  expect(seen.opened.map((request) => request.postDataJSON().evidence_id)).toEqual([ICR_54]);
  expect(seen.opened[0].postDataJSON()).toMatchObject({ run_id: "run-0001", route: "/projects/P130164" });
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Tab");
  await expect(marker(page, 1)).toBeFocused();
  await expect(page.getByRole("tooltip")).toBeVisible();
});

test("closing the drawer gives focus back to its marker without covering the answer with its card, even with the pointer resting there", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);
  // The pointer stays where it clicked, so when the drawer closes the marker comes back under it.
  await marker(page, 1).click();
  await expect(drawer(page).getByRole("heading", { level: 2 })).toBeFocused();

  await page.keyboard.press("Escape");

  await expect(marker(page, 1)).toBeFocused();
  // Longer than the card's 150 ms hover delay.
  await page.waitForTimeout(400);
  await expect(page.getByRole("tooltip")).toHaveCount(0);
  // Moving the pointer off and back opens it, as hover always does.
  await page.mouse.move(5, 880);
  await marker(page, 1).hover();
  await expect(page.getByRole("tooltip")).toBeVisible();
});

test("at 1024 px the drawer is 40 percent of the window, and the page beside it takes the rest", async ({ page }) => {
  await open(page, { width: 1024 });
  await askFromTheBox(page);
  await landed(page);

  await marker(page, 1).click();

  expect(Math.round((await drawer(page).boundingBox())!.width)).toBe(410);
  expect(Math.round((await page.locator("[data-page-column]").boundingBox())!.width)).toBe(1024 - 410);
});

test("reloading with the evidence parameter reopens the drawer at that source, with no claim and no switcher", async ({ page }) => {
  await open(page, { path: `/projects/P130164?evidence=${encodeURIComponent(ICR_54)}` });

  await expect(drawer(page)).toHaveAccessibleName("Rajasthan Road Sector Modernization, paragraph 54");
  await expect(drawer(page).locator("[data-meta-line]")).toHaveText(META);
  await expect(drawer(page).locator("[data-claim]")).toHaveCount(0);
  await expect(drawer(page).getByRole("tablist")).toHaveCount(0);
  // Focus is not moved on a wide screen; the drawer is reachable by Tab.
  await expect(drawer(page).getByRole("heading", { level: 2 })).not.toBeFocused();

  await drawer(page).getByRole("button", { name: "Close the source" }).click();
  await expect(drawer(page)).toHaveCount(0);
  expect(new URL(page.url()).search).toBe("");
});

test("Back closes a drawer the page opened, and the answer stays", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);
  await marker(page, 1).click();
  await expect(drawer(page)).toBeVisible();

  await page.goBack();

  await expect(drawer(page)).toHaveCount(0);
  await expect(panel(page).locator("[data-in-short]")).toBeVisible();
  await page.goForward();
  await expect(drawer(page)).toBeVisible();
});

test("below 768 px the drawer is a full-screen sheet, and the page behind it is inert", async ({ page }) => {
  await open(page, { width: 390 });
  await askFromTheBox(page);
  await landed(page);

  await marker(page, 1).click();

  await expect(drawer(page)).toHaveAttribute("aria-modal", "true");
  // Once it has slid up, the sheet fills the window.
  await expect
    .poll(async () => {
      const sheet = (await drawer(page).boundingBox())!;
      return [sheet.x, sheet.y, sheet.width, sheet.height].map(Math.round);
    })
    .toEqual([0, 0, 390, 900]);
  await expect(page.locator("[data-page-column]")).toHaveAttribute("inert", "");
  await expect(drawer(page).getByRole("heading", { level: 2 })).toBeFocused();
  const close = (await drawer(page).getByRole("button", { name: "Close the source" }).boundingBox())!;
  expect([close.width, close.height]).toEqual([44, 44]);

  await page.keyboard.press("Escape");
  await expect(drawer(page)).toHaveCount(0);
  await expect(marker(page, 1)).toBeFocused();
});

test("an agent that does not respond gets an error alert and Try again, with the steps done so far", async ({ page }) => {
  await open(page, { stream: "ask-agent-unavailable.sse" });
  await askFromTheBox(page);

  const alert = panel(page).getByRole("alert");
  await expect(alert).toContainText("I couldn't reach the model that writes my answers. Your question is still in the box.");
  await expect(alert.getByRole("button", { name: "Try again" })).toBeVisible();
  // The run's ID, so a person can share it if it happens again.
  await expect(panel(page).getByText("Answer ID run-0001")).toBeVisible();
  await expect(panel(page).locator("[data-check-line]")).toHaveCount(0);
  await expect(box(page)).toHaveValue(QUESTION);
});

test("with no model connected, the panel says so and offers no Try again, since trying again cannot help", async ({ page }) => {
  await open(page, { stream: "ask-no-agent.sse" });
  await askFromTheBox(page);

  const alert = panel(page).getByRole("alert");
  await expect(alert).toContainText(
    "I can't answer questions yet, because the model that writes my answers isn't connected. Your question is still in the box.",
  );
  await expect(panel(page).getByRole("button", { name: "Try again" })).toHaveCount(0);
});

test("a stream that ends before its done event says the connection dropped", async ({ page }) => {
  const partial = (await recorded("ask-p130164-rebidding.sse")).split("event: sentence")[0];
  await open(page);
  await page.route("**/api/ask", (route) => route.fulfill({ contentType: "text/event-stream", body: partial }));

  await askFromTheBox(page);

  await expect(panel(page).getByRole("alert")).toContainText("The connection dropped before the answer was ready. Your question is still in the box.");
  await expect(panel(page).getByRole("button", { name: "Try again" })).toBeVisible();
});

test("a question a content filter stopped is a refusal, in plain words, with no alert and no check line", async ({ page }) => {
  await open(page, { stream: "ask-content-filter.sse" });
  await askFromTheBox(page);

  await expect(panel(page).locator("[data-in-short]")).toHaveText(
    "I can't answer this as written, because a content filter stopped the question. Try asking it in different words.",
  );
  await expect(panel(page).getByRole("alert")).toHaveCount(0);
  await expect(panel(page).locator("[data-check-line]")).toHaveCount(0);
  await expect(panel(page).getByRole("link", { name: "How Strata works" })).toHaveAttribute("href", "/data");
});

test("an agent that found nothing to cite says so for the scope, and Ask across all projects asks again with no chip", async ({ page }) => {
  const seen = await open(page, { stream: "ask-p130164-nothing-found.sse" });
  await askFromTheBox(page, "Which firms built the bridges in P130164?");

  await expect(panel(page).locator("[data-answer=empty]")).toContainText(
    "I found nothing in the records or documents for P130164 that answers this. You can ask the same question across all projects.",
  );
  await expect(panel(page).locator("[data-check-line], [data-removed-box]")).toHaveCount(0);
  await panel(page).getByRole("button", { name: "Ask across all projects" }).click();

  await expect.poll(() => seen.asked.length).toBe(2);
  expect(seen.asked[1].postDataJSON()).toMatchObject({ scope: null });
  await expect(page.getByRole("button", { name: "Remove the scope P130164" })).toHaveCount(0);
});

test("an answer whose every sentence failed a check says so, and lists each one with its reason", async ({ page }) => {
  await open(page, { stream: "ask-p130164-before-the-icr.sse" });
  await askFromTheBox(page);

  await expect(panel(page).locator("[data-in-short]")).toHaveText(
    "I don't have an answer I can support with a source. I wrote three sentences, and each one failed a check.",
  );
  await expect(panel(page).locator("[data-removed-lead]")).toHaveText("I removed all three sentences.");
  // A quote inside a removed sentence takes single quotes, so the marks do not pile up.
  await expect(panel(page).locator("[data-removed-box] li").first()).toHaveText(
    '"The completion report says the works contract estimates should have been based on the market rate, because ' +
      "'108 of 328 cases had to go through rebidding'.\" It cited a source I did not retrieve for this question.",
  );
  await expect(panel(page).locator("[data-check-line]")).toHaveCount(0);
});

// The recorded showcase stream, with one event changed, for shapes no recorded stream has yet. A change
// that returns a list puts those events in the one's place.
async function changed(stream: string, type: string, index: number, change: (data: any) => any) {
  return changedText(await recorded(stream), type, index, change);
}

function changedText(text: string, type: string, index: number, change: (data: any) => any) {
  let seen = -1;
  return text
    .split("\n\n")
    .map((block) => {
      if (!block.startsWith(`event: ${type}\n`)) return block;
      seen += 1;
      if (seen !== index) return block;
      const result = change(JSON.parse(block.split("\ndata: ")[1]));
      return (Array.isArray(result) ? result : [result]).map((data) => `event: ${type}\ndata: ${JSON.stringify(data)}`).join("\n\n");
    })
    .join("\n\n");
}

// An ISR numbers no paragraphs: ticket 11 keys each section ("s4") and marks the passage unnumbered.
// The showcase answer with its third sentence citing ISR 1's section on the PDO indicators
// (tests/ground_truth/values.toml, isr-1-pdo-indicators), then ICR paragraph 54, as no recorded stream
// does yet.
const ISR_S4 = "strata.gold.passage:19095337/v1/s4";
async function citingAnIsrSection() {
  const isr = JSON.parse(await recorded("evidence-isr-p130164-s4.json"));
  let stream = await changed("ask-p130164-removed-number.sse", "sentence", 2, (data) => ({
    ...data,
    text: "The first status report set an end target of 80.00 for the share of rural people with an all-season road.",
    evidence_ids: [ISR_S4, ICR_54],
    numbers: [{ text: "80.00", evidence_id: ISR_S4 }],
    dates: [],
  }));
  stream = changedText(stream, "evidence", 1, (data) => [data, isr]);
  return stream;
}

test("a sentence that cites an ISR section names the section, never a paragraph, in the card, a number's tooltip and the switcher", async ({ page }) => {
  const stream = await citingAnIsrSection();
  await open(page);
  await page.route("**/api/ask", (route) => route.fulfill({ contentType: "text/event-stream", body: stream }));
  await askFromTheBox(page);
  await landed(page);
  const sentence = panel(page).locator("[data-sentence-text='2']");
  const isrMarker = sentence.locator("[data-citation='3']");

  await expect(isrMarker).toHaveAccessibleName(
    "Source 3: Implementation Status and Results Report, February 22, 2014, section Project Development Objective Indicators",
  );
  await isrMarker.hover();
  const card = page.locator("[data-evidence-card]");
  await expect(card.locator("[data-source]")).toHaveText(
    "Source: Implementation Status and Results Report, P130164, February 22, 2014, section Project Development Objective Indicators, page 2.",
  );
  // The section is table text with no sentence ends, so the card quotes about 280 characters of it, cut
  // between words, and never cuts a number such as 80.00 at its decimal point.
  const quote = (await card.locator("[data-excerpt]").textContent())!;
  expect(quote).toContain("Percentage Value 67.00 67.00 80.00 season road");
  expect(quote.length).toBeLessThanOrEqual(290);
  expect(quote).toMatch(/ \S+…"$/);
  const cardText = await card.textContent();
  await page.mouse.move(5, 880);
  await expect(card).toBeHidden();

  await sentence.locator("[data-num]").hover();
  await expect(page.getByRole("tooltip")).toHaveText("Matches the section Project Development Objective Indicators of the status report for P130164.");

  await isrMarker.click();
  const tabs = drawer(page).getByRole("tab");
  await expect(tabs.first()).toHaveText("ISR, Project Development Objective Indicators");
  await expect(tabs.first()).toHaveAccessibleName("ISR, Project Development Objective Indicators");
  await expect(tabs.nth(1)).toHaveAccessibleName("ICR paragraph 54");
  await expect(drawer(page).locator("[data-meta-line]")).toHaveText(
    "Implementation Status and Results Report · Rajasthan Road Sector Modernization (P130164) · February 22, 2014 · " +
      "Section Project Development Objective Indicators · PDF page 2 of 4",
  );
  // The sentence quotes nothing, so no words are highlighted, and the drawer says so of the section.
  await expect(drawer(page)).toContainText("This sentence does not quote the section, so no words are highlighted.");
  await expect(drawer(page)).toContainText("The whole section, word for word.");
  for (const text of [cardText, await tabs.first().textContent(), await drawer(page).locator("[data-meta-line]").textContent()]) {
    expect(text).not.toMatch(/\bs4\b|¶/);
  }
});

test("a reason code with no sentence in the copy file makes no claim about the removed sentence", async ({ page }) => {
  const stream = await changed("ask-p130164-removed-number.sse", "removed", 0, (data) => ({ ...data, reason: "a_new_check", reasons: [{ check: 9, code: "a_new_check", text: null }] }));
  await open(page);
  await page.route("**/api/ask", (route) => route.fulfill({ contentType: "text/event-stream", body: stream }));
  await askFromTheBox(page);

  await expect(panel(page).locator("[data-removed-box]")).toHaveText(
    "I removed one sentence. It said bids were usually opened within 45 days, and it failed a check.",
  );
});

test("a date written before the numbers in a sentence is checkable too", async ({ page }) => {
  const stream = await changed("ask-p130164-removed-number.sse", "sentence", 2, (data) => ({
    ...data,
    text: "On October 10, 2019 the report counted 108 of 328 cases.",
    numbers: [
      { text: "108", evidence_id: ICR_54 },
      { text: "328", evidence_id: ICR_54 },
    ],
  }));
  await open(page);
  await page.route("**/api/ask", (route) => route.fulfill({ contentType: "text/event-stream", body: stream }));
  await askFromTheBox(page);
  await landed(page);

  await expect(panel(page).locator("[data-sentence-text='2'] [data-num]")).toHaveText(["October 10, 2019", "108", "328"]);
});

test("Close the answer closes the panel and its drawer, and returns focus to the box without opening its list", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);
  await marker(page, 1).click();
  await expect(drawer(page)).toBeVisible();

  await panel(page).getByRole("button", { name: "Close the answer" }).click();

  await expect(panel(page)).toHaveCount(0);
  await expect(drawer(page)).toHaveCount(0);
  expect(new URL(page.url()).searchParams.get("evidence")).toBeNull();
  await expect(box(page)).toBeFocused();
  // The question is still in the box, but its list stays shut over the page you return to (the 14
  // brief, section 6.4), until you press Down or type.
  await expect(box(page)).toHaveValue(QUESTION);
  await expect(box(page)).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.press("ArrowDown");
  await expect(box(page)).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
  await expect(box(page)).toHaveAttribute("aria-expanded", "false");
  await page.keyboard.type("?");
  await expect(box(page)).toHaveAttribute("aria-expanded", "true");
});

// CLAUDE.md rule 2: a drawer opened from the old answer must never pair the new answer's sentence
// with the old answer's source.
test("a new question closes the drawer the old answer opened, and tints no sentence of the new answer", async ({ page }) => {
  const seen = await open(page);
  await askFromTheBox(page);
  await landed(page);
  await marker(page, 1).click();
  await expect(drawer(page).locator("[data-claim]")).toBeVisible();

  await box(page).focus();
  await page.keyboard.press("Enter");

  await expect.poll(() => seen.asked.length).toBe(2);
  await landed(page);
  await expect(drawer(page)).toHaveCount(0);
  expect(new URL(page.url()).searchParams.get("evidence")).toBeNull();
  await expect(panel(page).locator("[data-sentence-text].bg-tint")).toHaveCount(0);
  await expect(marker(page, 1)).toHaveAttribute("aria-expanded", "false");
});

test("a drawer opened from a link stays open when you ask a question", async ({ page }) => {
  await open(page, { path: `/projects/P130164?evidence=${encodeURIComponent(ICR_54)}` });
  await expect(drawer(page)).toBeVisible();

  await askFromTheBox(page);
  await landed(page);

  await expect(drawer(page)).toBeVisible();
  await expect(drawer(page).locator("[data-claim]")).toHaveCount(0);
  await expect(panel(page).locator("[data-sentence-text].bg-tint")).toHaveCount(0);
});

// The server applies no view's rules until ticket 40 (src/strata/server/app.py), so the answer must not
// say it was asked in a preview; the alert above it says what the page shows instead.
test("an answer asked with ?view=public names no preview, and page alerts sit above it", async ({ page }) => {
  await open(page, { path: "/projects/P130164?view=public" });
  await askFromTheBox(page);
  await landed(page);

  await expect(panel(page).locator("[data-asked]")).toHaveText("Asked within P130164.");
  const alert = (await page.locator("main [data-alert]").first().boundingBox())!;
  expect(alert.y + alert.height).toBeLessThanOrEqual((await panel(page).boundingBox())!.y);

  await marker(page, 1).click();
  await expect(drawer(page)).toContainText("The address asks for a preview, so I'm not recording the sources you open.");
});

test("the check line never uses the success state", async ({ page }) => {
  await open(page, { stream: "ask-p130164-rebidding.sse" });
  await askFromTheBox(page);
  await landed(page);

  const line = panel(page).locator("[data-check-line]");
  const look = await line.evaluate((el) => ({ background: getComputedStyle(el).backgroundColor, color: getComputedStyle(el).color }));
  expect(look).toEqual({ background: "rgb(231, 237, 243)", color: "rgb(61, 76, 92)" });
  await expect(line.locator("svg")).toHaveCount(0);
});

for (const width of [1440, 390]) {
  test(`axe finds no WCAG 2.2 AA violations in the answer and the open drawer at ${width} px`, async ({ page }) => {
    await open(page, { width });
    await askFromTheBox(page);
    await landed(page);
    await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
    let results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);

    await marker(page, 1).click();
    await expect(drawer(page)).toBeVisible();
    await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
    results = await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
    expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);
  });
}

test("a copied answer keeps its markers as [1] and drops the word joiners that tie them to their sentences", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);

  const copied = await page.evaluate(() => {
    const block = document.querySelector("[data-in-short]")!;
    const range = document.createRange();
    range.selectNodeContents(block);
    window.getSelection()!.removeAllRanges();
    window.getSelection()!.addRange(range);
    const data = new DataTransfer();
    block.dispatchEvent(new ClipboardEvent("copy", { clipboardData: data, bubbles: true, cancelable: true }));
    return data.getData("text/plain");
  });

  expect(copied).not.toContain("⁠");
  expect(copied).toContain('cases had to go through rebidding".[1]');
});

// The sheet is fixed and scrolls inside itself, so the page's own width stays 320 px whatever the sheet
// holds; its scrolling panel must not be wider than the screen either.
const sheetScrollsSideways = (page: Page) =>
  drawer(page)
    .locator(":scope > div")
    .evaluate((panel) => panel.scrollWidth > panel.clientWidth);

test("the answer reflows at 320 px with nothing scrolling sideways", async ({ page }) => {
  await open(page, { width: 320 });
  await askFromTheBox(page);
  await landed(page);

  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  await marker(page, 1).click();
  await expect(drawer(page)).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(320);
  expect(await sheetScrollsSideways(page)).toBe(false);
});

test("at 320 px a long section name wraps in the sheet's meta line, and the page part keeps to one line", async ({ page }) => {
  await open(page, { width: 320, path: `/projects/P130164?evidence=${encodeURIComponent(ISR_S4)}`, evidence: "evidence-isr-p130164-s4.json" });
  await expect(drawer(page).locator("[data-meta-line]")).toContainText("Section Project Development Objective Indicators");

  expect(await sheetScrollsSideways(page)).toBe(false);
  const pagePart = drawer(page).locator("[data-meta-part]").filter({ hasText: "PDF page 2 of 4" });
  expect(await pagePart.evaluate((part) => part.getClientRects().length)).toBe(1);
});

// The client side of the stream, moved here from ticket 13's stream.spec.ts: the panel reads the
// server's recorded stream as its events, in order, however the bytes arrive.

function streamOf(text: string, chunkSize: number): ReadableStream<Uint8Array> {
  const bytes = new TextEncoder().encode(text);
  let offset = 0;
  return new ReadableStream({
    pull(controller) {
      if (offset >= bytes.length) return controller.close();
      controller.enqueue(bytes.slice(offset, offset + chunkSize));
      offset += chunkSize;
    },
  });
}

async function collect(body: ReadableStream<Uint8Array>) {
  const events = [];
  for await (const event of readEvents(body)) events.push(event);
  return events;
}

const NO_AGENT = [
  { type: "error", data: { code: "no_agent" } },
  { type: "done", data: { run_id: "run-0001" } },
];

test("the client reads the server's recorded stream as its events, in order", async () => {
  expect(await collect(streamOf(await recorded("ask-no-agent.sse"), 4096))).toEqual(NO_AGENT);
});

test("the client reads the stream the same way when it arrives a few bytes at a time", async () => {
  const text = await recorded("ask-no-agent.sse");
  for (const size of [1, 3, 7]) {
    expect(await collect(streamOf(text, size))).toEqual(NO_AGENT);
  }
});

test("the client reads CRLF line ends, even when a chunk ends between CR and LF", async () => {
  const text = (await recorded("ask-no-agent.sse")).replaceAll("\n", "\r\n");
  for (const size of [1, 2, 3, 7]) {
    expect(await collect(streamOf(text, size))).toEqual(NO_AGENT);
  }
});

test("the client skips the server's keep-alive comments", async () => {
  const text = ": keep-alive\n\n" + (await recorded("ask-no-agent.sse")).replace("\n\n", "\n\n: keep-alive\n\n");
  expect(await collect(streamOf(text, 5))).toEqual(NO_AGENT);
});
