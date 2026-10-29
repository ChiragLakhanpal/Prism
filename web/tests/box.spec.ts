// The one box (ticket 14) at seam 4: as you type it lists what Enter will do, from one set of intent
// rules, and nothing happens until you choose. The lookups are answered from the responses recorded
// in tests/fixtures/api, which the server tests check the server against. The words are the ticket's
// and the 14 design brief's, copied here so the test checks the copy file against an independent source.
import type { Page, Request } from "@playwright/test";
import { scan } from "./axe";
import { expect, mockApi, recorded, test } from "./mocked";
import { tabUnderStickyParts } from "./sticky";

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
    // Ticket 21: a project's address opens its Summary.
    "/api/projects/P130164/summary": { body: await recorded("summary-p130164.json") },
    "/api/projects/P156634/summary": { body: await recorded("summary-p156634.json") },
    "/api/lookup/loan": { body: await recorded("lookup-loan-ida-60290.json") },
    "/api/lookup/activity": { body: await recorded("lookup-activity-ke-nwwda-541055-cw-rfb.json") },
    [`/api${PLAN}`]: { body: await recorded("check-plan-p156634-nwwda-2026-10-09.json") },
    ...extra,
  });
  await page.goto(path);
  await expect(page.locator("main h1")).toBeVisible();
  return { asked, unrecorded };
}

const box = (page: Page) => page.locator("[data-box-slot]").getByRole("combobox");
const options = (page: Page) => page.getByRole("listbox", { name: "What Enter will do" }).getByRole("option");

// Ticket 113: the box floats at the window's foot, so its list opens above it, at its width.
async function listAboveTheBox(page: Page) {
  const list = (await page.locator("[data-box-popup]").boundingBox())!;
  const form = (await page.locator("[data-box-slot] form").boundingBox())!;
  expect([list.x, list.width], "the list at the box's width").toEqual([form.x, form.width]);
  expect(list.y + list.height, "the list above the box").toBeLessThanOrEqual(form.y);
}

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
  await listAboveTheBox(page);
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
// a scroll gone wrong. The whole row or card is in view, its badges included, and the bar and the title
// are each wholly in view or wholly scrolled away. From 1024 px the bar sticks (ticket 93), so the row
// lands under it.
for (const width of [1440, 390, 320]) {
  test(`at ${width} px landing on a STEP reference cuts neither the bar nor the title at the top edge`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await open(page);
    await typeInBox(page, "KE-NWWDA-541055-CW-RFB");
    await expect(options(page).first()).toContainText("Northern Water Works Development Agency");
    await page.keyboard.press("Enter");

    const view = width >= 1024 ? "table" : "cards";
    const row = page.locator(`[data-view=${view}] [data-activity='KE-NWWDA-541055-CW-RFB']`);
    await expect(row).toBeFocused();
    await expect(row.locator("xpath=ancestor-or-self::*[self::tr or self::li][1]")).toBeInViewport({ ratio: 1 });
    await page.waitForTimeout(100);
    for (const part of ["[data-nav-bar]", "main h1"]) {
      const box = (await page.locator(part).boundingBox())!;
      expect(box.y >= 0 || box.y + box.height <= 0, `${part} at ${Math.round(box.y)} px, ${Math.round(box.height)} px tall`).toBe(true);
    }
    // The row is not under the bar where the bar sticks.
    const bar = (await page.locator("[data-nav-bar]").boundingBox())!;
    const landed = (await row.locator("xpath=ancestor-or-self::*[self::tr or self::li][1]").boundingBox())!;
    if (width >= 1024) expect(landed.y).toBeGreaterThanOrEqual(bar.y + bar.height);
    // No line of text above the row is left as a sliver at the top edge or under the sticky header: a
    // line counts as cut when a whole pixel of it sits on each side.
    const cut = await page.evaluate(() => {
      const header = document.querySelector<HTMLElement>("[data-plan-header]");
      const edge = header && getComputedStyle(header).position === "sticky" ? header.getBoundingClientRect().bottom : 0;
      const walker = document.createTreeWalker(document.querySelector("main")!, NodeFilter.SHOW_TEXT);
      const lines: string[] = [];
      for (let node = walker.nextNode(); node; node = walker.nextNode()) {
        if (!node.textContent?.trim() || (header && header.contains(node)) || node.parentElement?.closest(".sr-only")) continue;
        const range = document.createRange();
        range.selectNodeContents(node);
        for (const rect of range.getClientRects()) {
          if (rect.width > 0 && rect.top <= edge - 1 && rect.bottom >= edge + 1) {
            lines.push(`"${node.textContent.trim()}" from ${Math.round(rect.top)} to ${Math.round(rect.bottom)} px`);
          }
        }
      }
      return lines;
    });
    expect(cut).toEqual([]);
  });
}

