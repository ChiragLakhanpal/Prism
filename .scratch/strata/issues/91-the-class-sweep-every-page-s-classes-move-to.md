# 91: The class sweep: every page's classes move to their roles

**What to build:** After the functional tickets merge, move every use in the page files to its role so no page loses its hierarchy before its own ticket: `text-title` becomes `text-h2` (141 uses in 60 files), a `text-h3` that holds a finding becomes `text-lead`, `uppercase` leaves every class but `text-chart-label` (32 uses in 24 files), and a page's own `rounded-pill` on a control becomes `rounded-sm` while badges, markers and chips keep the pill. Empty the class lint's frozen list of files that used `uppercase` as each one is fixed, then delete the list. Paste the one sentence of block 1 marked for the class sweep. Leave the files the shell tickets rewrite (`TopNav.tsx`, `BoxBand.tsx`, `IntentBox.tsx`, `Frame.tsx`, `PageHeader.tsx`, `Breadcrumb.tsx`, `CollapsedSection.tsx`, `EvidenceDrawer.tsx`'s head) to those tickets, and leave `web/src/deck/` to its branch. No copy string, number, route or layout changes.

Read first: block 1 of `design-md.md`; the plan's section 5.3; `web/lint/rules.ts`; the class lint's report of today's uses; `web/tests/` specs that assert classes (grep for `text-title` and `uppercase`).

**Blocked by:** 90 (Tokens, fonts and lint for the redesigned shell); and every functional ticket merged, as the user's rule of October 25, 2026 asks

**Status:** ready
**Area:** design
**Phase:** P4
**Design review:** yes

- [ ] No file outside `web/src/deck/` uses `text-title`, the frozen uppercase list is gone, and the class lint passes with only the deck exemption.
- [ ] Every page's finding sentence that used `text-h3` uses `text-lead` (or the `finding` style where its page ticket has landed), and no section name outranks its finding on the package page, the plan check and Data readiness at 1440 and 390 px.
- [ ] Every Playwright spec passes unchanged in count, the captures differ only in type size, case and corners, and `git diff --stat` shows no file under `web/src/deck/` and none of the shell tickets' files.

**Gate seconds added:** about 0 (no new test; it updates class assertions in place).

## Comments

- October 27, 2026, design-lead: the second half of the tokens ticket, split after the second critic's review because it edits the same page files the functional tickets edit tonight. Specs to update: the ones that assert `text-title` or `uppercase`. Captures: every page's, once, after the sweep.

---
