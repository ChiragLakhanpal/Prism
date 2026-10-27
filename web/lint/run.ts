// The gate's copy and string lints (gates/steps.toml). Run it from anywhere:
//
//     node web/lint/run.ts
//
// It checks every string in the copy files against DESIGN.md section 7 and GLOSSARY.md, the
// definitions in GLOSSARY.md that Term shows, and every component in web/src for text that
// is not from a copy file, for a Term that names a word GLOSSARY.md does not define, for
// classes outside DESIGN.md's tokens, and for the classes the shell redesign retired (capitals
// outside a chart label, text-title and rounded-box; ticket 90). It prints one line per problem
// and exits with 1 when it finds any. Tests pass --copy, --component, --glossary, --registry and
// --design to point it at other files, and --root for the folder a component's path is read
// from (web/ by default); Term's words are always looked up in the repo's GLOSSARY.md.
//
// More files hold words people read. The source registry, config/sources.toml, holds each
// source's words on the Data readiness and Sources and licenses pages (labels, notes, fix
// sentences), and every one is checked like the copy. So are the package form schema's words,
// config/package_form.toml, each criterion chip's words (ticket 15), the lesson lists' labels
// (config/lessons.toml), the editions' names (config/editions.toml) and the roles' names
// (config/roles.toml), which the Lessons pages show (ticket 29), and the item registry's labels and
// phrases (config/criteria_items.toml), which section 5 of the package workspace shows (ticket 31).
// src/strata/tools/data_readiness_copy.json and src/strata/drafts/copy.json are the server's copies of
// copy.dataReadiness.server and of a draft's files' words, and the lint fails when either is out of date
// (web/lint/server-copy.ts writes them), as src/strata/estimates/steps.json is of the step-label registry,
// web/src/steps.ts (ticket 27).
import { readFileSync, readdirSync } from "node:fs";
import { join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { causalChecker, copyChecker, whatIfChecker } from "./copy.ts";
import { CAUSAL_SCOPES, CLASS_RULES_SKIP, FROZEN_CLASS_USES, UPPERCASE_ONLY_WITH, WHAT_IF_SAYS, WHAT_IF_SCOPES } from "./rules.ts";
import { copyStrings, lineOf, literalText, offTokenClasses, retiredClasses, scopedRanges, termLiterals, unusedKeeps } from "./source.ts";
import { staleServerCopies } from "./server-copy.ts";
import { definitions } from "../src/lib/definitions.ts";

const WEB = fileURLToPath(new URL("..", import.meta.url));
const REPO = resolve(WEB, "..");
// The step-label registry holds words people read too (ticket 27): each step's label and phrase, each stage and
// each family's name and abbreviation note, so it is checked like the copy file. So is the deck's copy file (ticket
// 47): its slides, speaker notes, and the figures' titles, text versions and captions.
const COPY_FILES = [join(WEB, "src/copy.ts"), join(WEB, "src/gallery/copy.ts"), join(WEB, "src/steps.ts"), join(WEB, "src/deck/copy.ts")];

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
    registry:
      given.registry ??
      (custom
        ? []
        : ["sources.toml", "package_form.toml", "lessons.toml", "editions.toml", "roles.toml", "criteria_items.toml"].map((name) => join(REPO, "config", name))),
    design: given.design?.[0] ?? join(REPO, "DESIGN.md"),
    // The folder a component's path is read from for the class rules' exemptions (ticket 90): web/, or a test's own.
    root: given.root?.[0] ?? WEB,
    custom,
  };
}

// The source registry's values that people read, each with its line: labels, nouns, notes, what a
// number counts, fix sentences, collections and data sources. Addresses and ids are left out. The package
// form schema's (ticket 15) are its groups' labels and names, each field's label and add_label, its
// options' labels and a count's units; STEP's own values and field names are left out, as they are words
// Strata copies word for word.
const REGISTRY_WORDS =
  /\b(label|phrase|add_label|unit|unit_one|noun|noun_one|covers|note|sentence|counts|counts_one|lack|name|short|publisher|origin|data_source)\s*=\s*"([^"]*)"/g;

function registryWords(text: string): { line: number; text: string }[] {
  return text.split("\n").flatMap((line, index) =>
    line.trimStart().startsWith("#") ? [] : [...line.matchAll(REGISTRY_WORDS)].map((match) => ({ line: index + 1, text: match[2] })),
  );
}

