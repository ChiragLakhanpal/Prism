// The capture command covers every gallery page at 1440, 1024 and 390 px, with hover and
// keyboard-focus shots, so design reviews are repeatable (criterion 10 of ticket 02). The
// whole command is not a gate step; these tests check its list of shots and run one of them.
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
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

// Ticket 95: every Task zone state at 1440 and 390 px, and the open and closed zones at 1024 px too.
test("the capture list photographs each Task zone state at 1440 and 390 px, and open and closed at 1024 px", () => {
  const widths = (state: string) => SHOTS.find((shot) => shot.name === `zones--state-${state}`)?.widths ?? [];
  for (const state of ["open", "closed", "loading", "error", "empty"]) {
    expect(widths(state), state).toEqual(expect.arrayContaining([1440, 390]));
  }
  expect(widths("open")).toContain(1024);
  expect(widths("closed")).toContain(1024);
});

// Ticket 98: Home on the workspace layout, with an answer asked from Home, and the officer's and the public's Home.
test("the capture list photographs Home answered, the officer's Home and the public's Home at 1440 px", () => {
  for (const name of ["home--populated", "home--first-run", "home--quiet-week", "home--answered", "home--officer", "home--public"]) {
    const shot = SHOTS.find((candidate) => candidate.name === name);
    expect(shot?.server, name).toBe("app");
    expect(shot?.widths ?? WIDTHS, name).toContain(1440);
  }
  expect(SHOTS.find((shot) => shot.name === "home--answered")?.api?.["/api/ask"]?.recorded).toBe("ask-p130164-rebidding.sse");
});

// Ticket 104: Data readiness at three widths, its closed rows opened, and beside the evidence drawer at 1024 px.
test("the capture list photographs Data readiness at 1440, 1024 and 390 px, with its rows open, and beside the drawer at 1024 px", () => {
  const shot = (name: string) => SHOTS.find((candidate) => candidate.name === `data--${name}`);
  expect(shot("readiness")?.widths ?? WIDTHS).toEqual([1440, 1024, 390]);
  expect(shot("rows-open")?.full).toBe(true);
  expect(shot("beside-drawer")?.widths).toEqual([1024]);
  expect(shot("beside-drawer")?.path).toContain("?evidence=");
});

// Ticket 102: Lessons (populated, a first visit and a failed read), a review page, Passage reports and Judging at the
// three widths. Every shot of the Lessons page answers who is viewing and the page's one read, so only the error shot
// shows a load error (ticket 60's note: the shell's shots on /lessons showed one).
test("the capture list photographs Lessons, a review page, Passage reports and Judging at 1440, 1024 and 390 px, and no Lessons shot fails by mistake", () => {
  for (const name of ["lessons--page", "lessons--page-first-visit", "lessons--library-error", "lessons--review--recommend", "retrieval--reports", "retrieval--judging", "retrieval--query"]) {
    const shot = SHOTS.find((candidate) => candidate.name === name);
    expect(shot?.server, name).toBe("app");
    expect(shot?.widths ?? WIDTHS, name).toEqual(WIDTHS);
  }
  const library = SHOTS.filter((shot) => shot.server === "app" && /^\/lessons(\?|$)/.test(shot.path));
  expect(library.map((shot) => shot.name)).toEqual(expect.arrayContaining(["app--lessons", "app--view-piu", "app--asof", "app--menu-open"]));
  for (const shot of library) {
    expect(shot.api?.["/api/lessons/me"], shot.name).toBeDefined();
    const read = shot.api?.["/api/lessons/page"];
    if (shot.name === "lessons--library-error") expect(read?.status, shot.name).toBe(503);
    else expect(Boolean(read && (read.status ?? 200) === 200 && (read.recorded || read.body)), shot.name).toBe(true);
  }
});

// Round 1 of ticket 102: a Lessons shot as of a past date shows the page the server sends for that date, recorded by
// tests/record_lessons_page_api.py, and never today's page with only its date changed (an answer as of a date never
// cites a document made public after it).
test("a Lessons shot as of a past date answers with the server's recording for that date", () => {
  const dated = SHOTS.filter((shot) => shot.server === "app" && /^\/lessons\?(.*&)?asof=\d{4}-\d{2}-\d{2}/.test(shot.path));
  expect(dated.map((shot) => shot.name)).toContain("app--asof");
  for (const shot of dated) {
    const asof = new URL(shot.path, "http://strata.test").searchParams.get("asof");
    const read = shot.api?.["/api/lessons/page"];
    expect(read?.body, shot.name).toBeUndefined();
    expect(read?.recorded, shot.name).toBeDefined();
    const page = JSON.parse(readFileSync(new URL(`../../tests/fixtures/api/${read!.recorded}`, import.meta.url), "utf8"));
    expect(page.as_of, shot.name).toBe(asof);
  }
});

test("the capture list has hover and keyboard-focus shots, and app shots against the recorded API", () => {
  expect(SHOTS.filter((shot) => shot.name.includes("--hover-")).length).toBeGreaterThan(5);
  expect(SHOTS.filter((shot) => shot.name.includes("--focus-")).length).toBeGreaterThan(5);
  expect(SHOTS.some((shot) => shot.server === "app" && shot.api?.["/api/me"]?.recorded === "me.json")).toBe(true);
});

test("the capture command takes a shot and saves it as a picture", () => {
  test.setTimeout(60_000);
  const out = mkdtempSync(join(tmpdir(), "strata-capture-"));
  // The child picks its own free ports, so it never clashes with this run's servers.
  const env: Record<string, string | undefined> = { ...process.env, STRATA_CAPTURE_DIR: out };
  delete env.STRATA_TEST_WEB_PORT;
  delete env.STRATA_TEST_GALLERY_PORT;
  const done = spawnSync(
    "npx",
    ["playwright", "test", "--config", "playwright.capture.config.ts", "-g", " badges at 390 px$", "--reporter=line"],
    { cwd: fileURLToPath(new URL("..", import.meta.url)), env, encoding: "utf8" },
  );
  expect(done.status, done.stdout + done.stderr).toBe(0);
  expect(statSync(join(out, "badges--390.png")).size).toBeGreaterThan(1000);
});
