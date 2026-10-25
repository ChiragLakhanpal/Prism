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
  // DESIGN.md section 5, Draft bar, and section 7, rule 19: the bar's fixed sentence, which every kind's
  // lead sentence comes before ("clearance" and "no-objection" are otherwise rule 19's).
  "Exporting sends nothing and is not a World Bank review, clearance or no-objection.",
  // DESIGN.md section 8, Exported files: the last sentence of the Word file's origin paragraph.
  "These notes are not a World Bank review, clearance or no-objection.",
  // The mission brief's Word origin paragraph (ticket 37; DESIGN.md section 8, Exported files).
  "This brief is not a World Bank review, clearance or no-objection.",
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
  ["stress shelf", "the hardest documents I read"],
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
  // Skeleton's corner radius class, such as rounded-pill.
  "radius",
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
  // The keyboard a phone shows for a field, such as "decimal".
  "inputMode",
  "scope",
  "live",
  "show",
  "widths",
  "htmlFor",
  // Table's breakpoint for cards: "md" or "lg".
  "cardsBelow",
  // The plan prompt's "Show the past range" weight, "primary" or "secondary" (ticket 15, brief 36).
  "showRangeVariant",
  // A readiness column's label in a card: "hidden" leaves it to screen readers (ticket 18).
  "cardLabel",
  // EightColumns' breakpoint: "lg" or "xl".
  "breakpoint",
  // Section 5 of the package workspace (ticket 31): a part's and a section's key for tests and focus, and the
  // package's API path.
  "partKey",
  "sectionKey",
  "base",
  // Keys of copy.checkLine.notCheckedClauses, such as "comparables".
  "notChecked",
  // The Data readiness page (ticket 16): which tooltip a measure's number gets ("ratio", "count" or
  // "day"), which column's definition its window shows ("linked"), and which rows a readiness
  // table's skeleton stands for ("kinds" or "sources"). What a clicked number is ("missing" or
  // "days") goes under role, above.
  "tooltipKind",
  "windowColumn",
  "skeletonRows",
  // The one box's scope chip: "project" or "package", which picks the placeholder.
  "scopeKind",
  // SVG settings in the range chart: a text's alignment ("start", "end"), a paint ("none") and a
  // path's drawing commands, such as the chevron after a dot past the axis ("M 10 4 L 13 7").
  "textAnchor",
  "fill",
  "d",
  // SVG settings in a project's timeline (ticket 23): a line's cap ("round") and a label's vertical
  // alignment ("central").
  "strokeLinecap",
  "dominantBaseline",
  // The disagreement card's keep action in a design gallery sample (ticket 23): its phase ("open", "saving",
  // "failed" or "kept") and when the choice was made, an ISO timestamp.
  "phase",
  "madeAt",
  // NoteSentences' type size: "small" in a draft, "body" in a lesson review's summary (ticket 29).
  "textSize",
  // The feedback row (ticket 32): the report kind a sample has chosen ("wrong_passage" or "not_useful"), why a
  // withdrawal failed ("failed" or "decided"), the server's reason code for no row ("preview"), and the loop's
  // mode ("pilot" or "scale"). Each is a code the copy file turns into words.
  "chosen",
  "withdrawFailed",
  "why_not",
  "mode",
  // The grade bar's two grades once a query is locked (ticket 32): grade codes such as "partly".
  "mine",
  "theirs",
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
