// The one way the screen tests run axe, tests/axe.ts (ticket 55). Its scans must find what axe's
// default run finds, so moving every spec onto it weakens no accessibility test, and they must cost
// less: the default run opens a blank page to finish each scan and loads axe into it a second time.
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "./mocked";
import { scan, WCAG_22_AA } from "./axe";

// Four WCAG 2.2 AA failures that axe names: an image with no text, a field with no label, a button
// with no name and pale grey text on white. The section holds one more image with no text.
const PIXEL = "data:image/gif;base64,R0lGODlhAQABAAAAACw=";
const FAILING = `<!doctype html><html lang="en"><head><title>Four failures</title></head><body><main>
<img src="${PIXEL}"><input type="text"><button></button>
<p style="color:#bbbbbb;background:#ffffff">Pale words</p>
<section id="part"><img src="${PIXEL}"></section>
</main></body></html>`;

type Results = Awaited<ReturnType<AxeBuilder["analyze"]>>;
const found = (results: Results) =>
  results.violations.map((v) => `${v.id}: ${v.nodes.map((node) => node.target.join(" ")).join(", ")}`);
const rules = (lines: string[]) => lines.map((line) => line.split(":")[0]);

test("a scan finds the same WCAG 2.2 AA violations as axe's default run, on the whole page and in one part of it", async ({ page }) => {
  await page.setContent(FAILING);

  const whole = found(await scan(page));
  expect(whole).toEqual(found(await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze()));
  expect(rules(whole)).toEqual(expect.arrayContaining(["button-name", "color-contrast", "image-alt", "label"]));

  const part = found(await scan(page, "#part"));
  expect(part).toEqual(found(await new AxeBuilder({ page }).include("#part").withTags(WCAG_22_AA).analyze()));
  expect(rules(part)).toEqual(["image-alt"]);
});

test("a scan runs inside the page it checks and opens no second page, which axe's default run does for each scan", async ({ page, context }) => {
  await page.setContent(FAILING);
  let opened = 0;
  context.on("page", () => {
    opened += 1;
  });

  await scan(page);
  expect(opened).toBe(0);

  await new AxeBuilder({ page }).withTags(WCAG_22_AA).analyze();
  expect(opened, "axe's default run").toBe(1);
});

test("a scan refuses a page that holds a frame, because it would leave out a frame from another origin", async ({ page }) => {
  await page.setContent(`<main><iframe title="Another page" srcdoc="<p>Inside</p>"></iframe></main>`);

  await expect(scan(page)).rejects.toThrow(/frame/);
});
