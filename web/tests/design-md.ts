// Reads DESIGN.md, the design system, so tests compare the app with the file people edit.
// Each function returns one part of it: the theme block, the type scale, the space scale.
import { readFile } from "node:fs/promises";

const DESIGN = new URL("../../DESIGN.md", import.meta.url);

async function section(number: number): Promise<string> {
  const text = await readFile(DESIGN, "utf8");
  const start = text.indexOf(`\n## ${number}. `);
  if (start === -1) throw new Error(`DESIGN.md has no section ${number}.`);
  const end = text.indexOf("\n## ", start + 1);
  return text.slice(start, end === -1 ? undefined : end);
}

// Section 2's @theme block, as a map from each custom property to its value.
export async function themeBlock(): Promise<Map<string, string>> {
  const text = await section(2);
  const block = /```css\n@theme \{\n([\s\S]*?)\n\}\n```/.exec(text);
  if (!block) throw new Error("DESIGN.md section 2 has no @theme block.");
  return declarations(block[1]);
}

export function declarations(css: string): Map<string, string> {
  const tokens = new Map<string, string>();
  // A comment, such as the one that marks an alias deprecated, is not part of any value.
  for (const part of css.replace(/\/\*[\s\S]*?\*\//g, "").split(";")) {
    const colon = part.indexOf(":");
    if (colon === -1) continue;
    const name = part.slice(0, colon).trim();
    if (name.startsWith("--")) tokens.set(name, normalize(part.slice(colon + 1)));
  }
  return tokens;
}

export function normalize(value: string): string {
  return value.trim().replace(/\s+/g, " ").replace(/\s*,\s*/g, ", ");
}

// below: the size and line height a step takes below 48rem of window width, such as the finding's 24 / 32.
export type TypeStep = {
  token: string;
  size: number;
  lineHeight: string;
  weight: number;
  tracking: string | null;
  below: { size: number; lineHeight: string } | null;
};

// Section 3's type scale: one row per token, with the size in px and the line height as written. A step
// that steps down on a phone, such as "28 / 36; 24 / 32 below 48rem of window width", gives its first pair
// as its size and line height and the second as below.
export async function typeScale(): Promise<TypeStep[]> {
  const text = await section(3);
  const rows = text.split("\n").filter((line) => /^\| `[a-z0-9-]+` \| \d+ \/ /.test(line));
  return rows.map((line) => {
    const cells = line.split("|").map((cell) => cell.trim());
    const token = cells[1].replaceAll("`", "");
    const [first, second] = cells[2].split(";");
    const [size, lineHeight] = first.split("/").map((part) => part.trim());
    const smaller = second && /(\d+) \/ (\d+)/.exec(second);
    const weight = Number(/\d{3}/.exec(cells[3])![0]);
    const tracking = /([+-]?[\d.]+(?:em|px)) ?tracking|\+?(-?[\d.]+em)/.exec(cells[3]);
    return {
      token,
      size: Number(size),
      lineHeight,
      weight,
      tracking: tracking ? (tracking[1] ?? tracking[2]).replace(/^\+/, "") : null,
      below: smaller ? { size: Number(smaller[1]), lineHeight: smaller[2] } : null,
    };
  });
}

// A row of section 4's table, such as "Space" or "Breakpoints", as written.
export async function shapeRow(name: string): Promise<string> {
  const text = await section(4);
  const row = text.split("\n").find((line) => line.startsWith(`| ${name} |`));
  if (!row) throw new Error(`DESIGN.md section 4 has no ${name} row.`);
  return row.split("|")[2].trim();
}

// Section 3's metrics for the "Open Sans Fallback" face, such as { "size-adjust": "105.22%" }.
export async function fallbackMetrics(): Promise<Record<string, string>> {
  const text = await section(3);
  const sentence = /`(size-adjust: [^`]+)`/.exec(text);
  if (!sentence) throw new Error("DESIGN.md section 3 does not give the fallback face's metrics.");
  return Object.fromEntries(sentence[1].split(";").map((part) => part.split(":").map((side) => side.trim())));
}

// Section 5's Draft bar sentence for review notes, word for word (ticket 35).
export async function draftBarSentence(): Promise<string> {
  const text = await section(5);
  const row = text.split("\n").find((line) => line.startsWith("| Draft bar |"));
  const said = row && /For review notes it reads: "([^"]+)"/.exec(row);
  if (!said) throw new Error("DESIGN.md section 5's Draft bar row does not give the review notes' sentence.");
  return said[1];
}

// Section 8's footer sentence, word for word.
export async function footerSentence(): Promise<string> {
  const text = await section(8);
  const row = text.split("\n").find((line) => line.startsWith("| Footer, every screen, slide and dashboard page |"));
  if (!row) throw new Error("DESIGN.md section 8 has no footer row.");
  return /"(.+)"/.exec(row)![1];
}
