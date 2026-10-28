// Ticket 111's reveals, measured as the browser runs them: every CSS transition that starts on the page, with the
// part of the page it moved (its data attributes), what it moved, from where, for how long and after what delay.
// A reveal is a transition from @starting-style, so it starts once, when its element is drawn, and never again.
import type { Page } from "@playwright/test";

export type Moved = { on: string[]; property: string; from: string; duration: number; delay: number };

// Call before the page loads.
export async function recordTransitions(page: Page) {
  await page.addInitScript(() => {
    const moved: { on: string[]; property: string; from: string; duration: number; delay: number }[] = [];
    (window as unknown as { moved: typeof moved }).moved = moved;
    window.addEventListener(
      "transitionrun",
      (event) => {
        const target = event.target as HTMLElement | SVGElement;
        const running = target.getAnimations().find((animation) => (animation as CSSTransition).transitionProperty === event.propertyName);
        const effect = running?.effect as KeyframeEffect | undefined;
        const timing = effect?.getComputedTiming();
        // A keyframe names its property in camel case, such as clipPath.
        const key = event.propertyName.replace(/-([a-z])/g, (_, letter: string) => letter.toUpperCase());
        const first = effect?.getKeyframes()[0] as Record<string, unknown> | undefined;
        moved.push({
          on: Object.keys(target.dataset ?? {}),
          property: event.propertyName,
          from: String(first?.[key] ?? ""),
          duration: Number(timing?.duration ?? 0),
          delay: Number(timing?.delay ?? 0),
        });
      },
      true,
    );
  });
}

// The transitions that ran on a part of the page named by one of its data attributes, such as "byline" for
// data-byline, in the order they started.
export async function transitionsOn(page: Page, data: string): Promise<Omit<Moved, "on">[]> {
  const all = await page.evaluate(() => (window as unknown as { moved: Moved[] }).moved);
  return all.filter((entry) => entry.on.includes(data)).map(({ property, from, duration, delay }) => ({ property, from, duration, delay }));
}

// Forget what ran so far, so a test can measure what the next act starts.
export async function forgetTransitions(page: Page) {
  await page.evaluate(() => {
    (window as unknown as { moved: Moved[] }).moved.length = 0;
  });
}