// GLOSSARY.md's definitions, which Term and DefinitionWindow show. Avoid lines are skipped.
function glossaryDefinitions(text: string): { line: number; text: string }[] {
  return text
    .split("\n")
    .map((line, index) => ({ line: index + 1, text: line }))
    .filter(({ text: line }) => line.trim() && !/^(#|\*\*|_Avoid_)/.test(line));
}

function main(): number {
  const { copy, components, glossary, registry, design, root, custom } = options(process.argv.slice(2));
  const check = copyChecker(design);
  const problems: string[] = [];
  const at = (file: string, line: number) => `${relative(process.cwd(), file) || file}:${line}`;
  const terms = definitions(readFileSync(join(REPO, "GLOSSARY.md"), "utf8"));

  const causal = causalChecker();
  const whatIf = whatIfChecker();
  for (const file of copy) {
    const source = readFileSync(file, "utf8");
    // The blocks that write about links between a contract and a paragraph also refuse causal words (ticket 22).
    const scoped = scopedRanges(source, file, CAUSAL_SCOPES);
    // The time estimate's blocks refuse "caused", "split" and "splitting", and its what-ifs say "went with" (ticket 26).
    const whatIfScoped = scopedRanges(source, file, WHAT_IF_SCOPES);
    const [says] = scopedRanges(source, file, [WHAT_IF_SAYS.scope]);
    let saysWords = false;
    for (const found of copyStrings(source, file)) {
      const inScope = scoped.some(([start, end]) => found.offset >= start && found.offset < end);
      const inWhatIf = whatIfScoped.some(([start, end]) => found.offset >= start && found.offset < end);
      if (says && found.offset >= says[0] && found.offset < says[1] && found.text.includes(WHAT_IF_SAYS.words)) saysWords = true;
      for (const problem of [...check(found.text), ...(inScope ? causal(found.text) : []), ...(inWhatIf ? whatIf(found.text) : [])]) {
        problems.push(`${at(file, lineOf(source, found.offset))}: "${found.text.trim()}" ${problem}`);
      }
    }
    if (says && !saysWords) {
      problems.push(`${at(file, lineOf(source, says[0]))}: the ${WHAT_IF_SAYS.scope} block never says "${WHAT_IF_SAYS.words}", as a what-if must (the 26 brief, section 7.4).`);
    }
  }
  for (const file of glossary) {
    for (const { line, text } of glossaryDefinitions(readFileSync(file, "utf8"))) {
      for (const problem of check(text)) problems.push(`${at(file, line)}: "${text.trim()}" ${problem}`);
    }
  }
  for (const file of registry) {
    for (const { line, text } of registryWords(readFileSync(file, "utf8"))) {
      for (const problem of check(text)) problems.push(`${at(file, line)}: "${text.trim()}" ${problem}`);
    }
  }
  if (!custom) {
    for (const stale of staleServerCopies()) {
      const from = stale.from.includes("/") ? stale.from : `${stale.from} in web/src/copy.ts`;
      problems.push(`${at(stale.file, 1)}: it is out of date with ${from}. Run node web/lint/server-copy.ts --write.`);
    }
  }
  for (const file of components) {
    const source = readFileSync(file, "utf8");
    for (const found of literalText(source, file)) {
      const held = found.from ? ` (held in the const ${found.from})` : "";
      problems.push(
        `${at(file, lineOf(source, found.offset))}: it ${found.where} "${found.text.trim()}"${held}, which is not from the copy file. ` +
          "Put the words in web/src/copy.ts and use them from there.",
      );
    }
    for (const found of termLiterals(source, file)) {
      if (found.text in terms) continue;
      problems.push(
        `${at(file, lineOf(source, found.offset))}: Term names "${found.text}", which GLOSSARY.md does not define. ` +
          "Use a term exactly as GLOSSARY.md writes it, or add the term there.",
      );
    }
    for (const found of offTokenClasses(source, file)) {
      problems.push(
        `${at(file, lineOf(source, found.offset))}: the class "${found.text}" is outside DESIGN.md's tokens. ` +
          "Use a color token, a type step or a space step from web/src/styles/app.css.",
      );
    }
    // Ticket 90: capitals only in a chart label, and no retired class, but in the deck's folder and the frozen files.
    const path = relative(root, file).split(sep).join("/");
    if (CLASS_RULES_SKIP.some((folder) => path.startsWith(folder))) continue;
    for (const found of retiredClasses(source, file, FROZEN_CLASS_USES[path])) {
      const where = `${at(file, lineOf(source, found.offset))}: the class "${found.text}"`;
      problems.push(
        found.where === UPPERCASE_ONLY_WITH
          ? `${where} sets capitals outside a chart label. Write the words in sentence case, or use "uppercase" ` +
              `with "${UPPERCASE_ONLY_WITH}" on a chart's lane or legend label (DESIGN.md section 3).`
          : `${where} is retired. Use "${found.where}" (DESIGN.md sections 3 and 4).`,
      );
    }
    // Ticket 91: a class the frozen list keeps for a file that no longer uses it comes off the list.
    for (const name of unusedKeeps(source, file, FROZEN_CLASS_USES[path])) {
      problems.push(
        `${at(file, 1)}: the class "${name}" is no longer used here, so take it off FROZEN_CLASS_USES in web/lint/rules.ts. ` +
          "Delete the list when it is empty.",
      );
    }
  }

  for (const problem of problems) console.log(problem);
  return problems.length ? 1 : 0;
}

process.exitCode = main();
