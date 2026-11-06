# 164: The research talk's figures, second four: record-gap, research-run, evidence-ladder and post-funnel

**What to build:** Four diagram-design figures for the research talk at /present/research (ticket 162), as the brief `.notes/deck3/brief.md` in the main checkout (`./.notes/deck3/brief.md`) specifies them: section 5 (what every figure builder must do, which repeats and extends the first deck's brief, section 4, at `.claude/worktrees/deck-second-draft/.notes/deck2/brief.md`) and section 6, F5 `record-gap`, F6 `research-run`, F7 `evidence-ladder` (the half slot, `viewBox="0 0 420 352"`) and F8 `post-funnel`. Each is drawn as HTML in `web/figures/<key>.html` with the skill at `.claude/skills/diagram-design` under the `strata-wb` profile (the marker `.diagram-design` is in the repo root), exported to `web/src/figures/<key>.svg` with `export_svg.py --system-fonts`, checked with `self_check.py --offline`, marked with the step markup so the deck shows it one press at a time, and rendered at 2x whole and at each step so you have looked at it before you report. Copy the head, CSS and markers of `web/figures/checks.html`, `web/figures/pipeline.html` or, for the half slot, `web/figures/ladder.html` exactly; the palette and fonts are the ones `tests/test_deck_figures.py` allows; labels in sentence case with no tracking; no counts and no number words in the SVG, its title or its description (dates, years and sequence numbers such as "ISR 19" and "October 8" are allowed).

Write only your own eight files: the four sources and the four exports. Do not edit the registry, the order file, the copy, the tests or anything else: ticket 162 adds your keys there from the brief's step texts, so your steps must match the brief's, in order, with the same count. Run `tests/test_deck_figures.py`'s checks on your own files by hand (the export equality, the self check, the viewBox, the palette, the fonts, the sentence-case rule, the step budget), not the full gate; your branch's gate is unchanged from `build/strata`'s and the merger runs it.

Essentials only, no review rounds. Commit with plain-English messages and no trailers. Report within ninety minutes: branch and worktree, each figure's key and step count, the PNGs you looked at, and anything you could not do or decided differently.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** app
**Phase:** P5
**Design review:** no

- [ ] `web/figures/record-gap.html`, `research-run.html`, `evidence-ladder.html` and `post-funnel.html` and their exports exist, each export equal to its source's export with system fonts, each passing the skill's self check offline, each in its slot's viewBox (the ladder in the half slot) and the strata-wb palette and fonts, with sentence-case labels and no counts.
- [ ] Each figure's steps are contiguous from 1, match the brief's step texts in order and count (4, 6, 5, 6), and keep the motion budget (at most 8 steps, 12 items, 2 items a step).
- [ ] Rendered at 2x whole and at each step, each figure reads well: no overlaps, no label outside its box, the focal item as the brief names it.

## Comments

- November 6, 2026, orchestrator: opened at 13:45 PST, in parallel with tickets 162, 163 and 165.
