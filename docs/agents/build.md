# Running the build

You are the **orchestrator**. You turn the ticket graph in `.scratch/strata/` into a working Strata on one integration branch, `build/strata`, by dispatching a team of subagents and integrating what they return. You plan, dispatch, decide and integrate; the team writes and checks the code.

## The team

Defined in `.claude/agents/`. Dispatch each with the Agent tool by its name.

| Agent | Job | Dispatch when |
|---|---|---|
| `pm` | Keeps `docs/STATUS.md` true: phase, exit criteria, frontier, in flight, blocked, risks, dates, decisions for the user | Start of a run; after each batch of merges; before you report to the user |
| `implementer` | Builds one ticket test-first in its own worktree, following the area brief for the ticket's `Area` | A ticket joins the frontier (with `isolation: worktree`) |
| `design-lead` | UX and design-system adherence: briefs new screens, reviews every user-visible change, builds `Area: design` tickets | A brief before any ticket that introduces a new screen; a review of every `Design review: yes` ticket; an `Area: design` ticket (with `isolation: worktree`) |
| `design-critic` | Independent visual craft review from screenshots, scored against a rubric | Every `Design review: yes` ticket, in parallel with `design-lead`; alone for tickets `design-lead` built |
| `reviewer` | Code review of the ticket's diff on two axes, Standards and Spec | Every ticket that reports done |
| `verifier` | Runs the gate, proves each acceptance criterion with evidence, tries to break the change | After the reviewer approves; at every phase gate |
| `merger` | Merges a passed ticket into `build/strata`, keeps the gate green, runs post-merge workspace steps, closes the ticket | When every check for that ticket has passed |

Built-in `Explore` agents handle broad lookups.

## Where things live

- **The main checkout** (this directory) stays on `build/strata`. Only you, `pm` and `merger` change files here, one at a time.
- **Ticket worktrees.** Each implementer builds in its own worktree and branch under `.claude/worktrees/`, started from this checkout's HEAD (`worktree.baseRef` is `head` in `.claude/settings.json`). Gitignored files, `.env` and installed dependencies included, stay behind, so each worktree installs its own. Reviewers, design agents and the verifier read and run the ticket's code from that worktree, whose path you pass them.
- **Notes** go in `.notes/` at the root of the main checkout (gitignored): `<NN>-brief.md`, `<NN>-review.md`, `<NN>-design.md`, `<NN>-critique.md`, `<NN>-verify.md` and `phase-<P>-verify.md`. Give every agent absolute paths.
- **Ticket state** is each ticket's `Status:` line on `build/strata`. Only you and `merger` change ticket files (`docs/agents/issue-tracker.md`), so merges never conflict on them.
- **Secrets** are in the main checkout's `.env`. Worktrees have none.

## Starting a run

1. Read `docs/STATUS.md`, `.scratch/strata/spec.md`, and every ticket's `Status` and `Blocked by` lines. Done when you can name the frontier.
2. First run only: commit everything as `main`'s first commit ("Plan Strata"), run `git switch -c build/strata`, and set `git config core.hooksPath .githooks` so the gate runs on every commit once it exists. Done when `build/strata` is checked out here.
3. **Credentials first.** Run `python3 .claude/hooks/guard.py --env-keys`. If keys are missing, ticket 03 starts in the first wave beside 01. Its implementer reports the wizard before writing the probes; pass the user the exact command to run it in their own terminal from this checkout, then continue the implementer. The user is most likely at the keyboard right after starting the build, so ask then.
4. Dispatch `pm` for a status read. Done when `docs/STATUS.md` reflects today.

## The loop

Repeat until every ticket is `done`:

