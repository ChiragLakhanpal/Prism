// The deep research talk at /present/research (ticket 162; .notes/deck3/brief.md; cut to sixteen slides by ticket 166):
// how two apps became one conversation, then the feature that came of it and the reasoning behind it, in ten content
// slides between the bookends, with a navy opener for each topic after the first. The tracker in the header is its
// agenda, so it has no agenda slide, and its topics carry names only. No slide shows DESIGN.md section 8's sentence (the user, November 6, 2026: no
// sources or disclaimers on the slides); the reading view keeps the app's footer. Its slides are
// web/src/deck/research/slides.tsx, its words web/src/deck/research/copy.ts.
import { researchCopy } from "../research/copy";
import { buildResearchSlides } from "../research/slides";
import { PLACES, TOPICS, type Talk } from "../talk";

export const researchTalk: Talk = {
  key: "research",
  ...PLACES.research,
  order: TOPICS.research,
  topics: () => researchCopy.topics,
  build: buildResearchSlides,
  footer: "none",
};
