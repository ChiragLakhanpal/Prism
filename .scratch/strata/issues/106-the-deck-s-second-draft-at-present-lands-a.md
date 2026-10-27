# 106: The deck's second draft at /present lands: a topic tracker, a press per point, navy openers and redrawn figures

**What to build:** Nothing new to write: the second draft of the deck exists on branch `deck/second-draft` at 494a176b (49 files, 5,683 lines added and 1,925 removed, built by a separate session on October 26, 2026 from the user's request, in the worktree `.claude/worktrees/deck-second-draft`; its brief is `.notes/deck2/brief.md` there). It rebuilds `/present` after fairshare's deck in the World Bank's design language: a header with the World Bank logo (the light file on light slides, the white file on navy ones) and a five-topic tracker, DESIGN.md section 8's footer sentence, one press per point or figure step, navy `#002244` openers for the title, the five topics and the close, hairline openers and redrawn diagram-design figures (`web/src/figures/*`, `web/figures/*.html`), demo slides that open the app's own routes in a new tab, the notes window and the reading view kept, `src/strata/proposal/deck.py` and `web/public/deck/data.json` with the demo links from `config/examples.toml`, the plan date, the example sentence and the smoke question, tests in `web/tests/deck.spec.ts`, `tests/test_deck_data.py` and `tests/test_deck_figures.py`, one allow entry in `docs/proposal/number_check.toml`, and six additive DESIGN.md lines in sections 4, 8, 9 and 11. This ticket is the branch's way into `build/strata`: the user looks at it first (the local app procedure in `.notes/local-run.md` serves the worktree), then a reviewer and the gate, then the merge, as every ticket. Two things to settle at the merge, agreed between the deck session and the orchestrator (the scratchpad's `redesign/deck-notes.md`, copied below): the navy slides are the user's call, and whichever of this branch and the redesign's tokens ticket merges second adds the clause to DESIGN.md's navy rule ("used for the top bar and the deck's navy slides, which carry the white logo (section 4, Deck frame)") if the user keeps them; and after the tokens ticket lands, the rebase applies its rules to the second draft (`text-title` to `text-h2` at `web/src/deck/Deck.tsx` 925 and 969 and `web/src/deck/ramp.ts` 44; the gap label at `web/src/deck/AwardChart.tsx` 86 to the 12 px chart label; the lint's uppercase rule), reruns `deck.spec.ts` and the three captures that still have a slide, and retires `deck--range-chart` and the eyebrow checks. If the deck branch rebases before ticket 91 (the class sweep) merges, it drops its own uses of `text-title` and `rounded-box` and the deck exemption itself, and the two aliases wait for 91. Every number on a slide stays bound to the snapshot and passes the number check; the copy follows section 7 and unslop.

Read first: the branch's commit 494a176b (`git show --stat`), `.notes/deck2/brief.md` in the worktree, `DESIGN.md` sections 4, 8, 9 and 11, `docs/proposal/number_check.toml`, `web/tests/deck.spec.ts`, the redesign's tokens ticket.

**Blocked by:** None (the user's look comes first; the merge order against the tokens ticket is settled above)

**Status:** ready-for-human
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] The user has looked at the second draft served from the worktree and said yes to the navy openers or asked for the light ones; the answer is recorded here.
- [ ] On the branch rebased onto `build/strata`, the gate passes, `web/tests/deck.spec.ts`, `tests/test_deck_data.py` and `tests/test_deck_figures.py` pass, and the number check passes with the one allow entry explained in its comment.
- [ ] Every slide's number is bound to the snapshot (no number typed into a slide), every claim on a slide names its source, and the copy passes DESIGN.md section 7 and `docs/agents/unslop.md` (the reviewer reads every slide).
- [ ] The demo slides open the app's routes from `config/examples.toml` in a new tab, and the reading view and the notes window work (the design critic looks at the deck at 1440 and 390 px).
- [ ] DESIGN.md's navy rule and section 4's Deck frame row agree after the merge, whichever of this ticket and the tokens ticket merged second.

## Comments

- October 27, 2026, orchestrator: opened after wave 4q, so the deck session's branch has a review and a merge path; the branch waits for the user's look first. The deck session's notes on the navy slides and the tokens sweep (October 26, 23:32 PDT) are in the ticket text.
- October 27, 2026, orchestrator (02:17 PDT): two wording fixes from the deck session (the logo file per slide background; the alias order against ticket 91).
