// The words the server writes, copied from web/src/copy.ts into JSON files the server reads, so the copy
// file stays their one home:
//
// - src/strata/tools/data_readiness_copy.json: the Data readiness page's sentences
//   (copy.dataReadiness.server), which the data_readiness_for tool reads.
// - src/strata/drafts/copy.json: a draft's exported files (copy.draft.files), with the source lines,
//   the check line and the removed sentences' reasons they repeat, which the draft runtime reads
//   (ticket 35).
//
// The lint lane fails when a JSON file is out of date (web/lint/run.ts), and this command writes them
// again:
//
//     node web/lint/server-copy.ts --write
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { copy } from "../src/copy.ts";

const at = (path: string) => fileURLToPath(new URL(`../../${path}`, import.meta.url));

export const SERVER_COPY_FILE = at("src/strata/tools/data_readiness_copy.json");
export const DRAFTS_COPY_FILE = at("src/strata/drafts/copy.json");

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
  return json({
    files: copy.draft.files,
    source: copy.source,
    recordSource: copy.evidence.recordSource,
    recordSourceShort: copy.evidence.recordSourceShort,
    checkLine: copy.checkLine,
    removed: { reasons: copy.removed.reasons, unknownReason: copy.removed.unknownReason },
    notVisible: copy.checkPlan.notVisible,
    footer: copy.footer,
  });
}

// Each JSON file, and the words it must hold.
export const SERVER_COPIES: { file: string; words: () => string; from: string }[] = [
  { file: SERVER_COPY_FILE, words: serverCopy, from: "copy.dataReadiness.server" },
  { file: DRAFTS_COPY_FILE, words: draftsCopy, from: "copy.draft.files" },
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
