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
  // DESIGN.md section 5, Draft bar ("clearance" and "no-objection" are otherwise rule 19's).
  "A working draft for the borrower's PPSD. Exporting sends nothing and is not a World Bank review, clearance or no-objection.",
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

// JSX attributes and component props whose strings are never shown to anyone: addresses, keys
// and settings. The string lint reads a string given to any other prop as copy, so a new
// component's props are checked without listing them here. Inside an object or an array
// given to a prop, each string is judged by its own key: in state={{ status: "empty",
// message: "..." }}, status is a setting and message is copy. List a prop here only when a
// component uses it, with the reason if it is not plain: name, method and download are left
// off, because a person's name, a STEP method and a file name are all read by someone.
export const NON_COPY_PROPS = new Set([
  "className",
  "href",
  "src",
  "id",
  "key",
  "type",
  "variant",
  "kind",
  "state",
  "status",
  "role",
  "lang",
  "target",
  "rel",
  "side",
  "align",
  "width",
  "term",
  "rowHeader",
  "autoComplete",
  "scope",
  "live",
  "show",
  "widths",
  "htmlFor",
  // Table's breakpoint for cards: "md" or "lg".
  "cardsBelow",
  // EightColumns' breakpoint: "lg" or "xl".
  "breakpoint",
  // Keys of copy.checkLine.notCheckedClauses, such as "comparables".
  "notChecked",
  // The Data readiness page (ticket 16): which tooltip a measure's number gets ("ratio", "count" or
  // "day"), which column's definition its window shows ("linked"), and which rows a readiness
  // table's skeleton stands for ("kinds" or "sources"). What a clicked number is ("missing" or
  // "days") goes under role, above.
  "tooltipKind",
  "windowColumn",
  "skeletonRows",
]);

// A prop or key that ends in one of these holds an address, an id or a class, such as pdfHref,
// runId or iconClassName.
export const NON_COPY_SUFFIXES = ["Href", "Id", "Key", "ClassName"];

// Props whose whole value is CSS, never text.
export const STYLE_PROPS = new Set(["style"]);

// DOM properties that put words on the page or into a screen reader when a component sets
// them outside JSX, such as document.title = copy.title. The string lint reads a string
// written to one of these as copy.
export const DOM_TEXT_PROPERTIES = new Set([
  "title",
  "textContent",
  "innerText",
  "innerHTML",
  "placeholder",
  "alt",
  "ariaLabel",
  "ariaDescription",
  "ariaRoleDescription",
  "ariaValueText",
  "ariaPlaceholder",
]);

// ARIA attributes hold settings ("true", "page", "polite") and ids, except these, which hold
// words a screen reader says. The string lint reads these as copy.
export const ARIA_TEXT_PROPS = new Set([
  "aria-label",
  "aria-description",
  "aria-roledescription",
  "aria-valuetext",
  "aria-placeholder",
  "aria-braillelabel",
  "aria-brailleroledescription",
]);
