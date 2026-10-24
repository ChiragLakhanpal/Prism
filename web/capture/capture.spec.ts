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
      // A path the shot holds never answers, so its page stays in its loading state.
      for (const path of shot.pending ?? []) await page.route(`**${path}`, () => undefined);
      await page.setViewportSize({ width, height: 900 });
      await page.goto(`${base}${shot.path}`);
      await page.locator("main").waitFor();
      await page.evaluate(() => document.fonts.ready);
      if (shot.act) await shot.act(page);
      await page.screenshot({ path: `${OUT}/${shot.name}--${width}.png`, fullPage: shot.full ?? !shot.act, animations: "disabled" });
    });
  }
}
