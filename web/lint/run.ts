// The gate's copy and string lints (gates/steps.toml). Run it from anywhere:
//
//     node web/lint/run.ts
//
// It checks every string in the copy files against DESIGN.md section 7 and GLOSSARY.md, the
// definitions in GLOSSARY.md that Term shows, and every component in web/src for text that
// is not from a copy file or classes outside DESIGN.md's tokens. It prints one line per
// problem and exits with 1 when it finds any. Tests pass --copy, --component, --glossary and
// --design to point it at other files.
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { copyChecker } from "./copy.ts";
import { copyStrings, lineOf, literalText, offTokenClasses } from "./source.ts";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const REPO = resolve(WEB, "..");
const COPY_FILES = [join(WEB, "src/copy.ts"), join(WEB, "src/gallery/copy.ts")];

function sourceFiles(dir: string): string[] {
  return readdirSync(dir, { withFileTypes: true }).flatMap((entry) => {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.tsx?$/.test(entry.name) && !entry.name.endsWith(".d.ts") ? [path] : [];
  });
}

function options(argv: string[]) {
  const given: Record<string, string[]> = {};
  for (let i = 0; i < argv.length; i += 2) (given[argv[i].replace(/^--/, "")] ??= []).push(resolve(argv[i + 1]));
  const custom = Object.keys(given).length > 0;
  return {
    copy: given.copy ?? (custom ? [] : COPY_FILES),
    components: given.component ?? (custom ? [] : sourceFiles(join(WEB, "src")).filter((file) => !COPY_FILES.includes(file))),
    glossary: given.glossary ?? (custom ? [] : [join(REPO, "GLOSSARY.md")]),
    design: given.design?.[0] ?? join(REPO, "DESIGN.md"),
  };
}

// GLOSSARY.md's definitions, which Term and DefinitionWindow show. Avoid lines are skipped.
function glossaryDefinitions(text: string): { line: number; text: string }[] {
  return text
    .split("\n")
    .map((line, index) => ({ line: index + 1, text: line }))
    .filter(({ text: line }) => line.trim() && !/^(#|\*\*|_Avoid_)/.test(line));
}

function main(): number {
  const { copy, components, glossary, design } = options(process.argv.slice(2));
  const check = copyChecker(design);
  const problems: string[] = [];
  const at = (file: string, line: number) => `${relative(process.cwd(), file) || file}:${line}`;

  for (const file of copy) {
    const source = readFileSync(file, "utf8");
    for (const found of copyStrings(source, file)) {
      for (const problem of check(found.text)) {
        problems.push(`${at(file, lineOf(source, found.offset))}: "${found.text.trim()}" ${problem}`);
      }
    }
  }
  for (const file of glossary) {
    for (const { line, text } of glossaryDefinitions(readFileSync(file, "utf8"))) {
      for (const problem of check(text)) problems.push(`${at(file, line)}: "${text.trim()}" ${problem}`);
    }
  }
  for (const file of components) {
    const source = readFileSync(file, "utf8");
    for (const found of literalText(source, file)) {
      problems.push(
        `${at(file, lineOf(source, found.offset))}: it ${found.where} "${found.text}", which is not from the copy file. ` +
          "Put the words in web/src/copy.ts and use them from there.",
      );
    }
    for (const found of offTokenClasses(source, file)) {
      problems.push(
        `${at(file, lineOf(source, found.offset))}: the class "${found.text}" is outside DESIGN.md's tokens. ` +
          "Use a colour token, a type step or a space step from web/src/styles/app.css.",
      );
    }
  }

  for (const problem of problems) console.log(problem);
  return problems.length ? 1 : 0;
}

process.exitCode = main();
