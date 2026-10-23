// Every page the gallery renders, read from the gallery's own index, so a new page is tested
// without editing the tests.
import { expect, type Page } from "@playwright/test";

export async function galleryPaths(page: Page): Promise<string[]> {
  await page.goto("/gallery");
  const list = page.getByRole("navigation", { name: "Components" }).getByRole("link");
  await expect(list.first()).toBeVisible();
  const links = await list.evaluateAll((anchors) => anchors.map((anchor) => new URL((anchor as HTMLAnchorElement).href).pathname));
  return ["/gallery", ...links];
}
