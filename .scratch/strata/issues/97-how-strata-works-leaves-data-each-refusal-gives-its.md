# 97: How Strata works leaves Data: each refusal gives its reason, and one window lists them all

**What to build:** Paste block 12a of `design-md.md`. How Strata works stops being a page, as the user asked (the deck at /present shows its figures). Remove `web/src/pages/data/HowStrataWorks.tsx`'s page and its sub-tab; move `WhatIDontDo` to `web/src/components/` as the body of a non-modal window, "What I turn down". Each refusal in the answer panel now says its own reason in place, as a third sentence after what I don't do and what I can do instead, from `copy.refusals[key].why`; the caption under it becomes a flush ghost, "See everything I turn down" (`answer.refusalAll`, replacing `refusalNote` and `refusalLink`), which opens that window; `CheckCriteria.tsx`'s refusal note does the same. The address `/data/how-strata-works` opens Data readiness through a replace. Leave `web/src/figures/` alone: the deck branch shares it. Data readiness's layout is the next Data ticket's.

Read first: the plan's section 8.4 (the table of where How Strata works' content goes, and the routes and tests that change); block 12a of `design-md.md`; `web/src/routes.ts` lines 61 to 64 and 133; `web/src/RoutePage.tsx` line 85; `web/src/pages/data/DataPage.tsx`, `HowStrataWorks.tsx`; `web/src/components/AnswerPanel.tsx` lines 46 and 471 to 490, `CheckCriteria.tsx` lines 18 and 205 to 215; `web/src/copy.ts` lines 15 to 60 (`REFUSALS`), 918 to 920 and 5601 to 5624; `web/src/gallery/pages.tsx` lines 87 and 1506 and `web/src/gallery/copy.ts` lines 279 and 1078 to 1079; `web/tests/data.spec.ts`, `checks.spec.ts`, `answer.spec.ts`, `sweep.spec.ts`.

**Blocked by:** 91 (The class sweep: every page's classes move to their roles)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] `/data/how-strata-works` lands on Data readiness with the address replaced, Data's sub-tabs list Data readiness and Sources and licenses only, and no route, gallery page or capture links to the old address (`data.spec.ts` line 72's list and line 81's title updated, lines 780 to 847 removed; `sweep.spec.ts` lines 112 to 113 removed).
- [ ] A refusal in the answer panel shows its lead, what I can do instead and its reason, each from the copy file's refusal key, and "See everything I turn down" opens a window that lists every refusal's lead and reason, with Escape returning focus to the button (`checks.spec.ts` lines 216 to 227 and `answer.spec.ts` lines 317 to 318 rewritten; the gallery's `what-i-dont-do` sample moves to the answer panel's page).
- [ ] `git diff --stat` shows no file under `web/src/figures/` or `web/src/deck/`.

**Gate seconds added:** about -0.8 (+0.2 for the window test; -1.0 for the How Strata works test and its route-table row, the two sweep rows and two captures).

## Comments

- October 27, 2026, design-lead: the first half of round 3's Data ticket, split after the second critic's review. The user's addition of October 26, 2026 (21:40 PDT) settles round 2's open item on How Strata works. It runs beside the shell: it touches AnswerPanel.tsx only in the refusal note (lines 471 to 490), while the frame ticket moves the panel's wrapper; whichever merges second rebases. Captures: `web/capture/shots.ts` line 1746's `refusal--how-strata-works` becomes `refusal--why`, and line 1973's `data("how", ...)` goes.
- The deck branch's follow-up for this ticket, lines on `deck/second-draft` at 494a176b: `web/src/deck/copy.ts` lines 1, 6 and 503 name How Strata works in comments; `web/src/figures/order.ts` line 17's `PAGE_ORDER` is then used by nothing in the app, so the deck keeps or removes it.

---
