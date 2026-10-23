# Issue tracker: Local Markdown

Issues and specs for this repo live as markdown files in `.scratch/`, committed to git so every worktree sees them.

## Conventions

- One feature per directory. Strata's build is `.scratch/strata/`.
- The spec is `.scratch/strata/spec.md`.
- Implementation issues are one file per ticket at `.scratch/strata/issues/<NN>-<slug>.md`, numbered from `01`, never a single combined tickets file.
- A ticket's state is the `Status:` line near the top of its file (role strings in `triage-labels.md`, build states below). Its blockers are the `Blocked by:` line.
- Comments and conversation history append to the bottom of the file under a `## Comments` heading, newest last, each starting with the date and the agent role.

## Build states

A ticket moves through these values of its `Status:` line, and only the named role moves it. Ticket files change only on the integration branch `build/strata`, in the main checkout; implementers leave them alone, so merges never conflict on them.

| Status | Set by | Means |
|---|---|---|
| `ready-for-agent` | `/to-tickets` | Fully specified; can start once every ticket in `Blocked by` is `done` |
| `ready-for-human` | `/to-tickets` or the orchestrator | Needs a person (credentials, an outside account, a decision) |
| `in-progress` | the orchestrator, on dispatch | An implementer is building it |
| `in-review` | the orchestrator, when the implementer reports | Reviews running; the comment names the branch and worktree |
| `done` | the merger, after merging | Merged into `build/strata`; the comment names the merge commit and the evidence |

**Frontier:** every ticket whose `Status` is `ready-for-agent` and whose blockers are all `done`. When there are more than the orchestrator can run at once, the ticket with the longest chain of tickets waiting on it goes first, and the lowest number breaks ties (see the standing rules in `build.md`).

## When a skill says "publish to the issue tracker"

Create a new file under `.scratch/strata/` (creating the directory if needed).

## When a skill says "fetch the relevant ticket"

Read the file at the referenced path. The user will normally pass the path or the issue number directly.

## When a skill says "close" or "resolve" a ticket

Set `Status: done` and append a comment with the merge commit. Never delete a ticket file.
