// The deck's talks, by key: the address names one (view.ts), and the engine (Deck.tsx) shows it. A new talk is one
// file here, its slides and its copy file.
import type { Talk, TalkKey } from "../talk";
import { researchTalk } from "./research";
import { strataTalk } from "./strata";

export const TALKS: Record<TalkKey, Talk> = { strata: strataTalk, research: researchTalk };
