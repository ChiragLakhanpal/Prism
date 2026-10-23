// GLOSSARY.md's definitions, by term, for Term and DefinitionWindow. GLOSSARY.md stays the one
// home of each definition (CLAUDE.md rule 4), and the bundler reads it at build time. Its
// Avoid lines are not shown. The gate's copy lint checks these definitions like the copy file.
import glossaryText from "../../GLOSSARY.md?raw";

export function definitions(text: string): Record<string, string> {
  const found: Record<string, string> = {};
  for (const match of text.matchAll(/^\*\*(.+?)\*\*:\n(.+)$/gm)) found[match[1]] = match[2].trim();
  return found;
}

export const terms = definitions(glossaryText);
