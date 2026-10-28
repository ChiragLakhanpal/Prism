// The answer panel and the evidence drawer (ticket 14) at seam 4. The panel plays the answer streams
// ticket 13's server writes, recorded byte for byte in tests/fixtures/api and checked against the server
// by tests/test_answer_stream.py, so the check line's counts on screen are the stream's. The words are
// the ticket's and the 14 design brief's, and the source's details are the ICR of October 10, 2019
// (tests/ground_truth/values.toml, icr-para-54), copied here so the test checks the screen against an
// independent source.
import { scan } from "./axe";
import { readEvents } from "../src/lib/sse";
import { askFromTheBox, box, drawer, ICR_54, landed, marker, open, panel, QUESTION } from "./answer-page";
import type { Page } from "@playwright/test";
import { expect, recorded, test } from "./mocked";
import { animationsDone } from "./settled";
import { forgetTransitions, recordTransitions, transitionsOn, type Moved } from "./reveals";

const META =
  "Implementation Completion and Results Report · Rajasthan Road Sector Modernization (P130164) · October 10, 2019 · Section III.B · ¶54 · PDF page 23 of 66";
const REMOVED = "I removed one sentence. It said bids were usually opened within 45 days, and no record supports that number.";
// The check line counts the sentences on screen, and since ticket 24 every answer runs the fourth check, so
// "whether each sentence follows from its sources" is no longer a gap (the 24 brief, section 4.1).
const CHECK_LINE =
  "Checked: 2 of 2 numbers match records; 1 of 1 date matches records; 2 of 2 quotes are on their pages. " +
  "Not checked: whether I found every passage that matters.";

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
  // Ticket 111: Strata's own words open with its byline, which is the answer's h3. The project page's records, the
  // steps, the check line and the removed box have none.
  await expect(panel(page).getByRole("heading", { level: 3, name: "Strata, in short" })).toBeVisible();
  await expect(page.locator("[data-byline]")).toHaveText(["Strata, in short"]);
  await expect(panel(page).locator("[data-in-short]")).toContainText("108 of 328 cases had to go through rebidding");
  await expect(marker(page, 1)).toHaveAccessibleName("Source 1: Implementation Completion and Results Report, October 10, 2019, paragraph 54");
  await expect(panel(page).locator("[data-check-line]")).toHaveText(CHECK_LINE);
  await expect(panel(page).locator("[data-removed-box]")).toHaveText(REMOVED);

  // The status line said each step once, in order, never a part of one, and then that the answer was ready.
  await expect.poll(() => page.evaluate(() => (window as unknown as { said: string[] }).said)).toEqual([
    "I'm reading your question.",
    "I'm searching the documents for P130164.",
    "I'm writing the answer.",
    "I'm checking each sentence against its sources.",
    "The answer is ready. I removed one sentence that failed a check.",
  ]);
  await expect(panel(page)).toHaveAttribute("aria-busy", "false");
});

test("the panel sits at the top of the page column under the bar, on columns 1 to 8 from 1024 px, above the page's own title, with In short in label and its sentences in lead", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);

  const card = (await panel(page).boundingBox())!;
  const band = (await page.locator("[data-box-band]").boundingBox())!;
  const column = (await page.locator("[data-page-column]").boundingBox())!;
  const title = (await page.locator("main h1").boundingBox())!;
  expect(card.y).toBeGreaterThanOrEqual(band.y + band.height);
  // Ticket 94: the first thing in the page column, 40 px under its top from 1024 px, with the window's margin before it.
  expect(Math.round(card.y - column.y)).toBe(40);
  expect(Math.round(card.x - column.x)).toBe(40);
  expect(card.y + card.height).toBeLessThan(title.y);
  // At 1440 px the page area is 1376 px beside the rail, where the sidebar rests (ticket 110). The window's 40 px margins
  // leave 1296 px (ticket 94), so columns 1 to 8 are 8 columns of 78.67 px and 7 gutters of 32 px.
  expect(Math.round(card.width)).toBe(853);
  // The byline in label (13/16, 600, ink-muted), with "Strata" in the wordmark's weight (700) in ink-heading, 8 px
  // above its sentences in lead (18/28, 400), DESIGN.md sections 3 and 5 (ticket 111).
  const style = (element: Element) => [getComputedStyle(element).fontSize, getComputedStyle(element).lineHeight, getComputedStyle(element).fontWeight];
  const byline = panel(page).getByRole("heading", { level: 3, name: "Strata, in short" });
  expect(await byline.evaluate(style)).toEqual(["13px", "16px", "600"]);
  expect(await byline.evaluate((element) => getComputedStyle(element).color)).toBe("rgb(75, 94, 113)");
  const name = byline.getByText("Strata", { exact: true });
  expect(await name.evaluate(style)).toEqual(["13px", "16px", "700"]);
  expect(await name.evaluate((element) => getComputedStyle(element).color)).toBe("rgb(1, 39, 64)");
  expect(await panel(page).locator("[data-in-short]").evaluate(style)).toEqual(["18px", "28px", "400"]);
  const [over, under] = [(await byline.boundingBox())!, (await panel(page).locator("[data-in-short]").boundingBox())!];
  expect(Math.round(under.y - (over.y + over.height))).toBe(8);
});

