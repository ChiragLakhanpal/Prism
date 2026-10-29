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

// Ticket 103: the Drafts list grouped, empty and in error, and a draft just marked as checked, at three widths.
test("the capture list photographs the Drafts list grouped, empty and in error, and a draft just marked as checked, at 1440, 1024 and 390 px", () => {
  for (const name of ["drafts-tab", "drafts-tab--empty", "drafts-tab--error", "draft", "draft--checked", "draft--marked-checked", "draft--error"]) {
    const shot = SHOTS.find((candidate) => candidate.name === name);
    expect(shot?.server, name).toBe("app");
    expect(shot?.widths ?? WIDTHS, name).toEqual([1440, 1024, 390]);
  }
  expect(SHOTS.find((shot) => shot.name === "draft--marked-checked")?.act).toBeDefined();
});

// Ticket 105: How I checked this answer and this draft, open, and a drawer's list landed on the row you came back to,
// at 1440 and 390 px.
test("the capture list photographs the check windows and a drawer's landed row at 1440 and 390 px", () => {
  for (const name of ["checks--how-window", "checks--how-window-draft", "evidence--landed-row"]) {
    const shot = SHOTS.find((candidate) => candidate.name === name);
    expect(shot?.server, name).toBe("app");
    expect(shot?.widths, name).toEqual([1440, 390]);
    expect(shot?.act, name).toBeDefined();
  }
  expect(SHOTS.find((shot) => shot.name === "checks--how-window-draft")?.api?.["/api/drafts/draft-0002"]?.recorded).toBe("drafts-review-notes-partial.json");
});

// Ticket 60: the outage states, the criteria with no judge, a draft another tab exported, and the view switch's shots,
// which take 800 px since the switch sits in the bar from 768 px (ticket 93's design review, follow-up 7).
test("the capture list photographs ticket 60's states at their widths", () => {
  const widths = (name: string) => SHOTS.find((shot) => shot.name === name)?.widths ?? WIDTHS;
  for (const name of [
    "checks--judge-silent-some-failed",
    "checks--removed-check-6-some-kept",
    "checks--removed-check-6-mixed",
    "checks--partial-refusal-unchecked",
    "criteria--readings-unjudged",
    "draft--conflict-exported",
  ]) {
    expect(SHOTS.some((shot) => shot.name === name), name).toBe(true);
    expect(widths(name), name).toEqual([1440, 1024, 390]);
  }
  for (const name of ["navigation--hover-pill", "navigation--focus-pill", "navigation--view-open"]) expect(widths(name), name).toEqual([1440, 1024, 800]);
});

// Ticket 60 (ticket 21's review, round 4, follow-up 3): a source page's table and a plan's STEP rows show as a table in
// its frame at 1024 px, so their shots take that width too, and the gallery shows both.
test("the source page's table and plan rows are captured at 1440, 1024, 390 and 320 px", () => {
  for (const name of ["source--table", "source--plan-rows"]) {
    expect(SHOTS.find((shot) => shot.name === name)?.widths, name).toEqual([1440, 1024, 390, 320]);
  }
});

// Ticket 60 (ticket 30's review, F12; its design review, B1): the risks shots pair section 1 and section 3 as the app
// does. Section 1's answer was read with the criteria section 3 was read with, so every comparable package section 3
// counted is one section 1 matched; the shots answer every route the package page reads; and the planned shots whose
// packages lack criteria or divide a package answer section 3 too.
const recording = (name: string) => JSON.parse(readFileSync(new URL(`../../tests/fixtures/api/${name}`, import.meta.url), "utf8"));
test("the risks shots pair section 1 and section 3 read with the same criteria, and every planned shot answers sections 2, 3 and 5", () => {
  const api = "/api/packages/KE-NWWDA-541055-CW-RFB";
  const shots = SHOTS.filter((candidate) => candidate.name.startsWith("risks--") && candidate.api?.[`${api}/risks`]?.recorded);
  expect(shots.map((shot) => shot.name)).toContain("risks--table");
  for (const shot of shots) {
    const risks = recording(shot.api![`${api}/risks`].recorded!);
    const comparables = recording(shot.api![`${api}/comparables`].recorded!);
    if (shot.api![`${api}/risks`].recorded!.includes("-india")) {
      // tests/record_risks_api.py reads India's risks with these criteria.
      expect([comparables.criteria.country, comparables.criteria.notice_from], shot.name).toEqual(["IN", "2013-01-01"]);
    }
    const matched = new Set<string>([
      ...comparables.rows.map((row: { step_reference: string }) => row.step_reference),
      ...comparables.coverage.not_used.flatMap((group: { step_references: string[] }) => group.step_references),
    ]);
    const counted = new URL(risks.counts_evidence_id.replace(/^[^?]*/, "http://strata.test/")).searchParams.get("packages")!.split(",");
    expect(counted.filter((reference) => !matched.has(reference)), shot.name).toEqual([]);
    for (const route of ["steps", "estimate", "criteria", "criteria/run"]) expect(shot.api![`${api}/${route}`], `${shot.name}: ${route}`).toBeDefined();
  }
  expect(SHOTS.find((shot) => shot.name === "planned--missing")?.api?.["/api/planned-packages/pkg-000000000002/risks"]?.recorded).toBe("risks-planned-yourself.json");
  expect(SHOTS.find((shot) => shot.name === "planned--dividing")?.api?.["/api/planned-packages/pkg-000000000003/risks"]).toBeDefined();
  expect(recording("risks-planned-yourself.json").empty_reason).toBe("missing_criteria");
  // Sections 2 and 5 answer for those packages too (its design review, F6).
  for (const [name, id] of [["planned--missing", "pkg-000000000002"], ["planned--dividing", "pkg-000000000003"]]) {
    const api = SHOTS.find((shot) => shot.name === name)?.api ?? {};
    for (const route of ["steps", "criteria"]) expect(api[`/api/planned-packages/${id}/${route}`]?.recorded, `${name}: ${route}`).toBeDefined();
  }
});

// Ticket 60 (ticket 29's design review, round 3, F8): a change or a retirement is decided on a lesson that already has a
// version, and its record's history names the version its outcome names, so the panel and the history agree.
test("a changed or retired lesson's captured record names the same version in its history and its outcome", () => {
  for (const name of ["lessons--review--decided-changed", "lessons--review--decided-retired"]) {
    const shot = SHOTS.find((candidate) => candidate.name === name)!;
    expect(shot.path, name).toContain("/recheck-");
    const [, answer] = Object.entries(shot.api ?? {}).find(([key]) => key.startsWith("/api/lessons/review/"))!;
    const body = JSON.parse(answer.body!);
    const decided = body.history.findLast((event: { event: string }) => event.event === "decided");
    expect(decided.version, name).toBe(body.outcome.version);
    expect(body.outcome.version, name).toBe(2);
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
