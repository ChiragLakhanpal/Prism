// Reads GLOSSARY.md's definitions, by term: each "**Term**:" line and the line under it. Its
// Avoid lines are left out. web/src/glossary.ts gives these to Term, and the gate's lint
// (web/lint/run.ts) checks that every term="..." a component writes is one of them.
export function definitions(text: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const match of text.matchAll(/^\*\*(.+?)\*\*:\n(.+)$/gm)) found[match[1]] = match[2].trim();
  return found;
}
