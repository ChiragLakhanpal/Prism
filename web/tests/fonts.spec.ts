// Fonts come from the app's own bundle, and the fallback face has DESIGN.md section 3's
// metrics, so text does not move when the web font arrives (criterion 2 of ticket 02).
import { expect, mockApi, recorded, test } from "./mocked";
import { fallbackMetrics } from "./design-md";

test("Open Sans and Roboto Mono load from the app's own files, and nothing else is fetched", async ({
  page,
  baseURL,
  outsideRequests,
}) => {
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });
  const fonts: string[] = [];
  page.on("request", (request) => {
    if (request.resourceType() === "font") fonts.push(request.url());
  });

  await page.goto("/");
  await page.evaluate(async () => {
    await document.fonts.load('400 16px "Open Sans"');
    await document.fonts.load('700 16px "Open Sans"');
    await document.fonts.load('400 16px "Roboto Mono"');
    await document.fonts.ready;
  });

  expect(fonts.length).toBeGreaterThanOrEqual(3);
  for (const url of fonts) expect(url).toMatch(new RegExp(`^${baseURL}/assets/[\\w-]+\\.woff2$`));
  expect(
    await page.evaluate(() =>
      ['400 16px "Open Sans"', '700 16px "Open Sans"', '400 16px "Roboto Mono"'].every((font) => document.fonts.check(font)),
    ),
  ).toBe(true);
  expect(outsideRequests).toEqual([]);
});

test("the fallback face uses the size-adjust and override values in DESIGN.md section 3", async ({ page }) => {
  const design = await fallbackMetrics();
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });
  await page.goto("/");

  const face = await page.evaluate(() => {
    type Metrics = { sizeAdjust: string; ascentOverride: string; descentOverride: string };
    const faces = Array.from(document.fonts) as (FontFace & Metrics)[];
    const found = faces.find((font) => font.family.replaceAll('"', "") === "Open Sans Fallback");
    return found && {
      "size-adjust": found.sizeAdjust,
      "ascent-override": found.ascentOverride,
      "descent-override": found.descentOverride,
    };
  });

  expect(Object.keys(design)).toEqual(["size-adjust", "ascent-override", "descent-override"]);
  expect(face).toEqual(design);
  expect(await page.evaluate(() => getComputedStyle(document.body).fontFamily)).toContain('"Open Sans Fallback"');
});
