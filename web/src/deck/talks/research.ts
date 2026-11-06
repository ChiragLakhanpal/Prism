// The deep research talk at /present/research (ticket 162; .notes/deck3/brief.md): how two apps became one
// conversation, then the feature that came of it and the reasoning behind it, in five topics between the bookends.
// DESIGN.md section 8's sentence shows once, on the title slide (the user, November 6, 2026: "just saying it once is
// enough, they know"). Its slides are web/src/deck/research/slides.tsx, its words web/src/deck/research/copy.ts.
import { buildResearchSlides, researchTopics } from "../research/slides";
import { PLACES, TOPICS, type Talk } from "../talk";

export const researchTalk: Talk = {
  key: "research",
  ...PLACES.research,
  order: TOPICS.research,
  topics: researchTopics,
  build: buildResearchSlides,
  footerOnEverySlide: false,
};
