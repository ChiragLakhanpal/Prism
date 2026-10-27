# 104: Data readiness by the page area, with its pages in the sidebar

**What to build:** Paste block 12b of `design-md.md`. Data readiness and Sources and licenses become sidebar items under Data and the sub-tab row goes. Convert every window breakpoint in `web/src/pages/data/DataReadiness.tsx` and `web/src/components/ReadinessTable.tsx` to the page area's container queries. The headline becomes the page's finding in the `finding` style; "What you can ask" and "Sources" are panels; the last three sections are closed rows with their one-sentence summaries. Every number keeps its window. Start from the design lead's brief, which draws Data readiness at 1440 and 390 px.

Read first: the design lead's brief for this ticket; the plan's section 8.4 (Data); block 12b of `design-md.md`; `web/src/pages/data/DataPage.tsx`, `DataReadiness.tsx`, `SourcesAndLicenses.tsx`; `web/src/components/ReadinessTable.tsx`, `MeasureNum.tsx`; `web/tests/data.spec.ts`, `shelf.spec.ts`, `sources.spec.ts`.

**Blocked by:** 99 (Projects: sub-pages in the sidebar, a shorter project head, and Summary's finding first); 97 (How Strata works leaves Data: each refusal gives its reason, and one window lists them all)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The sidebar under Data lists Data readiness and Sources and licenses only, and Data's sub-tab row is gone (`data.spec.ts`).
- [ ] No window breakpoint remains in `DataReadiness.tsx` or `ReadinessTable.tsx`, and a test opens Data readiness beside the drawer at 1024 px and finds its tables laid out as at a 550 px page area.
- [ ] The headline is the page's finding in the `finding` style; "What you can ask" and "Sources" are panels, the last three sections are closed rows that open in place with focus kept on their button, and Data readiness at 390 px is at least 30 percent shorter than the 11,205 px of `current/data-390.png`.

**Gate seconds added:** about +0.3 (the beside-the-drawer test).

## Comments

- October 27, 2026, design-lead: the second half of round 3's Data ticket, split after the second critic's review. Settles in full ticket 59's Data pages laid out by the window (line 40), and ticket 59's numbers that carry an underline but open nothing on Data readiness (lines 36 and 39) if the number tooltip ticket has not taken them. Specs to update: data.spec.ts, shelf.spec.ts, sources.spec.ts, capture.spec.ts. Captures: `readiness` at three widths. Second wave: it waits for the Projects ticket because both fill the sidebar's sub-item slot.

---