// Ticket 94: the frame's one hook keeps the scroll padding at the bar plus the plan check's sticky head, plus 8 px,
// so Tab down the page and Shift+Tab back up never leave the focused element under either. Ticket 113: and at the box
// that floats at the window's foot, 40 px tall and 16 px above the edge, plus 8 px, so nothing lands under it.
test("tabbing through the plan check never leaves the focused element under the bar, its sticky head or the box", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page, PLAN);
  const head = page.locator("[data-plan-header]");
  await expect(head).toHaveAttribute("data-sticky", "top");
  const height = await head.evaluate((element) => (element as HTMLElement).offsetHeight);
  expect(await page.evaluate(() => document.documentElement.style.scrollPaddingTop)).toBe(`${56 + height + 8}px`);
  // The bottom padding counts the box only while focus is in main (round 1's design review), as it is from the h1 on.
  await page.locator("main h1").first().focus();
  expect(await page.evaluate(() => document.documentElement.style.scrollPaddingBottom)).toBe(`${16 + 40 + 8}px`);
  const { checked, covered } = await tabUnderStickyParts(page, 30);
  expect(checked).toBeGreaterThan(40);
  expect(covered).toEqual([]);
});

// Ticket 15 gives free text a second option, "Plan a package from this sentence", which is never first
// (the 15 brief, section 7.1); web/tests/planned-package.spec.ts tests what choosing it does.
test("free text offers Ask this, then Plan a package, and nothing is sent until the person chooses one", async ({ page }) => {
  const { asked } = await open(page);

  await typeInBox(page, "Why were works contracts advertised again?");

  await expect(options(page)).toHaveCount(2);
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
  await expect(options(page).first()).toContainText("Enter");
  await expect(options(page).nth(1)).toHaveAccessibleName(
    "Plan a package from this sentence I'll read the criteria from your sentence and open a new package. You can change any of them.",
  );
  await page.waitForTimeout(400);
  expect(asked).toEqual([]);
  await expect(page.getByRole("region", { name: "Answer" })).toHaveCount(0);
});

