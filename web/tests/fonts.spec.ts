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
  // French, Spanish and Portuguese passages and answers draw in Open Sans too (ticket 42): its latin-ext files hold œ.
  await page.evaluate(() => document.fonts.load('400 16px "Open Sans"', "œ « ñ ã ç"));
  expect(await page.evaluate(() => document.fonts.check('16px "Open Sans"', "œ « ñ ã ç"))).toBe(true);
  expect(outsideRequests).toEqual([]);
});

// Ticket 90: the page's one finding is set in Open Sans Light (DESIGN.md section 3), self-hosted from
// @fontsource/open-sans/300.css like every other weight.
test("text in the finding style draws in Open Sans at weight 300, from the app's own files", async ({ page, baseURL, outsideRequests }) => {
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });
  const fonts: string[] = [];
  page.on("request", (request) => {
    if (request.resourceType() === "font") fonts.push(request.url());
  });
  await page.goto("/");
  const finding = await page.evaluate(async () => {
    const line = document.createElement("p");
    line.className = "text-finding";
    line.textContent = "2 of 49";
    document.querySelector("main")!.append(line);
    // Laying the line out starts its face's download; ready waits for it.
    line.getBoundingClientRect();
    await document.fonts.ready;
    const style = getComputedStyle(line);
    return {
      family: style.fontFamily.split(",")[0],
      weight: style.fontWeight,
      // The face the line draws in is loaded, and it is Open Sans's own 300, not a synthesized one.
      loaded: document.fonts.check('300 28px "Open Sans"', "2 of 49"),
      face: Array.from(document.fonts).some((face) => face.family.replaceAll('"', "") === "Open Sans" && face.weight === "300" && face.status === "loaded"),
    };
  });
  expect(finding).toEqual({ family: '"Open Sans"', weight: "300", loaded: true, face: true });
  const light = fonts.filter((url) => /open-sans-[\w-]*-300-normal/.test(url));
  expect(light.length, fonts.join("\n")).toBeGreaterThanOrEqual(1);
  for (const url of light) expect(url).toMatch(new RegExp(`^${baseURL}/assets/[\\w-]+\\.woff2$`));
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
