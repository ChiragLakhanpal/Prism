// The capture command covers every gallery page at 1440, 1024 and 390 px, with hover and
// keyboard-focus shots, so design reviews are repeatable (criterion 10 of ticket 02). The
// command itself is not a gate step; this checks its list of shots.
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { galleryCopy } from "../src/gallery/copy";
import { SHOTS, WIDTHS } from "../capture/shots";

test("the capture list photographs every gallery page at 1440, 1024 and 390 px", () => {
  expect(WIDTHS).toEqual([1440, 1024, 390]);
  for (const slug of Object.keys(galleryCopy.pages)) {
    const shot = SHOTS.find((candidate) => candidate.path === `/gallery/${slug}` && !candidate.act);
    expect(shot, slug).toBeDefined();
    expect(shot!.widths ?? WIDTHS).toEqual(WIDTHS);
  }
});

test("the capture list has hover and keyboard-focus shots, and app shots against the recorded API", () => {
  expect(SHOTS.filter((shot) => shot.name.includes("--hover-")).length).toBeGreaterThan(5);
  expect(SHOTS.filter((shot) => shot.name.includes("--focus-")).length).toBeGreaterThan(5);
  expect(SHOTS.some((shot) => shot.server === "app" && shot.api?.["/api/me"]?.recorded === "me.json")).toBe(true);
});

test("one command captures them, and it is not a gate step", () => {
  const scripts = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8")).scripts;
  expect(scripts.capture).toContain("playwright test --config playwright.capture.config.ts");
  const steps = readFileSync(new URL("../../gates/steps.toml", import.meta.url), "utf8");
  expect(steps).not.toContain("capture");
});
