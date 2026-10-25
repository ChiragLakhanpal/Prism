// The gate's copy lint and string lint (criteria 8 and 9 of ticket 02). Each test runs the
// same command the gate runs, web/lint/run.ts, on files it writes, and checks that the
// command fails on the mistake and passes once the mistake is gone.
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { footerSentence } from "./design-md";
import { placements, readRegistry, type SourceRegistry } from "./registries";

const RUN = fileURLToPath(new URL("../lint/run.ts", import.meta.url));

function lint(files: { copy?: string; component?: string; registry?: string }) {
  const dir = mkdtempSync(join(tmpdir(), "strata-lint-"));
  const args = [RUN];
  if (files.copy !== undefined) {
    writeFileSync(join(dir, "copy.ts"), files.copy);
    args.push("--copy", join(dir, "copy.ts"));
  }
  if (files.component !== undefined) {
    writeFileSync(join(dir, "Thing.tsx"), files.component);
    args.push("--component", join(dir, "Thing.tsx"));
  }
  if (files.registry !== undefined) {
    writeFileSync(join(dir, "sources.toml"), files.registry);
    args.push("--registry", join(dir, "sources.toml"));
  }
  const done = spawnSync("node", args, { encoding: "utf8" });
  return { code: done.status, output: done.stdout + done.stderr };
}

const copyWith = (text: string) => `export const copy = {\n  line: ${JSON.stringify(text)},\n};\n`;

const MISTAKES: [string, string, string, RegExp][] = [
  ["an em dash", "Packages took 7 months — longer than planned.", "Packages took 7 months, longer than planned.", /em dash/],
  ["an exclamation mark", "Your draft is ready!", "Your draft is ready.", /exclamation mark/],
  ["the word flag", "I flag two activities.", "I found two signals.", /"flag".*rule 19/],
  ["the word approve", "Approve this draft.", "Mark this draft as checked.", /"approve".*rule 19/],
  ["the word slippage", "The slippage was 40 days.", "The delay was 40 days.", /"slippage".*rule 19/],
  ["the Bank", "the Bank reviewed the plan.", "The World Bank reviewed the plan.", /"the Bank".*rule 8/],
  ["PP for Procurement Plan", "Open the PP for this project.", "Open the Procurement Plan for this project.", /"PP".*rule 19/],
];

for (const [name, wrong, right, reason] of MISTAKES) {
  test(`the gate fails when a copy-file string has ${name}, and passes once it is removed`, () => {
    const failed = lint({ copy: copyWith(wrong) });
    expect(failed.code, failed.output).toBe(1);
    expect(failed.output).toMatch(reason);
    expect(failed.output).toContain("copy.ts:2");

    const passed = lint({ copy: copyWith(right) });
    expect(passed.output).toBe("");
    expect(passed.code).toBe(0);
  });
}

test("the copy lint checks the words the source registry puts on the Data readiness page, and not its addresses", () => {
  const entry = (note: string) =>
    `[sources.cpia]\nendpoint = "https://api.worldbank.org/v2/clear"\n# I flag nothing here.\n\n` +
    `[[sources.cpia.declared]]\ncolumn = "coverage"\nnote = "${note}"\n`;
  const failed = lint({ registry: entry("IDA countries only, as flagged by IDA") });
  expect(failed.code, failed.output).toBe(1);
  expect(failed.output).toMatch(/sources\.toml:7: "IDA countries only, as flagged by IDA" uses "flagged"/);

  const passed = lint({ registry: entry("IDA countries only") });
  expect(passed.output).toBe("");
  expect(passed.code).toBe(0);
});

// Ticket 22: a link between a contract and a paragraph is "appeared together", never a cause, so the blocks that
// write about links refuse causal words, "because" included, and only those blocks.
test("the copy lint refuses causal wording on the contract trail, the Connections tab and Why this source, and only there", () => {
  const scoped = (text: string) => `export const copy = {\n  why: {\n    link: ${JSON.stringify(text)},\n  },\n  other: {\n    line: ${JSON.stringify(text)},\n  },\n} as const;\n`;
  for (const [wrong, word] of [
    ["The contract was late because the paragraph says so.", "because"],
    ["This lesson informed the contract.", "informed"],
    ["The delay led to rebidding.", "led to"],
  ]) {
    const failed = lint({ copy: scoped(wrong) });
    expect(failed.code, failed.output).toBe(1);
    expect(failed.output).toContain(`copy.ts:3: "${wrong}" uses "${word}", which says a cause.`);
    // The same words outside the scoped blocks are not checked for cause.
    expect(failed.output).not.toContain("copy.ts:6:");
  }
  const passed = lint({ copy: scoped("This paragraph appeared together with the contract.") });
  expect(passed.output).toBe("");
});

