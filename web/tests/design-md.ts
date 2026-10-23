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
  for (const part of css.split(";")) {
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

export type TypeStep = { token: string; size: number; lineHeight: string; weight: number; tracking: string | null };

// Section 3's type scale: one row per token, with the size in px and the line height as written.
export async function typeScale(): Promise<TypeStep[]> {
  const text = await section(3);
  const rows = text.split("\n").filter((line) => /^\| `[a-z0-9]+` \| \d+ \/ /.test(line));
  return rows.map((line) => {
    const cells = line.split("|").map((cell) => cell.trim());
    const token = cells[1].replaceAll("`", "");
    const [size, lineHeight] = cells[2].split("/").map((part) => part.trim());
    const weight = Number(/\d{3}/.exec(cells[3])![0]);
    const tracking = /([+-]?[\d.]+(?:em|px)) ?tracking|\+?(-?[\d.]+em)/.exec(cells[3]);
    return {
      token,
      size: Number(size),
      lineHeight,
      weight,
      tracking: tracking ? (tracking[1] ?? tracking[2]).replace(/^\+/, "") : null,
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

// Section 8's footer sentence, word for word.
export async function footerSentence(): Promise<string> {
  const text = await section(8);
  const row = text.split("\n").find((line) => line.startsWith("| Footer, every screen and slide |"));
  if (!row) throw new Error("DESIGN.md section 8 has no footer row.");
  return /"(.+)"/.exec(row)![1];
}
