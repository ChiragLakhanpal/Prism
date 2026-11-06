// What every figure says about itself, by its key, for both talks: Prism's own talk's figures (web/src/deck/copy.ts,
// figureCopy) and the deep research talk's (web/src/deck/research/copy.ts, researchFigureCopy). A figure's title is
// its SVG's <title>, and its steps are its text version, one line per press. Each figure key is in one copy file
// only, so the two never disagree.
import { figureCopy } from "../deck/copy";
import { researchFigureCopy } from "../deck/research/copy";

export const FIGURE_WORDS: Record<keyof typeof figureCopy | keyof typeof researchFigureCopy, { title: string; steps: readonly string[] }> = {
  ...figureCopy,
  ...researchFigureCopy,
};

export type FigureWordsId = keyof typeof FIGURE_WORDS;