test("every block the causal-wording rule names is in the copy file", async () => {
  const { scopedRanges } = await import("../lint/source.ts");
  const { CAUSAL_SCOPES } = await import("../lint/rules.ts");
  const file = fileURLToPath(new URL("../src/copy.ts", import.meta.url));
  expect(scopedRanges(readFileSync(file, "utf8"), file, CAUSAL_SCOPES)).toHaveLength(CAUSAL_SCOPES.length);
});

test("the server's copies of the Data readiness sentences and the draft files' words say what the copy file says", async () => {
  const { serverCopyIsCurrent, staleServerCopies } = await import("../lint/server-copy.ts");
  expect(serverCopyIsCurrent(), "run node web/lint/server-copy.ts --write").toBe(true);
  expect(staleServerCopies(), "run node web/lint/server-copy.ts --write").toEqual([]);
});

test("every kind of question in config/tools.toml has its words in the copy file, and its tool a coverage-line noun", async () => {
  // Review r3 P6: adding a kind is one entry in config/tools.toml, and a kind with no words here would
  // leave its numbers saying nothing about what they count.
  const { copy } = await import("../src/copy.ts");
  const tools = readFileSync(fileURLToPath(new URL("../../config/tools.toml", import.meta.url)), "utf8");
  const kinds = [...tools.matchAll(/^\[tools\.(\w+)\.readiness\]\s*\nkind = "(\w+)"/gm)].map(([, tool, kind]) => ({ tool, kind }));
  expect(kinds.length).toBeGreaterThan(0);
  // Review r4 P5: a block written in another order fails here instead of being skipped.
  expect(kinds.length, "every [tools.*.readiness] block starts with its kind line").toBe(
    [...tools.matchAll(/^\[tools\.\w+\.readiness\]/gm)].length,
  );
  const words = copy.dataReadiness;
  // A count that spells STEP out has a form for one as well.
  expect(Object.keys(words.kinds.countsSpelledOne)).toEqual(Object.keys(words.kinds.countsSpelled));
  for (const { tool, kind } of kinds) {
    expect(words.kinds.names[kind], `copy.dataReadiness.kinds.names.${kind}`).toBeTruthy();
    expect(words.kinds.counts[kind], `copy.dataReadiness.kinds.counts.${kind}`).toBeTruthy();
    expect(words.kinds.countsOne[kind], `copy.dataReadiness.kinds.countsOne.${kind}`).toBeTruthy();
    expect((words.server.fromNouns as Record<string, string>)[tool], `copy.dataReadiness.server.fromNouns.${tool}`).toBeTruthy();
  }
});

test("every measure a number on /data can open that fills no column has its own window words in the copy file", async () => {
  // Design r5 B1 and review r7 B1: a check's number, and then a kind's Ready for number, opened
  // Coverage's window. Every measure the page can show comes from one of three places: a column, a
  // check or a fix in config/sources.toml, or a kind's Ready for in config/tools.toml. Each one that
  // no column of its row shows has words of its own in copy.dataReadiness.measureWindows, so a new
  // one can never fall back to a column's name and definition, and each names its table.
  const { copy } = await import("../src/copy.ts");
  const { placed, conflicts } = placements();
  expect(conflicts, "a measure's window is chosen by its name, so each is placed one way").toEqual([]);
  const measureOf = (key: string) => key.slice(key.indexOf("/") + 1);
  const needed = [...placed].filter(([, placement]) => placement.column === null).map(([key]) => measureOf(key));
  // Each place adds at least one, so a reader that silently found none can't pass.
  expect(needed).toContain("latest_activities_with_confirmed_first_listing_read");
  expect(needed).toContain("gap_years_projects_in_local_currency");
  expect(needed).toContain("passages_embedded");
  const words = copy.dataReadiness.measureWindows;
  const missing = needed.filter((measure) => !words[measure]?.title || !words[measure]?.definition);
  expect(missing, "add each to copy.dataReadiness.measureWindows").toEqual([]);
  expect([...placed].filter(([, placement]) => !placement.table).map(([key]) => key), "every window names its table").toEqual([]);
  // Review r6 P3: the words are keyed by measure name alone, and a column's measure names repeat
  // across sources, so words for one would retitle every cell of that column that counts it.
  const columnMeasures = new Set([...placed].filter(([, placement]) => placement.column !== null).map(([key]) => measureOf(key)));
  expect(columnMeasures).toContain("linked_project");
  expect(
    Object.keys(words).filter((measure) => columnMeasures.has(measure)),
    "a column's number opens the column's window",
  ).toEqual([]);
  // Review r7 P3: fix 1's window names the awards dataset by the registry's label and years, so the
  // two can't drift apart.
  const awards = readRegistry<SourceRegistry>("sources.toml").sources.awards.readiness?.[0];
  expect(words.projects_with_contracts_lacking_step_reference.definition).toContain(`${awards?.label} ${awards?.covers}`);
});