test("free text that holds one project ID also offers to open it, second", async ({ page }) => {
  await open(page);

  await typeInBox(page, "Why were works contracts in P130164 advertised again?");

  await expect(options(page)).toHaveCount(3);
  await expect(options(page).first()).toHaveAccessibleName("Ask this Across all projects");
  await expect(options(page).nth(1)).toHaveAccessibleName(/^Open P130164/);
  await expect(options(page).nth(2)).toHaveAccessibleName(/^Plan a package from this sentence/);
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
  return page.locator("[data-box-slot]").evaluate(
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
  // DESIGN.md section 3: the hint's sample ID is in Roboto Mono, as every other ID the box writes, and so is the ID in
  // Home's second suggestion (ticket 112).
  expect(await idFaces(page, "P130164")).toEqual(["Roboto Mono", "Roboto Mono"]);
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
  await expect(page.locator("[data-box-slot]").getByText("Ask about this project")).toBeVisible();
  const remove = page.getByRole("button", { name: "Remove the scope P130164" });
  await expect(remove).toBeVisible();

  await page.keyboard.press("/");
  await page.keyboard.type("Why?");
  await expect(options(page).first()).toHaveAccessibleName("Ask this Within P130164");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Escape");
  await page.keyboard.press("Backspace");

  await expect(remove).toHaveCount(0);
  await expect(page.locator("[data-box-slot] [role=status]")).toHaveText(
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

// Tickets 12 and 14 together: on a package page the chip holds a STEP reference, which is far longer
// than a P-code. Below 1024 px, when the chip and a box you can type in do not fit on one line, the chip
// takes a row of its own above the text; a reference wider than that row breaks after a hyphen inside the
// chip. From 1024 px the box keeps one row in the bar (ticket 93): the chip keeps its reference whole on
// one line, and the text field gives way. The page never scrolls sideways, and what you type stays in view.
const LONG_REF = "KE-NWWDA-541055-CW-RFB-LOT-0001-2026-ABC";

async function openPackage(page: Page, ref: string, width: number) {
  await page.setViewportSize({ width, height: 900 });
  // Another reference answers with the same package under that reference: a package the page cannot find is no scope,
  // so its box has no chip (ticket 60).
  const found = JSON.parse(await recorded("package-ke-nwwda-541055.json"));
  found.package.step_reference = ref;
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`/api/packages/${encodeURIComponent(ref)}`]: { body: JSON.stringify(found) },
    [`/api/packages/${ref}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
  });
  await page.goto(`/packages/${encodeURIComponent(ref)}`);
  await expect(page.locator("main h1")).toBeVisible();
}

const rect = async (page: Page, selector: string) => (await page.locator(selector).boundingBox())!;

for (const ref of ["KE-NWWDA-541055-CW-RFB", LONG_REF]) {
  test(`at every width the scope chip keeps ${ref.length === 22 ? "a STEP reference" : "a 40-character reference"} whole inside the box, and the box stays wide enough to type in`, async ({ page }) => {
    for (const width of [320, 390, 768, 1024, 1440]) {
      await openPackage(page, ref, width);
      const chip = page.locator("[data-box-slot] [data-scope-chip]");
      await expect(chip).toContainText(ref);

      expect(await page.evaluate(() => document.documentElement.scrollWidth), `${width} px`).toBeLessThanOrEqual(width);
      const outer = await rect(page, "[data-box-slot] form > [data-focus-ring]");
      const inner = await rect(page, "[data-box-slot] [data-scope-chip]");
      expect(inner.x, `${width} px: the chip's left edge`).toBeGreaterThanOrEqual(outer.x);
      expect(inner.x + inner.width, `${width} px: the chip's right edge`).toBeLessThanOrEqual(outer.x + outer.width);
      // Below 1024 px, room for about ten characters of a question, and for the whole placeholder on a package page.
      // From 1024 px one row of 40 px, the chip's reference on one line, and room for about six characters; the
      // placeholder of a reference this long gives way there (gallery-frame.spec.ts proves the real one's is whole).
      const field = await rect(page, "[data-box-slot] input");
      const cut = await page.locator("[data-box-slot] [data-placeholder]").evaluate((el) => el.scrollWidth > el.clientWidth);
      if (width < 1024) {
        expect(field.width, `${width} px: the text field`).toBeGreaterThanOrEqual(96);
        expect(cut, `${width} px: the placeholder is cut`).toBe(false);
      } else {
        expect(outer.height, `${width} px: one row`).toBe(40);
        expect(inner.height, `${width} px: the reference on one line`).toBe(32);
        expect(field.width, `${width} px: the text field`).toBeGreaterThanOrEqual(64);
        if (ref.length === 22) expect(cut, `${width} px: the placeholder is cut`).toBe(false);
      }
      // The "/" hint, where a keyboard is assumed, stays at the end of the text field's row.
      const hint = page.locator("[data-box-slot] kbd");
      if (await hint.isVisible()) {
        const key = await hint.boundingBox();
        expect(Math.round(key!.y + key!.height / 2), `${width} px: the / hint`).toBe(Math.round(field.y + field.height / 2));
      }
    }
  });
}

test("a reference wider than its row breaks after a hyphen inside the chip, and one that fits a line moves there whole", async ({ page }) => {
  for (const [width, wider] of [[320, true], [390, true], [768, false]] as const) {
    await openPackage(page, LONG_REF, width);
    const lines = await page.locator("[data-box-slot] [data-scope-chip] .font-mono").evaluate((element) => {
      const rows = new Map<number, string>();
      const text = element.firstChild!;
      for (let i = 0; i < text.textContent!.length; i++) {
        const range = document.createRange();
        range.setStart(text, i);
        range.setEnd(text, i + 1);
        const top = Math.round(range.getBoundingClientRect().top);
        rows.set(top, (rows.get(top) ?? "") + range.toString());
      }
      return [...rows.entries()].sort((a, b) => a[0] - b[0]).map(([, line]) => line);
    });
    expect(lines.join(""), `${width} px`).toBe(LONG_REF);
    // At 768 px "Within" comes first, and the reference fits on the chip's next line whole.
    if (!wider) expect(lines, `${width} px`).toEqual([LONG_REF]);
    else expect(lines.length, `${width} px: ${lines.join(" | ")}`).toBeGreaterThan(1);
    // A chip that fills its row takes the box's whole row inside its padding: 12 px on the left, where the text under
    // it starts too, and 4 px on the right, where the remove button sits (ticket 93).
    if (wider) {
      const outer = await rect(page, "[data-box-slot] form > [data-focus-ring]");
      const chip = await rect(page, "[data-box-slot] [data-scope-chip]");
      expect(Math.round(chip.x - outer.x), `${width} px: the chip's left inset`).toBe(12);
      expect(Math.round(outer.x + outer.width - (chip.x + chip.width)), `${width} px: the chip's right inset`).toBe(4);
    }
    for (const [index, line] of lines.entries()) {
      expect(line.startsWith("-"), `${width} px, line ${index + 1}: ${lines.join(" | ")}`).toBe(false);
      if (index > 0) expect(lines[index - 1].endsWith("-"), `${width} px: ${lines.join(" | ")}`).toBe(true);
    }
  }
});

test("a press on the empty part of the chip's row puts the cursor in the text field, as a press on the field would", async ({ page }) => {
  await openPackage(page, "KE-NWWDA-541055-CW-RFB", 390);
  const outer = await rect(page, "[data-box-slot] form > [data-focus-ring]");
  const chip = await rect(page, "[data-box-slot] [data-scope-chip]");
  expect(await page.locator("[data-box-slot] form > [data-focus-ring]").evaluate((el) => getComputedStyle(el).cursor)).toBe("text");
  await page.mouse.click(outer.x + outer.width - 24, chip.y + chip.height / 2);
  await expect(page.locator("[data-box-slot] input")).toBeFocused();
});

// The whole box shows the text cursor, so a press anywhere in it outside the chip acts as a press on
// the field: on the "/" hint and on the search icon too. The chip keeps the pointer's own cursor.
test("a press on the box's / hint or its search icon puts the cursor in the text field, and the chip keeps its own cursor", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  await open(page);
  const input = page.locator("[data-box-slot] input");
  for (const part of ["kbd", "svg"]) {
    // Focus leaves the box for the h1 (a press would land on the box's suggestions, which lie over it; ticket 112).
    await page.locator("main h1").focus();
    await expect(input, part).not.toBeFocused();
    const target = page.locator(`[data-box-slot] form > [data-focus-ring] ${part}`).first();
    await expect(target, part).toBeVisible();
    await target.click();
    await expect(input, part).toBeFocused();
  }

  await openPackage(page, "KE-NWWDA-541055-CW-RFB", 1440);
  expect(await page.locator("[data-box-slot] [data-scope-chip]").evaluate((el) => getComputedStyle(el).cursor)).toBe("auto");
});

