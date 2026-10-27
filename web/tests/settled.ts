// Waits that let a screen test measure the page as a reader sees it once it has settled (ticket 56). A test waits for
// a state, never for a fixed time, because the gate runs beside other builds and a fixed time that is enough alone is
// not enough at a load average of 40 (docs/agents/areas/ops.md).
import type { Page } from "@playwright/test";

// Every Latin face the app's stylesheet declares has loaded, and two frames have drawn with it. The fallback face has
// Open Sans's metrics, but its words are not the same widths, so at 390 px a line can break in another place and move
// what comes after it by one line, about 22 px. On a busy computer the web font can arrive after a test's first
// measure, so a test that compares two measures, or scrolls to a place, waits here first.
export async function fontsLoaded(page: Page) {
  await page.evaluate(async () => {
    const latin = [...document.fonts].filter((face) => /U\+0+-0*FF\b/i.test(face.unicodeRange));
    await Promise.all(latin.map((face) => face.load()));
    await document.fonts.ready;
    await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
  });
}

// Every animation and transition that ends has ended, so a box is measured where it comes to rest. One that repeats
// for ever, such as a skeleton's pulse, never rests, so it is left out.
export async function animationsDone(page: Page) {
  await page.waitForFunction(() =>
    document
      .getAnimations()
      .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
      .every((animation) => animation.playState !== "running"),
  );
}
