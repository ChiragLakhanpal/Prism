# 165: The research talk's hairline figures: ground, two-slabs and rungs

**What to build:** Three hairline figures for the research talk's navy slides (ticket 162), as the brief `.notes/deck3/brief.md` in the main checkout (`./.notes/deck3/brief.md`) specifies them in section 7: `ground` (the title slide and the close), `two-slabs` (the opener of How we got here) and `rungs` (the opener of The decisions). The skill is `.claude/skills/hairline-create`; the kernel is `web/src/figures/hairline/kernel.js`, vendored unchanged and never edited; each figure is `web/src/figures/hairline/<name>.js` in the skill's format, one object and one idea, with a `tour` of three or four stops, passing the skill's `build.mjs` and `validate.mjs`, and `look.mjs` where a browser is available (Playwright is in `web/node_modules`). Words go only into `means` and the read-out, never the drawing. The deck sets the navy palette through the kernel's custom properties (plate `#002244`, edge `#dae3eb`, mid `#8a9db1`, lo `#2c4560`, hi `#169af3`); each figure must also read in the skill's default light palette. Read `web/src/figures/hairline/filter.js` and `plan-rows.js` first, and the first deck's brief, section 6 (`.claude/worktrees/deck-second-draft/.notes/deck2/brief.md`), for how its figures were specified and built. The skill's concept step asks a person to choose; there is nobody to ask, so take the concept the brief gives and say in your report what you decided within it.

Write only your own three files. Do not edit the kernel, the registry, the deck or the tests: ticket 162 registers the names (the deck loads every file beside the kernel through `import.meta.glob`, so a new file is found by its name once the deck's slide names it). Render each figure at rest and at each tour stop in Chromium (the skill's `look.mjs`, or a Playwright page that mounts the kernel and the figure as `web/src/figures/Figure.tsx` does) and look at the PNGs before you report. Run the skill's validator on each, not the full gate.

Essentials only, no review rounds. Commit with plain-English messages and no trailers. Report within ninety minutes: branch and worktree, each figure's name, its `means`, its tour stops and read-out, the PNGs you looked at, and anything you decided differently from the brief.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** app
**Phase:** P5
**Design review:** no

- [ ] `web/src/figures/hairline/ground.js`, `two-slabs.js` and `rungs.js` exist in the skill's format, each passing `build.mjs` and `validate.mjs`, with a tour of three or four stops and a `means` sentence of at most 140 characters that passes the copy lint's word rules (DESIGN.md section 7).
- [ ] Each figure answers the pointer as the brief says (the lifted tile and its pin, the slab that slides into a stack, the rung that lights), reads in the navy palette and in the light one, and was looked at as PNGs at rest and at each stop.

## Comments

- November 6, 2026, orchestrator: opened at 13:45 PST, in parallel with tickets 162, 163 and 164.