test("a P-code's chip on a phone and a STEP reference's chip on a wide screen sit on one row with the text, in a 40 px box", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 900 });
  await open(page, "/projects/P130164");
  const single = async (label: string) => {
    const outer = await rect(page, "[data-box-slot] form > [data-focus-ring]");
    const chip = await rect(page, "[data-box-slot] [data-scope-chip]");
    const field = await rect(page, "[data-box-slot] input");
    expect(Math.round(outer.height), label).toBe(40);
    expect(Math.round(chip.height), label).toBe(32);
    expect(Math.round(chip.y + chip.height / 2), label).toBe(Math.round(field.y + field.height / 2));
    expect(Math.round(field.x - (chip.x + chip.width)), `${label}: the gap after the chip`).toBe(8);
  };
  await single("P130164 at 390 px");

  await openPackage(page, "KE-NWWDA-541055-CW-RFB", 1440);
  await single("KE-NWWDA-541055-CW-RFB at 1440 px");
});

// Ticket 93 (DESIGN.md section 5, Top bar): below 1024 px the box takes a row of its own under the Menu button, the
// logo and the wordmark. Below 768 px Home's placeholder takes its short form, so it is never cut, and the field's
// name keeps the whole sentence; on a package page the placeholder sits under the chip. Below 360 px the search icon
// hides, for the field's room.
const PLACEHOLDER = async (page: Page) =>
  page.evaluate(() => {
    const shown = [...document.querySelectorAll<HTMLElement>("[data-box-slot] [data-placeholder]")].find((el) => el.getClientRects().length > 0)!;
    const field = document.querySelector<HTMLElement>("[data-box-slot] input")!;
    return { text: shown.textContent, width: shown.scrollWidth, field: field.getBoundingClientRect().width };
  });

