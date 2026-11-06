# 153: Pre-seeded deep research briefs for a handful of projects, researched by hand on November 5, 2026

**What to build:** The user's instruction of November 5, 2026 at 19:55 PST: the demo shows pre-seeded briefs for a handful of projects, with no live lookups. P156634 is seeded (ticket 147). This ticket seeds four more, each researched by hand from real public sources read by Prism's named client, never invented, so every marker in a brief opens a real page: P161305 (Horn of Africa Gateway Development Project, Kenya, active, the Isiolo to Mandera road), P145559 (Coastal Region Water Security and Climate Resilience Project, Kenya, active, Mwache dam), P167814 (Second Kenya Informal Settlements Improvement Project, active), and P130164 (Rajasthan Road Sector Modernization Project, India, closed in 2018, the deck's showcase, where the brief says what the ground record holds since closing).

For each project, one research agent delivers, on its own branch from `build/strata`: `ops/research/sample_<pid>.toml` in the shape of `sample_P156634.toml` (the outside items the brief cites: news articles with their outlet, date, URL and the recorded page; complaints from the Inspection Panel register; posts if any; the Sentinel-2 grids for two or three sites with coordinates from the project record; related project records), the recordings under `data/fixture/recorded/research/<source>/` in ticket 147's naming so the seed reads them offline, and a note in the toml's header saying which outlets refused the named client (their items keep the headline, as for Eastleigh Voice). At least ten outside items per active project with dates in 2025 or 2026 where they exist, and the ones that matter most to a procurement specialist: works finishing or stalling, contractors paid or not, awards and terminations, disputes with residents, audits, the state of service. The seed run locally (`uv run python ops/research/seed.py --project <pid> --state-file <scratch>/state.duckdb`, once ticket 152's engine flag lands, or with the fixture database before) must load the items, and the agent reports the counts per source. No code changes beyond the toml and the recordings; the gate must still pass (the recordings are read by tests only through the seed).

**Blocked by:** None for the research; the workspace seed waits for 152

**Status:** done
**Area:** knowledge
**Phase:** P5
**Design review:** no

- [ ] Four sample files and their recordings exist, each item a real page read on November 5 or 6, 2026, with its URL, date and outlet (the agents' reports list them).
- [ ] The seed loads each project's items locally with the counts the report gives (tests or a recorded run).
- [ ] On the workspace, each project's seed run exists and its brief is written and stored, so the Deep research tab opens on it at once (ticket 151's agent records it).

## Comments

- November 5, 2026, orchestrator: opened at 20:08 PST. Four research agents run in parallel, one per project.
- November 5, 2026, merger: merged on the integrated branch `worktree-agent-adfa26ba0a813e559` (head c492ce9d, where an integrator joined tickets 152, 155, 150, 154 and the four research branches of ticket 153, each gated on commit) into build/strata as merge commit 01f76c67, with history, because the history scan found no keys in the branch's commits. The gate on the merge commit passed in 168.3 seconds, under tonight's 180-second limit; the integrator's final gate on the branch passed in 154.5 seconds. The secret scan on build/strata after the merge found no keys. The worktree that built it, `.claude/worktrees/agent-adfa26ba0a813e559`, is removed after this commit. The branch stays.
  - Evidence: tonight's rule from the user (November 5, 18:05 PST) is essentials only, with no review or verify round, so the integrator's report is the evidence. The four research agents' sample files and recordings give 131 outside items, plus the GDACS and agency items. The seed on a fresh state file gives P130164 31 items, P145559 25, P156634 60, P161305 38 and P167814 28. The recorded P156634 writer answer replays with 70 kept and 0 removed. The recordings total 22.28 MB, under the 25 MB cap; the CAG PDF's recording is kept without its body. Criterion 3 is the workspace part and waits on ticket 151's agent.
  - Workspace results: none run tonight. Ticket 151's agent runs the six steps under "Tickets 150, 152, 153, 154 and 155, the second deploy of the Prism night" in `docs/workspace-catchup.md`, steps 4 to 6 for the seed of all five projects, a brief per project and the check of each.