test("the copy lint finds a banned word in a template's text and in any form of the word", () => {
  const failed = lint({ copy: "export const copy = {\n  done: (n: number) => `I flagged ${n} rows.`,\n};\n" });
  expect(failed.code).toBe(1);
  expect(failed.output).toMatch(/"flagged"/);
});

test("the copy lint allows DESIGN.md section 8's footer sentence word for word, and a fixed term", async () => {
  const footer = await footerSentence();
  expect(lint({ copy: copyWith(footer) }).code).toBe(0);
  expect(lint({ copy: copyWith("You still need the Bank's no-objection.") }).code).toBe(0);
  // Changed by one word, the sentence is no longer the fixed one, and "endorsed" is caught.
  expect(lint({ copy: copyWith(footer.replace("Strata is", "This is")) }).code).toBe(1);
});

test("the copy lint allows the draft bar's fixed sentence and the Word file's origin sentence word for word", () => {
  // DESIGN.md section 5's Draft bar, after the review notes' lead sentence (ticket 35), and section 8's
  // last sentence of the Word file's origin paragraph.
  const draftBar =
    "A working draft of your review notes on the borrower's Procurement Plan. Exporting sends nothing and is not a World Bank review, clearance or no-objection.";
  const word = "Strata is an independent demo built on World Bank open data. These notes are not a World Bank review, clearance or no-objection.";
  for (const text of [draftBar, word]) {
    const passed = lint({ copy: copyWith(text) });
    expect(passed.output).toBe("");
    expect(passed.code).toBe(0);
  }
  // Outside those sentences, "clearance" is still caught, and so is a changed fixed sentence.
  expect(lint({ copy: copyWith("I gave this draft its clearance.") }).code).toBe(1);
  expect(lint({ copy: copyWith("Exporting sends it and is a World Bank review, clearance or no-objection.") }).code).toBe(1);
});

test("the copy lint finds the Bank in capitals and with a no-break space, but not a bank guarantee", () => {
  for (const text of ["THE BANK reviewed the plan.", "the\u00a0Bank reviewed the plan."]) {
    const failed = lint({ copy: copyWith(text) });
    expect(failed.code, text).toBe(1);
    expect(failed.output, text).toMatch(/rule 8/);
  }
  expect(lint({ copy: copyWith("The bank guarantee was 2 percent of the bid.") }).code).toBe(0);
});

test("the copy lint finds GLOSSARY.md's Avoid terms, such as chunk", () => {
  const failed = lint({ copy: copyWith("I read 40 chunks of the report.") });
  expect(failed.code).toBe(1);
  expect(failed.output).toMatch(/"chunks".*GLOSSARY\.md/);
});