for (const width of [390, 320]) {
  test(`below 1024 px the box has its own row, and at ${width} px its placeholder is narrower than the field on Home and on a package page`, async ({ page }) => {
    await page.setViewportSize({ width, height: 900 });
    await open(page);
    const outer = await rect(page, "[data-box-slot] form > [data-focus-ring]");
    const logo = await rect(page, "[data-nav-bar] img");
    expect(outer.y, "the box's own row").toBeGreaterThanOrEqual(logo.y + logo.height);
    expect([outer.x, outer.width]).toEqual([16, width - 32]);
    await expect(page.locator("[data-box-slot] form svg.lucide-search")).toBeVisible({ visible: width >= 360 });
    const home = await PLACEHOLDER(page);
    expect(home.text).toBe("Open a project or package, or ask");
    expect(home.width, `Home at ${width} px`).toBeLessThan(home.field);
    await expect(box(page)).toHaveAccessibleName("Open a project or package, or ask a question");

    await openPackage(page, "KE-NWWDA-541055-CW-RFB", width);
    const onPackage = await PLACEHOLDER(page);
    expect(onPackage.text).toBe("Ask about this package");
    expect(onPackage.width, `a package page at ${width} px`).toBeLessThan(onPackage.field);
  });
}

// The fixture's longest reference, with spaces, one of the package's 49 comparables (the plan's section 7.10).
test("at 390 px a chip with the fixture's longest reference takes its own row, with the text under it", async ({ page }) => {
  const ref = "KE-UASIN GISHU COUNTY-571338-CW-RFB";
  await openPackage(page, ref, 390);
  const chip = page.locator("[data-box-slot] [data-scope-chip]");
  await expect(chip).toContainText("KE-UASIN GISHU COUNTY-571338-CW-RFB");
  const [outer, inner, field] = [
    await rect(page, "[data-box-slot] form > [data-focus-ring]"),
    await rect(page, "[data-box-slot] [data-scope-chip]"),
    await rect(page, "[data-box-slot] input"),
  ];
  expect(Math.round(inner.x - outer.x), "the chip starts the box's first row").toBe(12);
  expect(field.y, "the text under the chip").toBeGreaterThanOrEqual(inner.y + inner.height);
  expect(Math.round(field.x), "the chip and the text share one left edge").toBe(Math.round(inner.x));
  expect(inner.x + inner.width).toBeLessThanOrEqual(outer.x + outer.width);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);
});

