// GLOSSARY.md's definitions, by term, for Term and DefinitionWindow. GLOSSARY.md stays the one
// home of each definition (CLAUDE.md rule 4), and the bundler reads it at build time. The
// gate's copy lint checks these definitions like the copy file.
import glossaryText from "../../GLOSSARY.md?raw";
import { definitions } from "./lib/definitions";

export { definitions };
export const terms = definitions(glossaryText);
