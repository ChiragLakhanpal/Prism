// The six checks and the refusals in the answer panel (ticket 24) at seam 4. The panel plays the answer
// streams the server writes for the scripted cases, recorded byte for byte in tests/fixtures/api and checked
// against the server by tests/test_answer_stream.py, so every count on screen is the verifier's. The words
// are the ticket's and the 24 design brief's; ISR 7 and ICR paragraph 78 are tests/ground_truth/values.toml's.
import { scan } from "./axe";
import type { Page } from "@playwright/test";
import { askFromTheBox, landed, open, panel } from "./answer-page";
import { expect, test } from "./mocked";


async function answered(page: Page, stream: string, width = 1440) {
  const seen = await open(page, { stream, width });
  await askFromTheBox(page);
  await landed(page);
  return seen;
}

async function axe(page: Page) {
  const results = await scan(page, "[data-answer-panel]");
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join("; ")}`);
}

test("the check line reads the verifier's counts in the ticket's form, in the neutral state, when no model was needed", async ({ page }) => {
  await answered(page, "ask-ke-nwwda-541055-past-range.sse");

  const line = panel(page).locator("[data-check-line]");
  await expect(line).toHaveText(
    "Checked: 5 of 5 numbers match records; 2 of 2 quotes are on their pages. Not checked: whether these are the right comparables.",
  );
  await expect(line.locator("[data-check-part=judged]")).toHaveCount(0);
  expect(await line.evaluate((el) => [getComputedStyle(el).backgroundColor, getComputedStyle(el).color])).toEqual([
    "rgb(231, 237, 243)",
    "rgb(61, 76, 92)",
  ]);
  // Each part starts its own line, in the order checked, judged, not checked.
  const tops = await line.locator("[data-check-part]").evaluateAll((parts) => parts.map((part) => part.getBoundingClientRect().top));
  expect(tops[1]).toBeGreaterThan(tops[0]);
});

test("a judged sentence adds the model's part, and the steps list all six checks under the verifier's step", async ({ page }) => {
  await answered(page, "ask-ke-nwwda-541055-advice.sse");

  await expect(panel(page).locator("[data-check-part=judged]")).toHaveText(
    "Judged by a model: 1 of 1 sentence follows from its sources. The other three needed no model, because everything they stated matched a record or a page.",
  );
  await panel(page).getByRole("button", { name: /^Show the .* steps I took$/ }).click();
  const verifier = panel(page).locator("[data-steps] > ol > li").filter({ hasText: "I ran six checks" });
  await expect(verifier).toContainText("I ran six checks on the four sentences I wrote and removed none.");
  await expect(verifier.locator("[data-step-items] li")).toHaveText([
    // 49, 3.3, 7.9, 4.4, 13 and 1.5; the past range's summary and two comparables' rows.
    "6 of 6 numbers and dates matched a record or a quote.",
    "3 of 3 sources I cited came back for this question.",
    "2 of 2 quotes were word for word on their pages.",
    "A model judged one sentence, and 1 of 1 followed from its sources. The other three needed no model, because everything they stated matched a record or a page.",
    "1 of 1 sentence that gave advice cited a lesson or a comparable package.",
    "No sentence rested on a report that another report disagrees with.",
  ]);
});

test("a sentence its passage does not support is removed with check 4's reason from the copy file", async ({ page }) => {
  await answered(page, "ask-p130164-unsupported.sse");

  await expect(panel(page).locator("[data-removed-box]")).toHaveText(
    "I removed one sentence. It said the completion report blamed the contractors for the rebidding, and the sources it cited do not say that.",
  );
});

test("the removed box lists every removed sentence with its reason, the first in the lead, and passes axe at three widths", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    await answered(page, "ask-p130164-several-removed.sse", width);
    const box = panel(page).locator("[data-removed-box]");
    await expect(box.locator("[data-removed-lead]")).toHaveText("I removed three sentences.");
    await expect(box).toContainText("The first said bids were usually opened within 45 days, and no record supports that number.");
    await expect(box.getByRole("list", { name: "The others:" }).getByRole("listitem")).toHaveText([
      '"Base your works estimates on market rates before you advertise." It gave advice without citing a lesson or a comparable package.',
      '"The completion report blamed the contractors for the rebidding." The sources it cites do not say this.',
    ]);
    // Removed sentences are plain text: no number to check and no marker.
    await expect(box.locator("[data-num], [data-citation]")).toHaveCount(0);
    expect(await axe(page)).toEqual([]);
  }
});

test("advice removed by check 5 is quoted whole in the lead, since an order does not read as reported speech", async ({ page }) => {
  await answered(page, "ask-p130164-advice-without-lesson.sse");

  await expect(panel(page).locator("[data-removed-box]")).toHaveText(
    'I removed one sentence. It said "Base your works estimates on market rates before you advertise." It gave advice without citing a lesson or a comparable package.',
  );
  // Set as the list sets a removed sentence: in its own quote element, in ink, apart from its reason.
  const sentence = panel(page).locator("[data-removed-box] p").first().locator("q");
  await expect(sentence).toHaveText('"Base your works estimates on market rates before you advertise."');
  await expect(sentence).toHaveClass(/text-ink/);
});

test("when the judging model did not respond, its sentences are removed and Try again asks the question again", async ({ page }) => {
  const seen = await answered(page, "ask-p130164-judge-no-response.sse");

  const box = panel(page).locator("[data-removed-box]");
  // The lead says why, once: every removed sentence has the same cause, so no second sentence repeats it.
  await expect(box.locator("p").first()).toHaveText(
    "I removed one sentence. It said the completion report blamed the contractors for the rebidding, and I couldn't check it, because the model that judges sentences did not respond.",
  );
  await expect(box.locator("[data-unjudged]")).toHaveCount(0);
  await expect(panel(page).locator("[data-sentence-text]")).toHaveCount(3);
  await box.getByRole("button", { name: "Try again" }).click();
  await expect.poll(() => seen.asked.length).toBe(2);
});

test("when the judging model did not respond and nothing survived, an error says so over every sentence I wrote", async ({ page }) => {
  await answered(page, "ask-p130164-judge-no-response-none-kept.sse");

  await expect(panel(page).getByRole("alert")).toContainText(
    "I couldn't check my answer, because the model that judges sentences did not respond. Your question is still in the box.",
  );
  await expect(panel(page).getByRole("button", { name: "Try again" })).toBeVisible();
  await expect(panel(page).locator("[data-removed-box] [data-removed-lead]")).toHaveText("I removed both sentences.");
  // The alert names the cause, so each sentence under it says only that I couldn't check it.
  for (const item of await panel(page).locator("[data-removed-box] li").allTextContents()) expect(item).toMatch(/" I couldn't check it\.$/);
  await expect(panel(page).locator("[data-check-line]")).toHaveCount(0);
  // Above the alert, the verifier's done line alone: its six checks stay out of the way.
  await expect(panel(page).locator("[data-step-items]")).toHaveCount(0);
  // The alert speaks, so the status line ends on the last step it said and never adds that the answer is ready.
  const said = () => page.evaluate(() => (window as unknown as { said: string[] }).said);
  await expect.poll(async () => (await said()).at(-1)).toBe("I'm asking a model whether two sentences follow from their sources.");
  // One gap between status lines (ANNOUNCE_GAP_MS, 500 ms, in web/src/components/AnswerPanel.tsx) and a margin.
  await page.waitForTimeout(700);
  expect((await said()).filter((line) => line.startsWith("The answer is ready"))).toEqual([]);
});

test("when check 6 could not ask which reports disagree and nothing survived, an error says so and offers Try again", async ({ page }) => {
  const seen = await answered(page, "ask-p130164-disagreements-unavailable.sse");

  await expect(panel(page).getByRole("alert")).toContainText(
    "I couldn't check my answer, because I couldn't find out whether other reports disagree with its sources. Your question is still in the box.",
  );
  await expect(panel(page).locator("[data-in-short]")).toHaveCount(0);
  await expect(panel(page).locator("[data-removed-box] [data-removed-lead]")).toHaveText("I removed all three sentences.");
  await panel(page).getByRole("button", { name: "Try again" }).click();
  await expect.poll(() => seen.asked.length).toBe(2);
});

test("ICR paragraph 78 shows under ISR 7's sentence with both sides, though the agent left it out", async ({ page }) => {
  await answered(page, "ask-p130164-isr-7-rating.sse");

  const card = panel(page).getByRole("group", { name: "Two reports disagree: ISR 7 and ICR paragraph 78" });
  await expect(card).toBeVisible();
  const sides = card.locator("[data-side]");
  // Ticket 23's anatomy: each side's name, spelled out the first time the answer uses it, then its date and when
  // it was written, then what it said under the report's own field name.
  await expect(sides.nth(0)).toContainText("Implementation Status and Results Report (ISR) 7");
  await expect(sides.nth(0)).toContainText("August 26, 2016. Written during the project.");
  await expect(sides.nth(0)).toContainText("Progress towards achievement of PDO");
  await expect(sides.nth(0)).toContainText("Satisfactory");
  await expect(sides.nth(1)).toContainText("Implementation Completion and Results Report (ICR), paragraph 78");
  await expect(sides.nth(1)).toContainText("October 10, 2019. Written after the project closed.");
  await expect(sides.nth(1)).toContainText("Strata leans on this");
  // The whole sentence of paragraph 78 that holds the quote (values.toml, icr-para-78), as the drawer's card shows it.
  await expect(sides.nth(1)).toContainText(
    '"Indeed, it was clearly identified at the MTR that the achievement of part of the PDO was compromised by the major delays in implementing activities under Components 2 and 3 and lack of endorsement from relevant stakeholders."',
  );
  await expect(sides.nth(0)).toHaveAttribute("data-side", "other");
  // Equal weight: the same border and fill on both sides.
  const looks = await sides.evaluateAll((all) => all.map((side) => [getComputedStyle(side).borderColor, getComputedStyle(side).backgroundColor]));
  expect(looks[0]).toEqual(looks[1]);
  // The sentence's own source keeps number 1, and the other side gets the next.
  await expect(card.locator("[data-citation]")).toHaveText(["[1]", "[2]"]);
  await expect(card).toContainText(
    "For a judgment of how a project went, I lean on the later, more independent report, here ICR paragraph 78, and I keep ISR 7 as the record of the earlier view.",
  );
  await expect(card).toContainText('If you keep ISR 7 instead, I treat "Progress towards achievement of PDO" as Satisfactory.');
  // The stream names the sentence keeping the other report would change (ticket 23).
  await expect(card).toContainText("That changes one sentence in this answer.");
  // The abbreviation is spelled out the first time "In short" uses it.
  await expect(panel(page).locator("[data-in-short]")).toContainText("project development objective (PDO)");
  // The card follows the sentence it concerns, in the order of the page.
  const sentence = await panel(page).locator("[data-sentence-text='0']").boundingBox();
  expect((await card.boundingBox())!.y).toBeGreaterThan(sentence!.y);
  // A marker inside the card opens its source in the drawer, and closing it returns focus to the marker.
  const second = card.locator("[data-citation='2']");
  await second.click();
  await expect(page.getByRole("dialog")).toContainText("paragraph 78");
  // The drawer highlights the words the side quotes, though no sentence quoted them, and shows no sentence as
  // citing it, since none does.
  await expect(page.getByRole("dialog").locator("[data-passage] mark")).toContainText(
    "it was clearly identified at the MTR that the achievement of part of the PDO was compromised",
  );
  await expect(page.getByRole("dialog").locator("[data-claim]")).toHaveCount(0);
  await page.keyboard.press("Escape");
  await expect(second).toBeFocused();
  // Each side also opens its source by name (the 23 brief, section 5.2), and focus comes back to that link.
  const openIsr = card.getByRole("link", { name: "Open ISR 7" });
  await openIsr.click();
  await expect(page.getByRole("dialog")).toContainText("ISR");
  await page.keyboard.press("Escape");
  await expect(openIsr).toBeFocused();
});

test("the disagreement card's sides sit side by side at 1440 px and stack when the card is under 560 px", async ({ page }) => {
  for (const [width, columns] of [[1440, 2], [1024, 1], [390, 1]] as const) {
    await answered(page, "ask-p130164-isr-7-rating.sse", width);
    const sides = panel(page).locator("[data-disagreement] [data-side]");
    const [first, second] = [(await sides.nth(0).boundingBox())!, (await sides.nth(1).boundingBox())!];
    expect(first.y === second.y ? 2 : 1, `at ${width} px`).toBe(columns);
    expect(await axe(page)).toEqual([]);
  }
});

test("a disagreement the draft already showed is the same card, as an info note", async ({ page }) => {
  await answered(page, "ask-p130164-both-sides.sse");

  const card = panel(page).getByRole("group", { name: "Sources differ: ISR 7 and ICR paragraph 78" });
  await expect(card).toHaveAttribute("data-disagreement", "info");
});

test("a refusal is a first-person answer from the copy file, with a link to What I don't do, and passes axe at three widths", async ({ page }) => {
  for (const width of [1440, 1024, 390]) {
    await answered(page, "ask-refuses-supplier-scores.sse", width);
    await expect(panel(page).locator("[data-in-short]")).toHaveText(
      "I don't score or rank suppliers. I can list the contracts a supplier signed on World Bank-financed projects, each with its award notice.",
    );
    await expect(panel(page).locator("[role=alert], [data-check-line], [data-removed-box]")).toHaveCount(0);
    expect(await axe(page)).toEqual([]);
  }
  await panel(page).getByRole("link", { name: "How Strata works" }).click();
  await expect(page).toHaveURL(/\/data\/how-strata-works#what-i-dont-do$/);
  const heading = page.getByRole("heading", { level: 2, name: "What I don't do" });
  await expect(heading).toBeFocused();
  await expect(page.locator("[data-dont-do] dt")).toHaveCount(10);
  // The heading lands with room above it, not flush against the window's top.
  expect((await heading.boundingBox())!.y).toBeGreaterThanOrEqual(16);
  await expect(page.locator("[data-dont-do] dt").first()).toHaveText("I don't score or rank suppliers.");
});

test("a full refusal's steps say I turned the request down", async ({ page }) => {
  await answered(page, "ask-refuses-supplier-scores.sse");

  await panel(page).getByRole("button", { name: /^Show the .* steps? I took$/ }).click();
  await expect(panel(page).locator("[data-steps]")).toContainText("I turned the request down.");
});

test("a partial refusal opens In short, says the rest was answered, and the checked answer follows", async ({ page }) => {
  await answered(page, "ask-refuses-part-supplier-scores.sse");

  const inShort = panel(page).locator("[data-in-short]");
  await expect(inShort.locator("p").first()).toHaveText("I don't score or rank suppliers. I answered the rest of your question.");
  await expect(inShort).toContainText("108 of 328 cases had to go through rebidding");
  await expect(panel(page).locator("[data-check-line]")).toBeVisible();
});