test("the steps still to come are listed in muted text while the answer streams", async ({ page }) => {
  await open(page);
  await page.route("**/api/ask", () => undefined);

  await askFromTheBox(page);

  const steps = panel(page).locator("[data-steps] li");
  await expect(steps).toHaveText(["I'm reading your question.", "To do: write the answer.", "To do: check each sentence against its sources."]);
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
  // Ticket 21: "Open at page 23" opens the in-app source view at the page, with paragraph 54 to highlight.
  await expect(drawer(page).getByRole("link", { name: "Open at page 23", exact: true })).toHaveAttribute(
    "href",
    "/projects/P130164/documents/icr-2019-10-10?page=23&para=54",
  );
  expect(new URL(page.url()).searchParams.get("evidence")).toBe(ICR_54);
  await expect(marker(page, 1)).toHaveAttribute("aria-expanded", "true");
  await expect(panel(page).locator("[data-sentence-text='0']")).toHaveClass(/bg-tint/);

  // On a wide page the drawer is clamp(384px, 40vw, 560px) (ticket 94): 40 percent of 1440 px is 576, so 560 px, and
  // the page beside it, the 1376 px frame beside the rail less the drawer, stays usable.
  const width = Math.round((await drawer(page).boundingBox())!.width);
  expect(width).toBe(560);
  expect(Math.round((await page.locator("[data-page-column]").boundingBox())!.width)).toBe(816);
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

test("at 1024 px the drawer takes 40 percent of the window, 410 px, and the page beside the rail takes the rest", async ({ page }) => {
  await open(page, { width: 1024 });
  await askFromTheBox(page);
  await landed(page);

  await marker(page, 1).click();

  // 40 percent of the 1024 px window is 409.6 px, inside clamp(384px, 40vw, 560px) (ticket 94); the page beside the
  // 64 px rail (ticket 92) takes the rest.
  expect(Math.round((await drawer(page).boundingBox())!.width)).toBe(410);
  expect(Math.round((await page.locator("[data-page-column]").boundingBox())!.width)).toBe(550);
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

// The server answers 404 (unknown_evidence) for an ID it lacks and for a source not public by the as-of
// date (src/strata/server/app.py). The ICR of October 10, 2019 was not public on August 26, 2016, so an
// as-of link to it names the date as a reason, not only the link.
test("a link to a source as of a date before it was public says it may not have been public yet", async ({ page }) => {
  await open(page, { width: 390 });
  await page.route("**/api/evidence?**", (route) => route.fulfill({ status: 404, contentType: "application/json", body: '{"code":"unknown_evidence"}' }));
  await page.goto(`/projects/P130164?asof=2016-08-26&evidence=${encodeURIComponent(ICR_54)}`);

  await expect(drawer(page)).toContainText(
    "I have no source with this ID as of August 26, 2016. It may not have been public yet, or the link may be incomplete.",
  );
  await page.goto(`/projects/P130164?evidence=${encodeURIComponent(ICR_54)}`);
  await expect(drawer(page)).toContainText("I have no source with this ID. The link may be incomplete.");
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

// Ticket 111's reveals (DESIGN.md section 4, Motion): what a wait produced enters once, when the wait ends, and is
// drawn at once everywhere else. The transitions are the browser's own, as it ran them.
const byProperty = (moved: Omit<Moved, "on">[]) => [...moved].sort((a, b) => a.property.localeCompare(b.property));

test("a streamed answer's Strata, in short block enters over 200 ms and the check line's tick reveals 120 ms later; Back shows both at once", async ({ page }) => {
  await recordTransitions(page);
  await open(page, { stream: "ask-ke-nwwda-541055-past-range.sse" });
  await askFromTheBox(page);
  await landed(page);
  await animationsDone(page);

  expect(byProperty(await transitionsOn(page, "inShortBlock"))).toEqual([
    { property: "opacity", from: "0", duration: 200, delay: 0 },
    { property: "translate", from: "0px 4px", duration: 200, delay: 0 },
  ]);
  expect(await transitionsOn(page, "checkTick")).toEqual([{ property: "clip-path", from: "inset(0px 100% 0px 0px)", duration: 200, delay: 120 }]);
  // The tick sits in the check line's 48 px indent beside "Checked", where the removed box has its icon, 16 px wide
  // in ink-muted, and a screen reader hears only the line's words, which say "Checked".
  const line = panel(page).locator("[data-check-line]");
  const tick = line.locator("[data-check-tick]");
  await expect(tick).toHaveAttribute("aria-hidden", "true");
  await expect(line).toHaveText(/^Checked: /);
  const [edge, mark, checked] = [(await line.boundingBox())!, (await tick.boundingBox())!, (await line.locator("[data-check-part=checked]").boundingBox())!];
  expect([Math.round(mark.x - edge.x), Math.round(mark.width)]).toEqual([20, 16]);
  expect(mark.y).toBeGreaterThanOrEqual(checked.y);
  expect(mark.y + mark.height).toBeLessThanOrEqual(checked.y + 20);
  expect(await tick.evaluate((element) => getComputedStyle(element).color)).toBe("rgb(75, 94, 113)");

  // Back to the page the answer was asked on shows it at once.
  await page.getByRole("main").getByRole("link", { name: "Procurement", exact: true }).first().click();
  await expect(page).toHaveURL(/\/procurement$/);
  await forgetTransitions(page);
  await page.goBack();
  await expect(panel(page).locator("[data-in-short]")).toBeVisible();
  await animationsDone(page);
  expect(await transitionsOn(page, "inShortBlock")).toEqual([]);
  expect(await transitionsOn(page, "checkTick")).toEqual([]);
});

test("the evidence drawer enters with opacity and 12 px from the right over 160 ms, moves nothing when its source changes, and closes at once", async ({ page }) => {
  await recordTransitions(page);
  await open(page, { stream: "ask-p130164-isr-section.sse" });
  await askFromTheBox(page);
  await landed(page);
  await animationsDone(page);
  await forgetTransitions(page);
  const moves = async () => (await page.evaluate(() => (window as unknown as { moved: Moved[] }).moved)).filter((entry) => ["opacity", "translate", "transform"].includes(entry.property));

  await panel(page).locator("[data-sentence-text='3'] [data-citation='4']").click();
  await expect(drawer(page)).toBeVisible();
  // It arrives from its own edge without pushing the page sideways.
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(1440);
  await animationsDone(page);
  expect(await transitionsOn(page, "evidenceDrawer")).toEqual([{ property: "opacity", from: "0", duration: 160, delay: 0 }]);
  expect(await transitionsOn(page, "drawerPanel")).toEqual([{ property: "translate", from: "12px", duration: 160, delay: 0 }]);

  await forgetTransitions(page);
  await drawer(page).getByRole("tab").first().click();
  await expect(drawer(page).getByRole("tab").first()).toHaveAttribute("aria-selected", "true");
  await animationsDone(page);
  expect(await moves()).toEqual([]);

  await drawer(page).getByRole("button", { name: "Close the source" }).click();
  await expect(drawer(page)).toHaveCount(0);
  expect(await moves()).toEqual([]);
});

test("under reduced motion the answer's block, the check line's tick and the evidence drawer arrive with no transition", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await recordTransitions(page);
  await open(page, { stream: "ask-ke-nwwda-541055-past-range.sse" });
  await askFromTheBox(page);
  await landed(page);
  await marker(page, 1).click();
  await expect(drawer(page)).toBeVisible();

  for (const part of ["inShortBlock", "checkTick", "evidenceDrawer", "drawerPanel"]) expect(await transitionsOn(page, part), part).toEqual([]);
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
  // Measured once the sheet's slide has ended (ticket 90's sheet slides on a transition), so the size is exact: a box
  // measured mid-slide came back as 44.0000019, and rounding it would also pass a 43.6 px button (ticket 56).
  await animationsDone(page);
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
  // How Strata works' "What I don't do", the route the 16 brief settled (the 24 brief, section 4.5).
  await expect(panel(page).getByRole("link", { name: "How Strata works" })).toHaveAttribute("href", "/data/how-strata-works#what-i-dont-do");
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

// An ISR numbers no paragraphs: ticket 11 keys each section ("s4") and marks the passage unnumbered. The
// recorded answer's fourth sentence quotes the table in ISR 1's section on the PDO indicators
// (tests/ground_truth/values.toml, isr-1-rural-access-end-target) and also cites the ICR's Annex 1.A,
// which tracked the same indicator. A passage backs a number only inside quoted words, so the numbers
// 67.00 and 80.00 sit inside the quote's highlight (tests/test_answer_stream.py).
const ISR_S4 = "strata.gold.passage:19095337/v1/s4";
const ISR_QUOTE = "Percentage Value 67.00 67.00 80.00";
const marked = (words: string) => `Highlight starts. ${words} Highlight ends.`;
// What the card shows, without the words only a screen reader hears.
const shownExcerpt = async (page: Page) =>
  (await page.locator("[data-evidence-card] [data-excerpt]").textContent())!.replace("Highlight starts. ", "").replace(" Highlight ends.", "");

test("a sentence that quotes an ISR section names the section, never a paragraph, and highlights the quote that holds its numbers", async ({ page }) => {
  await open(page, { stream: "ask-p130164-isr-section.sse" });
  await askFromTheBox(page);
  await landed(page);
  const sentence = panel(page).locator("[data-sentence-text='3']");
  const isrMarker = sentence.locator("[data-citation='3']");

  await expect(isrMarker).toHaveAccessibleName(
    "Source 3: Implementation Status and Results Report, February 22, 2014, section Project Development Objective Indicators",
  );
  await isrMarker.hover();
  const card = page.locator("[data-evidence-card]");
  await expect(card.locator("[data-source]")).toHaveText(
    "Source: Implementation Status and Results Report, P130164, February 22, 2014, section Project Development Objective Indicators, page 2.",
  );
  // The section is table text with no sentence end, so the card quotes about 280 characters of it around
  // the quote, cut between words, with the quote highlighted whole and no number cut at its decimal point.
  await expect(card.locator("mark")).toHaveText(marked(ISR_QUOTE));
  const quote = await shownExcerpt(page);
  expect(quote.length).toBeLessThanOrEqual(290);
  expect(quote).toMatch(/^"…\S/);
  expect(quote).toMatch(/ \S+…"$/);
  const cardText = await card.textContent();
  await page.mouse.move(5, 880);
  await expect(card).toBeHidden();

  // Every number in the sentence matched the section, inside its quote.
  await expect(sentence.locator("[data-num]")).toHaveText(["67.00", "67.00", "80.00"]);
  await sentence.locator("[data-num]").last().hover();
  await expect(page.getByRole("tooltip")).toHaveText("Matches the section Project Development Objective Indicators of the status report for P130164.");
  // DESIGN.md section 3: Roboto Mono for IDs, in the tooltip as in the Asked line above it.
  const tipFaces = await page.getByRole("tooltip").evaluate((tip) =>
    Array.from(tip.querySelectorAll("*"))
      .filter((child) => child.children.length === 0 && child.textContent === "P130164")
      .map((child) => getComputedStyle(child).fontFamily.split(",")[0].replaceAll('"', "")),
  );
  expect(tipFaces).toEqual(["Roboto Mono"]);

  await isrMarker.click();
  const tabs = drawer(page).getByRole("tab");
  await expect(tabs.first()).toHaveText("ISR, Project Development Objective Indicators");
  await expect(tabs.first()).toHaveAccessibleName("ISR, Project Development Objective Indicators");
  await expect(drawer(page).locator("[data-meta-line]")).toHaveText(
    "Implementation Status and Results Report · Rajasthan Road Sector Modernization (P130164) · February 22, 2014 · " +
      "Section Project Development Objective Indicators · PDF page 2 of 4",
  );
  // The project's name keeps its ID beside it: the line never breaks between "Modernization" and "(P130164)".
  // The ID is a link to its project page (ticket 21), padded above and below for its hit area, so the two
  // are compared by the middles of their boxes.
  const sameLine = await drawer(page)
    .locator("[data-meta-part]")
    .nth(1)
    .evaluate((part) => {
      const middle = (box: DOMRect) => Math.round((box.top + box.bottom) / 2);
      const name = part.querySelector(":scope > span:not(.font-mono)")!.getClientRects();
      return middle(name[name.length - 1]) === middle(part.querySelector(".font-mono")!.getClientRects()[0]);
    });
  expect(sameLine).toBe(true);
  // The drawer marks the quote in the whole section and scrolls it into view.
  const mark = drawer(page).locator("[data-passage] mark");
  await expect(mark).toHaveText(marked(ISR_QUOTE));
  await expect(mark).toBeInViewport();
  await expect(drawer(page)).toContainText("The whole section, word for word.");
  for (const text of [cardText, await tabs.first().textContent(), await drawer(page).locator("[data-meta-line]").textContent()]) {
    expect(text).not.toMatch(/\bs4\b|¶/);
  }

  // The ICR's annex is cited but not quoted, so its section has no highlight, and the drawer says so.
  await tabs.first().press("ArrowRight");
  await expect(tabs.nth(1)).toHaveAttribute("aria-selected", "true");
  await expect(tabs.nth(1)).toHaveAccessibleName(/^ICR, Annex\s1\.A$/);
  await expect(drawer(page).locator("[data-passage] mark")).toHaveCount(0);
  await expect(drawer(page)).toContainText("This sentence does not quote the section, so no words are highlighted.");
});

// A section's closing ID, such as "1.A" in "Annex 1.A", stays with the word before it, as a short
// section keeps to one line in the meta line; a long ISR section name still wraps between its words.
test("a section's closing ID never breaks from its name in the card's source line, the drawer's heading or its tab", async ({ page }) => {
  await open(page, { stream: "ask-p130164-isr-section.sse" });
  await askFromTheBox(page);
  await landed(page);
  const annex = panel(page).locator("[data-sentence-text='3'] [data-citation='4']");
  const text = async (locator: import("@playwright/test").Locator) => (await locator.textContent()) ?? "";

  await annex.hover();
  expect(await text(page.locator("[data-evidence-card] [data-source]"))).toContain("Annex\u00a01.A,");
  await annex.click();
  await expect(drawer(page).getByRole("tab").nth(1)).toHaveAttribute("aria-selected", "true");
  expect(await text(drawer(page).getByRole("heading", { level: 2 }))).toContain("section Annex\u00a01.A");
  expect(await text(drawer(page).getByRole("tab").nth(1))).toBe("ICR, Annex\u00a01.A");
  expect(await text(drawer(page).getByRole("tab").first())).toBe("ISR, Project Development Objective Indicators");
});

// "In short" is in lead (ticket 94), which DESIGN.md section 3 sets at 18/28, so a line that holds a number you can
// check is as tall as one that does not. The ISR answer's fourth sentence holds three of them.
for (const width of [1440, 390]) {
  test(`at ${width} px the lines of In short sit 28 px apart, with or without a number you can check`, async ({ page }) => {
    await open(page, { stream: "ask-p130164-isr-section.sse", width });
    await askFromTheBox(page);
    await landed(page);
    const block = panel(page).locator("[data-in-short]");
    await expect(block.locator("button[data-num]")).toHaveCount(6);
    // The bottom of each line of plain text, leaving out the numbers (buttons) and the markers (links).
    const bottoms = await block.evaluate((element) => {
      const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
      const seen: number[] = [];
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (node.parentElement?.closest("button, a, .sr-only")) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        for (const rect of range.getClientRects()) {
          if (rect.width > 0 && !seen.some((bottom) => Math.abs(bottom - rect.bottom) < 4)) seen.push(rect.bottom);
        }
      }
      return seen.sort((a, b) => a - b);
    });
    expect(bottoms.length).toBeGreaterThan(3);
    const gaps = bottoms.slice(1).map((bottom, at) => Math.round(bottom - bottoms[at]));
    expect(gaps).toEqual(gaps.map(() => 28));
  });
}

// WCAG 2.2 SC 2.4.11, Focus Not Obscured: the drawer scrolls to the ISR's highlight on open, and the tab
// that Tab then moves to must never sit hidden under the drawer's sticky header (the 14 design review,
// round 4, B1). The first two window sizes hid it before the drawer scrolled only for a highlight out of
// view; the first and the third still scroll, and hide it without the panel's scroll padding.
for (const [width, height] of [
  [1024, 600],
  [320, 900],
  [320, 700],
] as const) {
  test(`at ${width} by ${height} px the source tab you Tab to shows below the drawer's sticky header`, async ({ page }) => {
    await open(page, { stream: "ask-p130164-isr-section.sse", width });
    await page.setViewportSize({ width, height });
    await askFromTheBox(page);
    await landed(page);
    await panel(page).locator("[data-sentence-text='3'] [data-citation='3']").click();
    await expect(drawer(page).locator("[data-passage] mark")).toBeInViewport();

    // From the heading: the copy key (ticket 112), the close, then the first source tab.
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    const tab = drawer(page).getByRole("tab", { name: "ISR, Project Development Objective Indicators" });
    await expect(tab).toBeFocused();
    // The sticky header that holds the heading and "Close the source".
    const header = drawer(page).locator("[data-drawer-header]");
    await expect(header.getByRole("button", { name: "Close the source" })).toBeVisible();
    await expect(async () => {
      const [tabBox, headerBox] = [await tab.boundingBox(), await header.boundingBox()];
      expect(tabBox!.y).toBeGreaterThanOrEqual(headerBox!.y + headerBox!.height);
      expect(tabBox!.y + tabBox!.height).toBeLessThanOrEqual(height);
    }).toPass({ timeout: 2000 });
  });
}

// The claim beside its source is why the drawer exists, so opening it never slides "From the answer"
// under the sticky header for a highlight already in view. Only a highlight out of view scrolls, and it
// then sits in the middle of the space under the header (the 14 critique, round 4). At 1024 by 900 and
// 390 by 844 the ISR's highlight is in view on open; at 320 by 568 it is below the fold.
for (const [width, height, scrolls] of [
  [1024, 900, false],
  [390, 844, false],
  [320, 568, true],
] as const) {
  test(`at ${width} by ${height} px the drawer opens ${scrolls ? "with the highlight in the middle under its header" : "with the claim, its sources and the highlight all in view"}`, async ({ page }) => {
    await open(page, { stream: "ask-p130164-isr-section.sse", width });
    await page.setViewportSize({ width, height });
    await askFromTheBox(page);
    await landed(page);
    await panel(page).locator("[data-sentence-text='3'] [data-citation='3']").click();
    const mark = drawer(page).locator("[data-passage] mark");
    await expect(mark).toHaveText(marked(ISR_QUOTE));

    await expect(async () => {
      const header = (await drawer(page).locator("[data-drawer-header]").boundingBox())!;
      const under = header.y + header.height;
      const shown = (await mark.boundingBox())!;
      expect(shown.y).toBeGreaterThanOrEqual(under);
      expect(shown.y + shown.height).toBeLessThanOrEqual(height);
      if (scrolls) {
        const middle = under + (height - under) / 2;
        expect(Math.abs(shown.y + shown.height / 2 - middle)).toBeLessThanOrEqual(2);
      } else {
        expect((await drawer(page).locator("[data-claim]").boundingBox())!.y).toBeGreaterThanOrEqual(under);
        expect((await drawer(page).getByRole("tab").first().boundingBox())!.y).toBeGreaterThanOrEqual(under);
      }
    }).toPass({ timeout: 2000 });
  });
}

// A whole sentence a reader quotes is often longer than the third of the card's room that goes before
// the match, so the cut must never fall inside the matched words.
test("a long quote stays whole and highlighted in the evidence card, which still keeps to about 280 characters", async ({ page }) => {
  const isr = JSON.parse(await recorded("evidence-isr-p130164-s4.json"));
  // From "Share of rural population" to "250-500": 248 characters of the section.
  const [start, end] = [64, 312];
  const stream = await changed("ask-p130164-isr-section.sse", "evidence", 2, (data) => ({ ...data, highlights: [{ sentence: 3, start, end }] }));
  await open(page);
  await page.route("**/api/ask", (route) => route.fulfill({ contentType: "text/event-stream", body: stream }));
  await askFromTheBox(page);
  await landed(page);

  await panel(page).locator("[data-sentence-text='3'] [data-citation='3']").hover();

  const card = page.locator("[data-evidence-card]");
  await expect(card.locator("mark")).toHaveCount(1);
  await expect(card.locator("mark")).toHaveText(marked(isr.row.text.slice(start, end)));
  expect((await shownExcerpt(page)).length).toBeLessThanOrEqual(290);
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

// A passage backs a number only inside quoted words, but it also backs its report's date, which is in
// the drawer's meta line and not in the paragraph (src/strata/agent/verifier.py, check 1). The tooltip
// points where the value is.
test("a number's tooltip names the paragraph it was quoted from, and a date's names the report's date when the paragraph does not hold it", async ({ page }) => {
  await open(page);
  await askFromTheBox(page);
  await landed(page);

  await panel(page).locator("[data-sentence-text='0'] [data-num]").first().hover();
  await expect(page.getByRole("tooltip")).toHaveText("Matches paragraph 54 of the completion report for P130164.");
  await page.mouse.move(5, 880);
  await expect(page.getByRole("tooltip")).toHaveCount(0);

  const date = panel(page).locator("[data-sentence-text='2'] [data-num]");
  await expect(date).toHaveText("October 10, 2019");
  await date.hover();
  await expect(page.getByRole("tooltip")).toHaveText("Matches the date of the completion report for P130164.");
});

test("Close the answer closes the panel and its drawer, and returns focus to the box without opening its list until you ask for it", async ({ page }) => {
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
  // brief, section 6.4), until you click in the box, press Down or type.
  await expect(box(page)).toHaveValue(QUESTION);
  await expect(box(page)).toHaveAttribute("aria-expanded", "false");
  await box(page).click();
  await expect(box(page)).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Escape");
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
  // The address drops the source once the drawer has closed, which a busy computer can draw a frame later.
  await expect.poll(() => new URL(page.url()).searchParams.get("evidence")).toBeNull();
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

// The server applies the view's rules (ticket 40), so the answer says it was asked in a preview of the public view, and
// the preview banner sits above it.
test("an answer asked with ?view=public names the preview, and the banner sits above it", async ({ page }) => {
  await open(page, { path: "/projects/P130164?view=public" });
  await askFromTheBox(page);
  await landed(page);

  await expect(panel(page).locator("[data-asked]")).toHaveText("Asked within P130164, in a preview of the public view.");
  const alert = (await page.locator("main [data-alert]").first().boundingBox())!;
  expect(alert.y + alert.height).toBeLessThanOrEqual((await panel(page).boundingBox())!.y);

  await marker(page, 1).click();
  // Ticket 32: a passage a search found shows the feedback row, disabled in a preview, and its line replaces brief
  // 14's preview line (the 32 brief, section 10, item 7).
  await expect(drawer(page)).toContainText(
    "This is a preview, so I'm not recording the sources you open, and you can't report a passage.",
  );
});

test("the check line never uses the success state", async ({ page }) => {
  await open(page, { stream: "ask-p130164-rebidding.sse" });
  await askFromTheBox(page);
  await landed(page);

  const line = panel(page).locator("[data-check-line]");
  const look = await line.evaluate((el) => ({ background: getComputedStyle(el).backgroundColor, color: getComputedStyle(el).color }));
  expect(look).toEqual({ background: "rgb(231, 237, 243)", color: "rgb(61, 76, 92)" });
  // Ticket 111: its one icon is the tick beside "Checked", in ink-muted, never success green.
  await expect(line.locator("svg")).toHaveCount(1);
  expect(await line.locator("svg[data-check-tick]").evaluate((el) => getComputedStyle(el).color)).toBe("rgb(75, 94, 113)");
});

for (const width of [1440, 390]) {
  test(`axe finds no WCAG 2.2 AA violations in the answer and the open drawer at ${width} px`, async ({ page }) => {
    await open(page, { width });
    await askFromTheBox(page);
    await landed(page);
    await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
    let results = await scan(page);
    expect(results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`)).toEqual([]);

    await marker(page, 1).click();
    await expect(drawer(page)).toBeVisible();
    await page.waitForFunction(() => document.getAnimations().every((a) => a.playState !== "running" || a.effect?.getTiming().iterations === Infinity));
    results = await scan(page);
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
