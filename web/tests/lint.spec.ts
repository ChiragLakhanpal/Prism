// The gate's copy lint and string lint (criteria 8 and 9 of ticket 02). Each test runs the
// same command the gate runs, web/lint/run.ts, on files it writes, and checks that the
// command fails on the mistake and passes once the mistake is gone.
import { spawnSync } from "node:child_process";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { footerSentence } from "./design-md";

const RUN = fileURLToPath(new URL("../lint/run.ts", import.meta.url));

function lint(files: { copy?: string; component?: string }) {
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
  ];
  for (const component of cases) {
    const failed = lint({ component });
    expect(failed.code, component).toBe(1);
    expect(failed.output).toMatch(/Thing\.tsx:1: .*not from the copy file/);
  }
});

test("a component that takes every string from the copy file passes the string lint", () => {
  const component = [
    `import { copy } from "./copy";`,
    `export const A = ({ on }: { on: boolean }) => (`,
    `  <section className="flex gap-4 p-6" aria-labelledby="t" data-state={on ? "open" : "closed"}>`,
    `    <h2 id="t">{copy.title}</h2> · <span aria-hidden>/</span>`,
    `    <img alt="" src="/x.svg" />{format(3, "short")}`,
    `  </section>`,
    `);`,
  ].join("\n");
  const passed = lint({ component });
  expect(passed.output).toBe("");
  expect(passed.code).toBe(0);
});

test("the class lint refuses spacing off DESIGN.md's scale and colours outside the tokens", () => {
  for (const bad of ["p-5", "gap-7", "gap-y-5", "mt-[13px]", "bg-[#ff0000]", "text-[15px]", "md:px-9"]) {
    const failed = lint({ component: `export const A = () => <div className="flex ${bad}" />;` });
    expect(failed.code, bad).toBe(1);
    expect(failed.output).toContain(`"${bad}"`);
  }
  expect(
    lint({ component: `export const A = () => <div className="p-0.5 px-3 gap-6 gap-x-3 gap-y-1 -mt-2 md:p-16 m-auto" />;` }).code,
  ).toBe(0);
});
