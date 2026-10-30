// Ticket 140: the gallery's Lessons, Passage reports and Judging states, drawn from the server's own recorded answers,
// print no person's name or email. Each act's actor reads "You", a role with its region, or "A reviewer", by the one
// rule the server applies (strata.config.Roles.actor) and LessonParts' actorText writes.
import type { Page } from "@playwright/test";
import { expect, test } from "./mocked";
import { EMAIL, people } from "./people";

async function open(page: Page, slug: string): Promise<string> {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.goto(`/gallery/${slug}`);
  await expect(page.locator("[data-gallery-root] h1")).toBeVisible();
  return page.locator("[data-gallery-root]").innerText();
}

async function namesNoPerson(text: string) {
  const lower = text.toLowerCase();
  expect((await people()).filter((word) => lower.includes(word.toLowerCase()))).toEqual([]);
  expect(text).not.toMatch(EMAIL);
}

test("the gallery's lesson states name your own act as yours and others by role and region, and no person", async ({ page }) => {
  const text = await open(page, "lessons");
  // The queue row Omar recommended, as he reads it.
  expect(text).toContain("You recommended adding it as evidence to another lesson on October 27, 2026.");
  // The re-check Wanjiru asked for, as Asha reads it.
  expect(text).toContain("A lead procurement specialist for Eastern and Southern Africa asked for a re-check");
  await namesNoPerson(text);
});

test("the gallery's passage feedback, passage report and judging states name no person", async ({ page }) => {
  await namesNoPerson(await open(page, "retrieval"));
  const reports = await open(page, "judging");
  // Daniel's decision as he reads it, and as Priya reads it when it overtook hers.
  expect(reports).toMatch(/Ranked lower for questions about [^.]+ on October 23, 2026, by you\./);
  expect(reports).toContain("A passage reviewer decided on these reports on");
  await namesNoPerson(reports);
});
