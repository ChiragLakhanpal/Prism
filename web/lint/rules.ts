// What the gate's lints allow and refuse. Change a rule here, in one place (CLAUDE.md rule 9).
// DESIGN.md section 7 rule 19's banned words are not listed here: web/lint/copy.ts reads them
// from DESIGN.md itself, so the file people edit is the one the gate enforces.

// Spacing classes (p-*, m-*, gap-*, space-*) may use only these steps of --spacing (4 px),
// which are DESIGN.md section 4's space scale: 2, 4, 8, 12, 16, 24, 32, 40, 48 and 64 px.
export const SPACE_STEPS = [0.5, 1, 2, 3, 4, 6, 8, 10, 12, 16];

// Sentences and terms the copy may use word for word, even though a rule would catch a word
// inside them. Each one names where it is fixed.
export const FIXED_TERMS = [
  // DESIGN.md section 8, the footer on every screen ("endorsed" is otherwise rule 19's).
  "Strata is an independent demo built on World Bank open data. It is not a World Bank product, and the World Bank has not reviewed or endorsed it.",
  // DESIGN.md section 7, rule 8: the one fixed term where "the Bank" stays.
  "the Bank's no-objection",
];

// DESIGN.md section 7, rule 8: never the regional codes; spell the region out.
export const REGION_CODES = ["AFR", "EAP", "ECA", "LAC", "MNA", "SAR"];

// GLOSSARY.md's Avoid terms that are never right in user-facing copy, with the word to use.
// Avoid terms that are ordinary words in other senses (fact, statement, context, alert,
// benchmark, average, market, estimate, readiness, tier, slice, learning) are left out,
// because only a person can tell which sense a sentence means. So is PIU, which GLOSSARY.md
// avoids only in copy shared across countries and uses in its own definition.
export const GLOSSARY_AVOID: [string, string][] = [
  ["chunk", "passage"],
  ["snippet", "passage"],
  ["evidence layer", "stratum"],
  ["source rank", "evidence tier"],
  ["conflict", "disagreement"],
  ["contradiction", "disagreement"],
  ["discrepancy", "disagreement"],
  ["data quality score", "data readiness"],
  ["structured data", "What, the stratum of records"],
  ["semi-structured data", "How, the stratum of operational documents"],
  ["unstructured data", "Why, the stratum of narrative documents"],
  ["purchase requisition", "package"],
  ["purchase order", "package"],
  ["client", "implementing agency"],
  ["time to award", "procurement cycle time"],
  ["re-bid", "rebidding"],
  ["re-tender", "rebidding"],
  ["similar package", "comparable"],
  ["precedent", "comparable"],
  ["prediction", "time estimate"],
  ["forecast", "time estimate"],
  ["insight", "lesson"],
  ["draft lesson", "proposed lesson"],
  ["candidate", "proposed lesson"],
  ["risk score", "signal"],
  ["ICB", "Request for Bids, open international"],
  ["NCB", "Request for Bids, open national"],
  ["Shopping", "Request for Quotations"],
  ["Direct Contracting", "Direct Selection"],
];

// JSX attributes and component props that a person reads or hears. The string lint refuses
// a literal in any of them; the words belong in the copy file.
export const USER_FACING_PROPS = new Set([
  "aria-label",
  "aria-description",
  "aria-roledescription",
  "aria-valuetext",
  "aria-placeholder",
  "alt",
  "title",
  "placeholder",
  "label",
  "heading",
  "description",
  "caption",
  "message",
  "text",
  "hint",
  "eyebrow",
  "summary",
]);
