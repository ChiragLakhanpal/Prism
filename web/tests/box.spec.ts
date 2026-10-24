// The one box (ticket 14) at seam 4: as you type it lists what Enter will do, from one set of intent
// rules, and nothing happens until you choose. The lookups are answered from the responses recorded
// in tests/fixtures/api, which the server tests check the server against. The words are the ticket's
// and the 14 design brief's, copied here so the test checks the copy file against an independent source.
import type { Page, Request } from "@playwright/test";
import { expect, mockApi, recorded, test } from "./mocked";

const PLAN = "/projects/P156634/procurement/northern-water-works-development-agency";

async function open(page: Page, path = "/", extra: Record<string, { status?: number; body: string }> = {}) {
  const asked: Request[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/ask") asked.push(request);
  });
  const unrecorded = await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    "/api/projects/P130164": { body: await recorded("project-p130164.json") },
    "/api/projects/P156634": { body: await recorded("project-p156634.json") },
    "/api/lookup/loan": { body: await recorded("lookup-loan-ida-60290.json") },
    "/api/lookup/activity": { body: await recorded("lookup-activity-ke-nwwda-541055-cw-rfb.json") },
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    ...extra,
  });
  await page.goto(path);
  await expect(page.locator("main h1")).toBeVisible();
  return { asked, unrecorded };
}

const box = (page: Page) => page.locator("[data-box-band]").getByRole("combobox");
const options = (page: Page) => page.getByRole("listbox", { name: "What Enter will do" }).getByRole("option");

async function typeInBox(page: Page, text: string) {
  await page.keyboard.press("/");
  await expect(box(page)).toBeFocused();
  await page.keyboard.type(text);
}

test("typing a project ID lists Open first, with the project's name once it is looked up, and Enter opens it", async ({ page }) => {
  const { asked } = await open(page);

  await typeInBox(page, "P130164");

  await expect(options(page).first()).toHaveAccessibleName("Open P130164 Rajasthan Road Sector Modernization Project, India");
  await expect(options(page).first()).toHaveAttribute("aria-selected", "true");
  await expect(box(page)).toHaveAttribute("aria-expanded", "true");
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(/\/projects\/P130164$/);
  await expect(page.locator("main h1")).toBeFocused();
  await expect(box(page)).toHaveValue("");
  expect(asked).toEqual([]);
});

for (const written of ["IDA60290", "IDA-60290", "IDA / 60290", "60290"]) {
  test(`the loan number ${written} opens the project it finances`, async ({ page }) => {
    await open(page);

    await typeInBox(page, written);

    await expect(options(page).first()).toHaveAccessibleName(
      "Open the project for IDA-60290 P156634, Water and Sanitation Development Project",
    );
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/\/projects\/P156634$/);
  });
}

test("a bare five-digit number offers Ask this first until the lookup finds its loan", async ({ page }) => {
  let answer: () => void = () => {};
  const held = new Promise<void>((resolve) => (answer = resolve));
  await open(page);
  await page.route("**/api/lookup/loan**", async (route) => {
    await held;
    await route.fulfill({ contentType: "application/json", body: await recorded("lookup-loan-ida-60290.json") });
  });

  await typeInBox(page, "60290");

  await expect(options(page)).toHaveCount(1);
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
  answer();
  await expect(options(page).first()).toHaveAccessibleName(/^Open the project for IDA-60290/);
  await expect(options(page).nth(1)).toHaveAccessibleName("Ask this Across all projects");
});

test("a STEP reference opens its plan's check with that activity in view and focused", async ({ page }) => {
  await open(page);

  await typeInBox(page, "KE-NWWDA-541055-CW-RFB");

  await expect(options(page).first()).toHaveAccessibleName(
    "Show KE-NWWDA-541055-CW-RFB in its plan In the Northern Water Works Development Agency plan of October 9, 2026, P156634",
  );
  await page.keyboard.press("Enter");

  await expect(page).toHaveURL(new RegExp(`${PLAN}#KE-NWWDA-541055-CW-RFB$`));
  const row = page.locator("[data-view=table] [data-activity='KE-NWWDA-541055-CW-RFB']");
  await expect(row).toBeFocused();
  await expect(row).toBeInViewport();
  await expect(page.locator("tr[id='KE-NWWDA-541055-CW-RFB']")).toHaveAttribute("data-named", "true");
});

// The critique of ticket 14, round 2: a landing that cuts the title or the box at the top edge reads as
// a scroll gone wrong. The row is in view, and the band and the title are each wholly in view or wholly
// scrolled away.
for (const width of [1440, 390]) {
  test(`at ${width} px landing on a STEP reference cuts neither the band nor the title at the top edge`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await open(page);
    await typeInBox(page, "KE-NWWDA-541055-CW-RFB");
    await expect(options(page).first()).toContainText("Northern Water Works Development Agency");
    await page.keyboard.press("Enter");

    const view = width >= 1024 ? "table" : "cards";
    const row = page.locator(`[data-view=${view}] [data-activity='KE-NWWDA-541055-CW-RFB']`);
    await expect(row).toBeFocused();
    await expect(row).toBeInViewport({ ratio: 1 });
    await page.waitForTimeout(100);
    for (const part of ["[data-box-band]", "main h1"]) {
      const box = (await page.locator(part).boundingBox())!;
      expect(box.y >= 0 || box.y + box.height <= 0, `${part} at ${Math.round(box.y)} px, ${Math.round(box.height)} px tall`).toBe(true);
    }
  });
}

