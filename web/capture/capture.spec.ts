// Takes every shot in capture/shots.ts at each of its widths and saves it as
// <name>--<width>.png in STRATA_CAPTURE_DIR (web/screenshots when unset).
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "@playwright/test";
import { mockApi, recorded } from "../tests/mocked";
import { SHOTS, WIDTHS } from "./shots";

const OUT = resolve(process.env.STRATA_CAPTURE_DIR ?? fileURLToPath(new URL("../screenshots", import.meta.url)));
mkdirSync(OUT, { recursive: true });

for (const shot of SHOTS) {
  for (const width of shot.widths ?? WIDTHS) {
    test(`${shot.name} at ${width} px`, async ({ page }) => {
      const base = shot.server === "app" ? process.env.STRATA_CAPTURE_APP_URL : process.env.STRATA_CAPTURE_GALLERY_URL;
      const responses: Record<string, { status?: number; body: string }> = {};
      for (const [path, answer] of Object.entries(shot.api ?? {})) {
        responses[path] = { status: answer.status, body: answer.recorded ? await recorded(answer.recorded) : (answer.body ?? "") };
      }
      await mockApi(page, responses);
      // A path the shot holds never answers, whatever its query, so its page stays in its loading state.
      for (const path of shot.pending ?? []) await page.route((url) => url.pathname.endsWith(path) || (url.pathname + url.search).endsWith(path), () => undefined);
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`${base}${shot.path}`);
      await page.locator("main").waitFor();
      await page.evaluate(() => document.fonts.ready);
      if (shot.act) await shot.act(page);
      const full = shot.full ?? !shot.act;
      // A whole page is shot in a window as tall as the page, so a sticky bar sits at the page's end
      // instead of being painted over the middle; a shot of the first screen shows it stuck.
      if (full) {
        // A block that holds a screen's height (min-h-svh) would grow with the tall window, so it keeps the
        // 900 px window's height, as a reader sees it (the 21 design review, round 3, F1).
        await page.evaluate(() => {
          for (const block of document.querySelectorAll<HTMLElement>(".min-h-svh")) block.style.minHeight = `${innerHeight}px`;
        });
        const height = await page.evaluate(() => document.documentElement.scrollHeight);
        await page.setViewportSize({ width, height: Math.max(900, height) });
      }
      await page.screenshot({ path: `${OUT}/${shot.name}--${width}.png`, fullPage: full, animations: "disabled" });
    });
  }
}
