// The copy lint over the proposal (ticket 46; the 46 brief, sections 14 and 23), a gate step that runs even when only
// Markdown is staged (gates/steps.toml, always = true). Run it from anywhere:
//
//     node web/lint/proposal.ts                    the proposal's source, the built proposal if there is one, and the
//                                                  words its registries put into it
//     node web/lint/proposal.ts docs/proposal.md   one file, or several
//
// It reads each Markdown file as a reader sees it: link text without addresses, table cells, titles of number links,
// and HTML cells without their tags. Code, addresses, HTML attributes and the build's {placeholders} are left out.
// Every piece goes through the app's own copy lint (copyChecker in web/lint/copy.ts): DESIGN.md section 7, rule 19's
// words, "PP" as a whole word, em dashes, exclamation marks, curly quotes, "the Bank" outside a fixed term, the region
// codes and GLOSSARY.md's Avoid terms. DESIGN.md section 8's sentences are fixed terms, so they pass word for word.
//
// Two places quote the assessment's own words: the rubric map's criteria and Annex 4's first column, written as cells
// with data-quote="assessment". There, GLOSSARY.md's Avoid terms ("Structured data", "re-bidding", "precedent") are
// allowed; every other rule still holds.
//
// It prints one line per problem, with the file and line, and exits with 1 when it finds any.
import { existsSync, readFileSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { copyChecker } from "./copy.ts";

const REPO = resolve(fileURLToPath(new URL("../..", import.meta.url)));
const DOCUMENTS = ["docs/proposal/source.md", "docs/proposal.md"];
// The registries whose words the build puts into the proposal, and the keys that hold those words.
const REGISTRIES: [string, string[]][] = [
  ["config/rubric.toml", ["name", "summary", "says", "label"]],
  ["config/designed_not_built.toml", ["name", "exists_now"]],
  ["config/change_drills.toml", ["change"]],
  ["docs/proposal/results.toml", ["name", "noun", "labels"]],
  ["docs/proposal/settings.toml", ["name", "enforces"]],
];

export type Piece = { line: number; text: string; quote: boolean };

const QUOTE_CELL = /<(td|th)\b[^>]*\bdata-quote="assessment"[^>]*>(.*?)<\/\1>/g;

// The words of one Markdown line, as a reader sees them, in pieces: the assessment's quoted cells apart.
export function readable(line: string, number: number): Piece[] {
  const pieces: Piece[] = [];
  let text = line.replace(QUOTE_CELL, (_, _tag, inner: string) => {
    pieces.push({ line: number, text: inner.replace(/<[^>]+>/g, " "), quote: true });
    return " ";
  });
  // A number link's title is read on hover, so its words are copy too.
  for (const title of text.matchAll(/\]\([^)\s]*\s+"([^"]*)"\)/g)) pieces.push({ line: number, text: title[1], quote: false });
  text = text
    .replace(/<!--.*?-->/g, " ")
    .replace(/`[^`]*`/g, " ")
    .replace(/!\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/\[([^\]]*)\]\([^)]*\)/g, "$1")
    .replace(/<[^>]+>/g, " ")
    .replace(/\{[a-z#¶]+:[^{}]*\}|\{#[a-z0-9-]+\}|\{[a-z-]+(:[a-z-]+)?\}/g, " ")
    .replace(/https?:\/\/\S+/g, " ");
  pieces.push({ line: number, text, quote: false });
  return pieces;
}

export function markdownPieces(source: string): Piece[] {
  const pieces: Piece[] = [];
  let fenced = false;
  source.split("\n").forEach((line, index) => {
    if (line.trimStart().startsWith("```")) {
      fenced = !fenced;
      return;
    }
    if (!fenced) pieces.push(...readable(line, index + 1));
  });
  return pieces;
}

export function registryPieces(source: string, keys: string[]): Piece[] {
  const pattern = new RegExp(`(?:^|[\\s{,])(${keys.join("|")})\\s*=\\s*"([^"]*)"`, "g");
  return source.split("\n").flatMap((line, index) =>
    line.trimStart().startsWith("#") ? [] : [...line.matchAll(pattern)].map((found) => ({ line: index + 1, text: found[2].replace(/\{[a-z]+:[^{}]*\}/g, " "), quote: false })),
  );
}

export function proposalProblems(pieces: Piece[], designPath = join(REPO, "DESIGN.md")): { line: number; text: string; problem: string }[] {
  const check = copyChecker(designPath);
  const quoted = copyChecker(designPath, { avoid: false });
  return pieces.flatMap((piece) => (piece.quote ? quoted : check)(piece.text).map((problem) => ({ line: piece.line, text: piece.text.trim(), problem })));
}

function main(argv: string[]): number {
  const given = argv.map((file) => resolve(file));
  const documents = given.length ? given : DOCUMENTS.map((file) => join(REPO, file)).filter((file) => existsSync(file));
  const found: string[] = [];
  const report = (file: string, problems: ReturnType<typeof proposalProblems>) => {
    for (const { line, text, problem } of problems) {
      const shown = text.length > 100 ? `${text.slice(0, 97)}...` : text;
      found.push(`${relative(process.cwd(), file) || file}:${line}: "${shown}" ${problem}`);
    }
  };
  for (const file of documents) report(file, proposalProblems(markdownPieces(readFileSync(file, "utf8"))));
  if (!given.length) {
    for (const [name, keys] of REGISTRIES) {
      const file = join(REPO, name);
      if (existsSync(file)) report(file, proposalProblems(registryPieces(readFileSync(file, "utf8"), keys)));
    }
  }
  for (const line of found) console.log(line);
  return found.length ? 1 : 0;
}

if (fileURLToPath(import.meta.url) === resolve(process.argv[1])) process.exitCode = main(process.argv.slice(2));
