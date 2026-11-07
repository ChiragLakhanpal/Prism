// Prism's own talk at /present (ticket 47; the second draft's brief): five topics between the bookends, with DESIGN.md
// section 8's sentence along every slide's foot. Its slides are web/src/deck/slides.tsx, its words web/src/deck/copy.ts.
import { deckCopy } from "../copy";
import { buildSlides } from "../slides";
import { PLACES, TOPICS, type Talk } from "../talk";

export const strataTalk: Talk = {
  key: "strata",
  ...PLACES.strata,
  order: TOPICS.strata,
  topics: () => deckCopy.topics,
  build: buildSlides,
  footer: "every",
};