test("the gate fails when a component renders a string that is not from the copy file", () => {
  const cases = [
    `export const A = () => <p>Nothing here yet.</p>;`,
    `export const A = () => <p>{"Nothing here yet."}</p>;`,
    `export const A = ({ on }: { on: boolean }) => <p>{on ? "Open" : "Closed"}</p>;`,
    `export const A = () => <button aria-label="Close the source" />;`,
    `export const A = () => <img alt="World Bank logo" src="/logo.svg" />;`,
    `export const A = () => <Card title={\`Plan \${1}\`} />;`,
    // Any prop that is not on rules.ts's NON_COPY_PROPS list is read as copy, so the props of
    // Strata's own components are covered without listing them.
    `export const A = () => <EmptyState title={copy.x} body="Plans appear once they load." />;`,
    `export const A = () => <CoverageLine part={3} whole={4} noun="matching packages" href="#data" />;`,
    // Strings inside an object or an array given to a prop are judged by their own key.
    `export const A = () => <Num value={3} check={{ tooltip: "Matches paragraph 54." }} />;`,
    `export const A = () => <Answer state={{ status: "empty", message: "I found nothing." }} />;`,
    `export const A = () => <Steps steps={[{ key: "read", running: "Reading your question." }]} />;`,
    `export const A = () => <CitationMarker n={1} source="Implementation Completion and Results Report" href="#s1" />;`,
    // A string kept in a const and rendered by name.
    `const words = "Nothing here yet."; export const A = () => <p>{words}</p>;`,
    `const words = "Close the source"; export const A = () => <button aria-label={words} />;`,
    // A key read from a local lookup object, and a default prop value.
    `const words = { empty: "Nothing here yet." }; export const A = () => <p>{words.empty}</p>;`,
    `const words = { empty: "Nothing here yet." }; export const A = () => <p>{words["empty"]}</p>;`,
    `export function A({ body = "Nothing here yet." }) { return <p>{body}</p>; }`,
    // A STEP method and a person's name are read by someone, so these props are copy too.
    `export const A = () => <Row method="Request for Bids" />;`,
    `export const A = () => <Person name="Ana Example" />;`,
    // Words joined with +, as children and as props: each piece with letters is copy, as it
    // is in the template form.
    `export const A = ({ n }: { n: number }) => <p>{n + " packages"}</p>;`,
    `export const A = ({ state }: { state: string }) => <p>{"Opened " + state}</p>;`,
    `export const A = () => <p>{"Something " + "went wrong."}</p>;`,
    `export const A = ({ name }: { name: string }) => <button aria-label={"Close the " + name} />;`,
    `export const A = ({ name }: { name: string }) => <Alert title={name + " alert"} />;`,
    // A let or a var is read like a const, by the value it starts with.
    `let words = "Nothing here yet."; export const A = () => <p>{words}</p>;`,
    `var words = "Nothing here yet."; export const A = () => <p>{words}</p>;`,
    // Props passed by spreading an object, written in place or kept in a const.
    `export const A = () => <Card {...{ title: "Nothing here yet." }} />;`,
    `const props = { title: "Nothing here yet." }; export const A = () => <Card {...props} />;`,
    // Words a component writes into the page itself, outside JSX.
    `export function A() { document.title = "Packages, Strata"; return null; }`,
    `export function A({ el }: { el: HTMLElement }) { el.textContent = "Nothing here yet."; return null; }`,
  ];
  for (const component of cases) {
    const failed = lint({ component });
    expect(failed.code, component).toBe(1);
    expect(failed.output, component).toMatch(/Thing\.tsx:1: .*not from the copy file/);
  }
});

test("a component that takes every string from the copy file passes the string lint", () => {
  const component = [
    `import { copy } from "./copy";`,
    `const WIDE = "(min-width: 64rem)";`,
    `const LOOK = { box: "bg-info-bg" };`,
    `export const A = ({ on }: { on: boolean }) => (`,
    `  <section className="flex gap-4 p-6" aria-labelledby="t" data-state={on ? "open" : "closed"}>`,
    `    <h2 id="t">{copy.title}</h2> · <span aria-hidden>/</span>`,
    `    <img alt="" src="/x.svg" />{format(3, "short")}`,
    `    <Answer state={{ status: "empty", message: copy.empty }} aria-live="polite" />`,
    `    <ol style={{ minHeight: "calc(6 * 1.45em)" }}><li key="read">{copy.read}</li></ol>`,
    `    <Num part={1} whole={2} show="count" style="table" />{matchMedia(WIDE).matches && copy.wide}`,
    `    <div className={LOOK.box} /><div className={LOOK["box"]} />`,
    // + that builds an address, a class, a key or a sum, or text with no letters, is not copy.
    `    <a href={"#" + copy.id} className={"flex " + LOOK.box} key={"row-" + 1} data-n={"n" + 2}>{1 + 2}</a>`,
    `    <span>{"(" + 3 + ")"}</span><div {...{ className: "p-4", role: "note" }} />`,
    `  </section>`,
    `);`,
    `export function B({ el }: { el: HTMLElement }) { el.className = "p-4"; el.textContent = copy.title; document.title = copy.title; }`,
  ].join("\n");
  const passed = lint({ component });
  expect(passed.output).toBe("");
  expect(passed.code).toBe(0);
});

test("the gate fails when a Term names a word GLOSSARY.md does not define", () => {
  const failed = lint({ component: `export const A = () => <Term term="Comparables" />;` });
  expect(failed.code).toBe(1);
  expect(failed.output).toMatch(/Thing\.tsx:1: .*"Comparables".*GLOSSARY\.md/);
  expect(lint({ component: `export const A = () => <Term term="Comparable" />;` }).code).toBe(0);
});

test("the class lint refuses spacing off DESIGN.md's scale and colors outside the tokens", () => {
  for (const bad of ["p-5", "gap-7", "gap-y-5", "mt-[13px]", "bg-[#ff0000]", "text-[15px]", "md:px-9"]) {
    const failed = lint({ component: `export const A = () => <div className="flex ${bad}" />;` });
    expect(failed.code, bad).toBe(1);
    expect(failed.output).toContain(`"${bad}"`);
  }
  expect(
    lint({ component: `export const A = () => <div className="p-0.5 px-3 gap-6 gap-x-3 gap-y-1 -mt-2 md:p-16 m-auto" />;` }).code,
  ).toBe(0);
});
