# 127: The ask box has presence: on the grid, 56 px tall, named, edged and shadowed, with an Enter button

**What to build:** On October 29, 2026 the owner said the ask box "looks lost amongst the content, doesn't stand out". The design lead measured it on the local copy (`docs/design/notes-2026-10-29/ask-bar-and-width-proposal.md`, the proposal to read first): 640 by 40 px, centred on the page column, its white fill 1.07:1 against the page, a 1 px edge and a faint shadow the only separation, sharing no edge with anything, moving 281 px when the drawer opens, and on a package workspace its centre sits 277 px right of the work's centre. Build the lead's Option A, in its order: (1) put the box on the grid: on a workspace page it spans the work's columns (1 to 7 at 1440 and 1280 px), on a wide page columns 3 to 10, so its edges meet the content's and it centres over the draft bar (this closes ticket 113's alignment item); (2) its new look: 56 px tall, the navy bar's height; a visible name "Ask Strata" at its left that pairs with the answer heading; a 1 px `primary` edge and a new navy-tinted token `shadow-float` added to DESIGN.md's tokens; an outlined Enter button named for what Enter does ("Look up" or "Ask") that replaces the "/" hint once the person types; the resting and open states, the drawer's open state, the error state and the thinking state each drawn in the gallery. At 1024 px and below nothing moves (the lead found those widths right). The owner's three calls, taken as recommended: the `primary` edge, the box may centre differently on wide and workspace pages, and the tracker question belongs to ticket 130. Prove it with the shell and box specs at 1440, 1280, 1024 and 390 px (the edges on the grid, the height, the name, the button's text before and after typing, the shadow token), axe clean, and the recorded answer streams unchanged. Keep the gate under 150 seconds; touch nothing under web/src/deck/.

Read first: `docs/design/notes-2026-10-29/ask-bar-and-width-proposal.md` (Option A's sketches and files), `web/src/components/AskBox*` and `web/src/lib/sticky.ts` (ticket 113's floating box), `DESIGN.md` (the box's row and the tokens), `docs/design/redesign-2026-10/plan.md` section 5.7, ticket 113's done comment.

**Blocked by:** the Mobbin pass (the design lead looks at real ask bars and command bars on Mobbin and refines Option A; the owner asked on October 29 that design work wait for it)

**Status:** ready
**Area:** web
**Phase:** P4
**Design review:** no

- [ ] The box's edges sit on the grid: columns 1 to 7 on a workspace page and 3 to 10 on a wide page at 1440 and 1280 px, centred over the draft bar, unchanged at 1024 px and below (a spec measures the edges).
- [ ] The box is 56 px tall with the visible name "Ask Strata", a 1 px `primary` edge, the `shadow-float` token (in DESIGN.md), and an Enter button named for its action that replaces the "/" hint once the person types; each state is in the gallery; axe is clean at the four widths.
- [ ] The recorded answer streams and the box's lookups behave as before (the existing specs pass), and the ticket's own specs run under five seconds of gate time.

## Comments

- October 29, 2026, orchestrator: parked at 14:05 PDT at the owner's word ("parking the design related stuff so that the lead can use mobbin's mcp for inspo and the build"); the lead's proposal moved to docs/design/notes-2026-10-29/ so a builder in a worktree can read it.

- October 29, 2026, orchestrator: opened at 13:30 PDT from the design lead's proposal of the same day; the owner's Mobbin pick may refine the look later, as a follow-up.