test("free text offers Ask this, and nothing is sent until the person chooses it", async ({ page }) => {
  const { asked } = await open(page);

  await typeInBox(page, "Why were works contracts advertised again?");

  await expect(options(page)).toHaveCount(1);
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
  await expect(options(page).first()).toContainText("Enter");
  await page.waitForTimeout(400);
  expect(asked).toEqual([]);
  await expect(page.getByRole("region", { name: "Answer" })).toHaveCount(0);
});

test("free text that holds one project ID also offers to open it, second", async ({ page }) => {
  await open(page);

  await typeInBox(page, "Why were works contracts in P130164 advertised again?");

  await expect(options(page)).toHaveCount(2);
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
  await expect(options(page).nth(1)).toHaveAccessibleName(/^Open P130164/);
  await page.keyboard.press("ArrowDown");
  await expect(options(page).nth(1)).toHaveAttribute("aria-selected", "true");
  await expect(box(page)).toHaveAttribute("aria-activedescendant", (await options(page).nth(1).getAttribute("id"))!);
});

test("an ID no record holds says so under the list, and Ask this is the only option", async ({ page }) => {
  await open(page, "/", { "/api/projects/P999999": { status: 404, body: '{"code":"unknown_project"}' } });

  await typeInBox(page, "P999999");

  await expect(page.getByText("I have no project P999999.")).toBeVisible();
  await expect(options(page)).toHaveCount(1);
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
});

// DESIGN.md section 3: Roboto Mono for IDs, wherever the box writes one.
async function idFaces(page: Page, id: string) {
  return page.locator("[data-box-band]").evaluate(
    (band, wanted) =>
      Array.from(band.querySelectorAll("*"))
        .filter((element) => element.children.length === 0 && element.textContent === wanted)
        .map((element) => getComputedStyle(element).fontFamily.split(",")[0].replaceAll('"', "")),
    id,
  );
}

test("every ID the box writes is in Roboto Mono: in an option, its second line and the not-found line", async ({ page }) => {
  await open(page, "/", { "/api/projects/P999999": { status: 404, body: '{"code":"unknown_project"}' } });

  await typeInBox(page, "IDA-60290");
  await expect(options(page).first()).toContainText("P156634, Water and Sanitation Development Project");
  expect(await idFaces(page, "IDA-60290")).toEqual(["Roboto Mono"]);
  expect(await idFaces(page, "P156634")).toEqual(["Roboto Mono"]);

  await box(page).fill("KE-NWWDA-541055-CW-RFB");
  await expect(options(page).first()).toContainText("P156634");
  expect(await idFaces(page, "P156634")).toEqual(["Roboto Mono"]);

  await box(page).fill("P999999");
  await expect(page.getByText("I have no project P999999.")).toBeVisible();
  expect(await idFaces(page, "P999999")).toEqual(["Roboto Mono"]);
});

test("a lookup that fails says so, and the person can still ask", async ({ page }) => {
  await open(page, "/", { "/api/lookup/activity": { status: 503, body: '{"code":"data_service"}' } });

  await typeInBox(page, "KE-NWWDA-541055-CW-RFB");

  await expect(page.getByText("I couldn't look up KE-NWWDA-541055-CW-RFB just now. You can still ask about it.")).toBeVisible();
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
});

test("focused and empty, the box gives its hint; Escape closes the list, then empties the box", async ({ page }) => {
  await open(page);

  await page.keyboard.press("/");
  await expect(box(page)).toHaveAccessibleDescription(
    "Type a project ID such as P130164, a STEP reference, a loan number, or a question.",
  );
  await page.keyboard.type("P130164");
  await expect(options(page)).toHaveCount(2);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("listbox")).toHaveCount(0);
  await expect(box(page)).toHaveValue("P130164");
  await expect(box(page)).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(box(page)).toHaveValue("");
});

test("on a project page the box carries a removable scope chip, and Backspace in the empty box removes it", async ({ page }) => {
  await open(page, "/projects/P130164");

  await expect(box(page)).toHaveAccessibleName("Open a project or package, or ask a question");
  await expect(box(page)).toHaveAccessibleDescription(/Questions you ask here cover P130164 only\./);
  await expect(page.locator("[data-box-band]").getByText("Ask about this project")).toBeVisible();
  const remove = page.getByRole("button", { name: "Remove the scope P130164" });
  await expect(remove).toBeVisible();

  await page.keyboard.press("/");
  await page.keyboard.type("Why?");
  await expect(options(page).first()).toHaveAccessibleName("Ask this Within P130164");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Backspace");

  await expect(remove).toHaveCount(0);
  await expect(page.locator("[data-box-band] [role=status]")).toHaveText(
    "The scope is removed. Questions now cover all projects.",
  );
  await page.keyboard.type("Why?");
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
});

test("/ focuses the box from anywhere outside a text field, and is not typed", async ({ page }) => {
  await open(page);
  await page.locator("main h1").focus();

  await page.keyboard.press("/");

  await expect(box(page)).toBeFocused();
  await expect(box(page)).toHaveValue("");
  await expect(box(page)).toHaveAttribute("aria-keyshortcuts", "/");
});
