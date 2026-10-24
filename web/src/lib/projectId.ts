// The ProjectId rule's parts that need no browser (ticket 21; the 21 brief, section 9): what a P-code
// looks like in text, and the places the Playwright sweep (web/tests/sweep.spec.ts) leaves out.

// A P-code where it stands alone in text: P and six digits.
export const PROJECT_ID = /\bP\d{6}\b/g;

// The places the sweep leaves out, in one list: text a person types (form fields), the one box's scope
// chip, whose only action is to remove it, and visually hidden text that repeats a link already on
// screen. The page's <title> is outside the body, so the sweep never reads it. Briefs 37 and 41 add theirs
// here.
export const PROJECT_ID_EXEMPT = ["input", "textarea", "[data-scope-chip]", ".sr-only", "[data-project-id-exempt]"];
