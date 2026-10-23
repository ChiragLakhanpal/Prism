// The design gallery is for development only: the production build has none of its code,
// and its address shows the app (criterion 11 of ticket 02).
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, mockApi, recorded, test } from "./mocked";

const dist = (name: string) => fileURLToPath(new URL(`../${name}/`, import.meta.url));

function filesIn(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) =>
    entry.isDirectory() ? filesIn(join(dir, entry.name)) : [join(dir, entry.name)],
  );
}

const holdsGallery = (dir: string) =>
  filesIn(dir)
    .filter((file) => /\.(js|css|html)$/.test(file))
    .filter((file) => readFileSync(file, "utf8").includes("data-gallery-root"));

test("the production build holds none of the gallery's code, and the gallery build does", () => {
  expect(holdsGallery(dist("dist"))).toEqual([]);
  // The marker the check looks for is real: the gallery build carries it.
  expect(holdsGallery(dist("dist-gallery")).length).toBeGreaterThan(0);
});

test("the gallery's address in the production build shows the app, not the gallery", async ({ page }) => {
  await mockApi(page, { "/api/me": { body: await recorded("me.json") } });
  await page.goto("/gallery/buttons");

  await expect(page.getByText("You are signed in as Ana Example.")).toBeVisible();
  await expect(page.locator("[data-gallery-root]")).toHaveCount(0);
});
