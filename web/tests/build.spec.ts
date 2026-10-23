// The design gallery is for development only: the production build has none of its code,
// and its address shows the app (criterion 11 of ticket 02).
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, mockShell, test } from "./mocked";
import { galleryCopy } from "../src/gallery/copy";

const dist = (name: string) => fileURLToPath(new URL(`../${name}/`, import.meta.url));

function filesIn(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? filesIn(join(dir, entry.name)) : [join(dir, entry.name)],
  );
}

// The gallery's root marker, and a sentence from its own copy file.
const MARKS = ["data-gallery-root", galleryCopy.sampleNote];

const holdsGallery = (dir: string) =>
  filesIn(dir)
    .filter((file) => /\.(js|css|html)$/.test(file))
    .filter((file) => MARKS.some((mark) => readFileSync(file, "utf8").includes(mark)));

test("the production build holds none of the gallery's code, and the gallery build does", () => {
  expect(holdsGallery(dist("dist"))).toEqual([]);
  // The marker the check looks for is real: the gallery build carries it.
  expect(holdsGallery(dist("dist-gallery")).length).toBeGreaterThan(0);
});

test("the gallery's address in the production build shows the app's not-found page, not the gallery", async ({ page }) => {
  await mockShell(page);
  await page.goto("/gallery/buttons");

  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Page not found");
  await expect(page.locator("[data-gallery-root]")).toHaveCount(0);
});