1. **Dispatch the frontier.** Set each frontier ticket's `Status:` to `in-progress` and commit. Dispatch one `implementer` per ticket (or `design-lead` for `Area: design`) with `isolation: worktree`, at most four at a time. Give each one pointers only: the ticket path, the spec path, its area brief and any notes. Before a ticket that introduces a new screen, get a brief from `design-lead` first and add its path. A `ready-for-human` ticket goes to the user (see below).
2. **Check what comes back.** When an implementer reports, set the ticket to `in-review` with a comment naming its branch and worktree. Dispatch `reviewer`, and for `Design review: yes` also `design-lead` and `design-critic`, in parallel, each with the ticket path, the branch, the worktree path and the notes folder. Then dispatch `verifier`. A blocking finding goes back to the same implementer: continue it with SendMessage (load the tool with ToolSearch if needed), pointing at the notes paths. If that implementer can't continue, dispatch a new one without isolation and tell it to work in the ticket's worktree. Repeat this step after the fix.
3. **Integrate.** When every check passes, dispatch `merger` with the branch, the worktree path, the notes paths and anything the implementer said must run on the shared workspace. Done when the ticket is `done` and the gate is green on `build/strata`.
4. **Recompute the frontier** and return to step 1. After each batch of merges, dispatch `pm`.
5. **Phase gates.** When the last ticket of a phase merges, dispatch `verifier` on `build/strata` with that phase's exit criteria from `docs/PLAN.md` section 13, then `pm`. Tell the user in one short paragraph what now works, what comes next, and any decision they need to make.

## The shared workspace

Strata shares Databricks Free Edition with fairshare (PLAN.md section 2): one SQL warehouse, five concurrent job tasks and one daily compute quota. Work on it happens one run at a time. `merger` runs deploys and jobs after a merge. A ticket that is itself workspace work (the day-one tests, for example) runs alone, and you tell its implementer to pass the main checkout's `.env` with `--env-file`.

## When to involve the user

Only for what you can't decide or do yourself: credentials and outside accounts (call the Skill tool with `mattpocock-skills:wizard` to script those steps for the user to run in their own terminal), a choice that changes scope or the plan, an exit criterion still failing after two attempts, and anything outward-facing (pushing, opening a PR, granting access). Batch your questions into one message and keep the rest of the frontier moving while you wait.

## Keeping your context clear

Work from reports and pointers; leave files and diffs to the subagents. Before your context grows heavy, write a handoff in `docs/STATUS.md` (in flight, next, open decisions) and suggest `/compact` at the next phase gate. Anything outside the spec becomes a new ticket or a "designed, not built" line for the proposal, decided with `pm`.

## Standing rules for this build (added October 22, 2026)

- **Start the session inside this folder.** The guard hook, the named agents and `/build` load only when the session starts in `strata/`. If the Agent tool says a role such as `pm` is not found, the session started one folder up: stop and ask the user to restart with `cd strata && claude`.
- **Credentials may be missing.** When `python3 .claude/hooks/guard.py --env-keys` shows missing keys, do not wait for them. Build and test every offline part of a ticket against the local fixtures. Each step that needs the Databricks workspace, Foundry or Azure is a workspace step: the merger appends its exact command and what proves it worked to `docs/workspace-catchup.md` instead of running it, and the verifier marks that criterion parked, never passed. Ticket 03 becomes `ready-for-human` once its wizard and probes merge, and from then on it counts as satisfied for the frontier. When `.env` is filled, run the catch-up file in order and have the verifier re-check every parked criterion.
- **fairshare may be unreadable.** On the user's machine, every tool gets "Operation not permitted" on it. Write what PLAN.md section 12 describes from its description and the spec, say so in the report, and leave the user one question: grant access and diff later, or accept the rewrite.
- **Words.** Everything a person reads, in the product and in the repo, is plain English a 10th grader can follow, in full sentences, following DESIGN.md section 7 and the unslop rules. The rules are in the repo at `docs/agents/unslop.md` (copied from https://github.com/cursor/plugins/tree/main/pstack/skills/unslop, which is the version the user asked for); point every agent at that file. The user restated this on October 23, 2026: copy, text, answers and UX copy all read at a 10th-grade level.
- **Models.** Every agent runs on Opus 5.5 at effort `xhigh`, set in its frontmatter. When a role is dispatched through a general agent or the Workflow tool, pass the same model and effort by hand.

## Finishing

When every ticket is `done`: call the Skill tool with `mattpocock-skills:code-review` on `build/strata` with `main` as the fixed point, and dispatch an implementer to fix what it raises; have `verifier` run the full gate and the hindsight test; then ask the user whether to open a PR or merge into `main`, and suggest they run `/retro` in this session.
