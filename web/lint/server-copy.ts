// The words the server writes, copied from web/src/copy.ts into JSON files the server reads, so the copy
// file stays their one home:
//
// - src/strata/tools/data_readiness_copy.json: the Data readiness page's sentences
//   (copy.dataReadiness.server), which the data_readiness_for tool reads.
// - src/strata/drafts/copy.json: a draft's exported files (copy.draft.files), with the source lines,
//   the check line and the removed sentences' reasons they repeat, which the draft runtime reads
//   (ticket 35).
// - src/strata/knowledge/lessons/copy.json: the review queue's sentences (copy.lessons.server), whose count
//   words and forms the lesson review chooses on the server (ticket 29).
// - src/strata/estimates/steps.json: the step-label registry (web/src/steps.ts), whose families, family rule and
//   STEP step names estimate_time reads to date each step (ticket 27).
// - src/strata/server/timeline_copy.json: a project timeline's title and alt text (copy.timeline.server), with the
//   words for one to nine, which the timeline route writes on the server (ticket 23).
// - src/strata/dashboard/copy.json: the AI/BI dashboard's words (copy.dash and copy.kpi), which the dashboard
//   generator and the nightly job's "What the measures say" read (ticket 45).
//
// The lint lane fails when a JSON file is out of date (web/lint/run.ts), and this command writes them
// again:
//
//     node web/lint/server-copy.ts --write
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { copy } from "../src/copy.ts";
import { stepFamilies } from "../src/steps.ts";

const at = (path: string) => fileURLToPath(new URL(`../../${path}`, import.meta.url));

export const SERVER_COPY_FILE = at("src/strata/tools/data_readiness_copy.json");
export const DRAFTS_COPY_FILE = at("src/strata/drafts/copy.json");
export const LESSONS_COPY_FILE = at("src/strata/knowledge/lessons/copy.json");
export const STEPS_COPY_FILE = at("src/strata/estimates/steps.json");
export const TIMELINE_COPY_FILE = at("src/strata/server/timeline_copy.json");
export const DASHBOARD_COPY_FILE = at("src/strata/dashboard/copy.json");

const json = (words: unknown) => `${JSON.stringify(words, null, 2)}\n`;

export function serverCopy(): string {
  return json({
    ...copy.dataReadiness.server,
    words: copy.num.words,
    badges: { partial: copy.badge.partial, gap: copy.badge.gap },
    footer: copy.footer,
  });
}

export function draftsCopy(): string {
  const kinds = Object.entries(copy.draft.kinds);
  return json({
    files: copy.draft.files,
    // Each kind's hold lines by copy key, as the draft bar looks them up, so a test can check every hold
    // in config/drafts.toml has its sentence; and the kind's own words for removed sentences' reasons.
    holds: Object.fromEntries(kinds.map(([key, words]) => [key, { ...copy.draft.bar.hold, notChecked: words.holdNotChecked }])),
    removedReasons: Object.fromEntries(kinds.map(([key, words]) => [key, words.removedReasons])),
    source: copy.source,
    recordSource: copy.evidence.recordSource,
    recordSourceShort: copy.evidence.recordSourceShort,
    // A record a mission brief cites names its source by its key, and its totals record by the tool (ticket 37).
    summaryRecordSources: copy.evidence.summaryRecordSources,
    toolSource: copy.evidence.toolSource,
    // A passage, the counts of comparable completion reports and a lesson version, as the pack names them (ticket 36).
    passageSource: copy.evidence.passageSource,
    passageParagraph: copy.evidence.passageParagraph,
    passageSection: copy.evidence.passageSection,
    countsSource: copy.evidence.countsSource,
    lessonSource: copy.evidence.lessonSource,
    // A suggested PPSD row's passage footnote writes each source as its pill does (ticket 36).
    pill: { pill: copy.packageRisks.pill, pillNoProject: copy.packageRisks.pillNoProject, pillParagraph: copy.packageRisks.pillParagraph },
    checkLine: copy.checkLine,
    removed: { reasons: copy.removed.reasons, unknownReason: copy.removed.unknownReason },
    notVisible: copy.checkPlan.notVisible,
    footer: copy.footer,
  });
}

export function lessonsCopy(): string {
  // The Lessons page (ticket 39) writes its count words on the server, from one to nine, and the feedback sentence
  // from ticket 32's templates, so both keep one home in the copy file.
  return json({ ...copy.lessons.server, words: copy.num.words, feedback: copy.retrieval.sentence });
}

export function stepsCopy(): string {
  return json({ families: stepFamilies });
}

export function timelineCopy(): string {
  return json({ ...copy.timeline.server, numberWords: copy.num.words });
}

// The dashboard's words (ticket 45): titles, descriptions, text tiles, the words its queries show, and the templates
// the nightly job fills for "What the measures say", with the words for one to nine and the months.
export function dashboardCopy(): string {
  return json({
    dash: copy.dash,
    kpi: copy.kpi,
    words: copy.num.words,
    months: copy.dataReadiness.server.months,
    footer: copy.footer,
  });
}

// Each JSON file, and the words it must hold.
export const SERVER_COPIES: { file: string; words: () => string; from: string }[] = [
  { file: SERVER_COPY_FILE, words: serverCopy, from: "copy.dataReadiness.server" },
  { file: DRAFTS_COPY_FILE, words: draftsCopy, from: "copy.draft.files" },
  { file: LESSONS_COPY_FILE, words: lessonsCopy, from: "copy.lessons.server" },
  { file: STEPS_COPY_FILE, words: stepsCopy, from: "web/src/steps.ts" },
  { file: TIMELINE_COPY_FILE, words: timelineCopy, from: "copy.timeline.server" },
  { file: DASHBOARD_COPY_FILE, words: dashboardCopy, from: "copy.dash and copy.kpi" },
];

function isCurrent(file: string, words: () => string): boolean {
  try {
    return readFileSync(file, "utf8") === words();
  } catch {
    return false;
  }
}

// Whether the Data readiness file says what the copy file says.
export function serverCopyIsCurrent(): boolean {
  return isCurrent(SERVER_COPY_FILE, serverCopy);
}

// The JSON files that are out of date with the copy file.
export function staleServerCopies(): { file: string; from: string }[] {
  return SERVER_COPIES.filter((entry) => !isCurrent(entry.file, entry.words));
}

if (process.argv.includes("--write") && fileURLToPath(import.meta.url) === resolve(process.argv[1])) {
  for (const entry of SERVER_COPIES) {
    writeFileSync(entry.file, entry.words());
    console.log(`Wrote ${entry.file}.`);
  }
}
