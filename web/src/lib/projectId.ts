// The ProjectId rule's parts that need no browser (ticket 21; the 21 brief, section 9): what a P-code
// looks like in text, and the places the Playwright sweep (web/tests/sweep.spec.ts) leaves out.

// A P-code where it stands alone in text: P and six digits.
export const PROJECT_ID = /\bP\d{6}\b/g;

// The places the sweep leaves out, in one list: text a person types (form fields), the one box's scope
// chip, whose only action is to remove it, visually hidden text that repeats a link already on screen, and
// the current crumb on a project's own tabs, whose P-code sits just above the h1's link to the same page
// (the 21 design review, round 2, F21). The page's <title> is outside the body, so the sweep never reads
// it. Brief 37 adds the meta line of a Following row, whose heading link already opens that project's page, so a
// second link would double the row's tab stops (WCAG technique H2). Brief 41 adds its own here.
export const PROJECT_ID_EXEMPT = ["input", "textarea", "[data-scope-chip]", ".sr-only", "[data-project-id-exempt]", "[data-project-crumb]",
  "[data-project-row-meta]"];