// Ticket 112: focused and empty, the box keeps its hint and suggests questions for the page, each a question of
// evals/benchmark.yaml without its as-of date (config/examples.toml's [[ask]], sent by GET /api/me). The words are the
// ticket's, copied here.
const PACKAGE = "KE-NWWDA-541055-CW-RFB";
const SUGGESTED = {
  package: [
    `How long did packages like ${PACKAGE} take from notice to signed contract?`,
    `How many packages like ${PACKAGE} were advertised again, and why?`,
    `Were packages like ${PACKAGE} signed above or below their cost estimates?`,
  ],
  project: ["Which contracts were signed on P156634 since its last ISR?", "Does P156634 need a look, and which signals put it there?"],
  plan: ["Which activities in this plan need a look, and why?"],
  home: [
    `How long did packages like ${PACKAGE} take from notice to signed contract?`,
    "Why did so many works contracts in P130164 go through rebidding?",
  ],
};
const group = (page: Page, name: string) => page.locator("[data-box-slot]").getByRole("group", { name });

// A move inside the app, as Back and Forward make one, so one page load serves every page.
async function moveTo(page: Page, path: string) {
  await page.evaluate((to) => {
    window.history.pushState({ key: `moved-${to}` }, "", to);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
  await expect(page).toHaveURL((url) => url.pathname === path);
}

test("focused and empty, each page's box keeps its hint and suggests the page's questions under the page's name; typing replaces them", async ({ page }) => {
  const { asked } = await open(page, "/", {
    "/api/home": { body: await recorded("home.json") },
    [`/api/packages/${PACKAGE}`]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`/api/packages/${PACKAGE}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
  });

  for (const [path, name, questions] of [
    ["/", "Ask, for example", SUGGESTED.home],
    ["/lessons", "Ask, for example", SUGGESTED.home],
    [`/packages/${PACKAGE}`, "Ask about this package", SUGGESTED.package],
    ["/projects/P156634", "Ask about this project", SUGGESTED.project],
    [PLAN, "Ask about this plan", SUGGESTED.plan],
  ] as const) {
    if (path !== "/") await moveTo(page, path);
    await page.locator("main h1").focus();
    await page.keyboard.press("/");
    await expect(box(page)).toHaveAccessibleDescription(/^Type a project ID such as P130164/);
    await expect(group(page, name).getByRole("option")).toHaveText([...questions]);
    await expect(box(page)).toHaveAttribute("aria-expanded", "true");
    // None is chosen until Down or Up moves to one, so Enter in the empty box asks nothing.
    await expect(group(page, name).getByRole("option", { selected: true })).toHaveCount(0);
    if (path === "/") {
      expect(await idFaces(page, PACKAGE)).toEqual(["Roboto Mono"]);
      expect(await idFaces(page, "P130164")).toEqual(["Roboto Mono", "Roboto Mono"]);
    }
  }

  await page.keyboard.type("P1");
  await expect(page.locator("[data-box-slot]").getByRole("group")).toHaveCount(0);
  await expect(options(page).first()).toHaveAccessibleName("Ask this Within P156634");
  expect(asked).toEqual([]);
});

async function openPackageToAsk(page: Page, width: number) {
  await page.setViewportSize({ width, height: 900 });
  const asked: Request[] = [];
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/ask") asked.push(request);
  });
  await mockApi(page, {
    "/api/me": { body: await recorded("me.json") },
    "/api/freshness": { body: await recorded("freshness.json") },
    [`/api/packages/${PACKAGE}`]: { body: await recorded("package-ke-nwwda-541055.json") },
    [`/api/packages/${PACKAGE}/comparables`]: { body: await recorded("comparables-ke-nwwda-541055.json") },
    "/api/ask": { body: await recorded("ask-ke-nwwda-541055-past-range.sse") },
  });
  await page.goto(`/packages/${PACKAGE}`);
  await expect(page.locator("main h1")).toBeVisible();
  return asked;
}

test("Down then Enter asks the first package suggestion within the package, a click asks another, and axe passes with the list open", async ({ page }) => {
  const asked = await openPackageToAsk(page, 1440);
  const answer = page.getByRole("region", { name: "Answer" });

  await page.keyboard.press("/");
  const suggestions = group(page, "Ask about this package").getByRole("option");
  await expect(suggestions).toHaveCount(3);
  await listAboveTheBox(page);
  expect((await scan(page)).violations).toEqual([]);
  await page.keyboard.press("ArrowDown");
  await expect(suggestions.first()).toHaveAttribute("aria-selected", "true");
  await expect(box(page)).toHaveAttribute("aria-activedescendant", (await suggestions.first().getAttribute("id"))!);
  await page.keyboard.press("Enter");

  await expect(box(page)).toHaveValue(SUGGESTED.package[0]);
  await expect(box(page)).toBeFocused();
  await expect(answer).toContainText("The middle half of the 49 comparable packages took 3.3 to 7.9 months");
  await expect(answer).toContainText(`Asked within ${PACKAGE}`);
  expect(asked.map((request) => [request.postDataJSON().question, request.postDataJSON().scope])).toEqual([[SUGGESTED.package[0], PACKAGE]]);
  // Ticket 101: the package page is a workspace page, so the answer takes the work's columns above the page head,
  // beside the side panel.
  await expect(page.locator("[data-workspace] [data-workspace-work]").filter({ has: answer })).toHaveCount(1);
  expect((await answer.boundingBox())!.y).toBeLessThan((await page.locator("[data-page-head]").boundingBox())!.y);
  await expect(page.getByRole("region", { name: "From the plan row" })).toBeVisible();

  // Empty the box, and a click in it brings the suggestions back; a click on one asks it the same way.
  await page.keyboard.press("Escape");
  await expect(box(page)).toHaveValue("");
  await box(page).click();
  await suggestions.nth(1).click();
  await expect(box(page)).toHaveValue(SUGGESTED.package[1]);
  await expect.poll(() => asked.map((request) => request.postDataJSON().question)).toEqual([SUGGESTED.package[0], SUGGESTED.package[1]]);
  expect(asked[1].postDataJSON().scope).toBe(PACKAGE);
});

test("at 390 px the package's suggestions open above the box with no WCAG 2.2 AA violation, and scroll inside a short window", async ({ page }) => {
  await openPackageToAsk(page, 390);

  await page.keyboard.press("/");
  await expect(group(page, "Ask about this package").getByRole("option")).toHaveCount(3);
  await listAboveTheBox(page);
  expect((await scan(page)).violations).toEqual([]);
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(390);

  // Ticket 113: the list is at most as tall as the window less the bar and 96 px, and scrolls inside.
  await page.setViewportSize({ width: 390, height: 360 });
  const list = page.locator("[data-box-popup]");
  await expect
    .poll(() => list.evaluate((el) => ({ height: Math.round(el.getBoundingClientRect().height), scrolls: el.scrollHeight > el.clientHeight })))
    .toEqual({ height: 360 - 56 - 96, scrolls: true });
  await listAboveTheBox(page);

  // Ticket 60 (ticket 93's review, F2): the active option scrolls into the list's view as the arrow keys move to it.
  const options = group(page, "Ask about this package").getByRole("option");
  for (let step = 0; step < 3; step++) await page.keyboard.press("ArrowDown");
  await expect(options.last()).toHaveAttribute("aria-selected", "true");
  const inside = async () => {
    const [frame, option] = [(await list.boundingBox())!, (await options.last().boundingBox())!];
    return option.y >= frame.y - 1 && option.y + option.height <= frame.y + frame.height + 1;
  };
  await expect.poll(inside).toBe(true);
});
