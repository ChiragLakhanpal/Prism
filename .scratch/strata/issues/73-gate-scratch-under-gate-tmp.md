# 73: The gate's pytest runs keep their scratch where the next run clears it, so a stopped run cannot fill the disk

**What to build:** On October 25, 2026 at 23:50 PDT the Mac's data volume was full, and no command could start in any session. pytest's shared temporary folder (`$TMPDIR/pytest-of-<user>`) held 301 run folders, about 408 GB. The cause has two parts. First, most tests copy the 38 MB fixture database into their `tmp_path`, so one full run of `tests/` holds about 7 GB, and pytest's default retention policy (`all`) keeps every test's folder until the run ends. Second, when the gate's limit passes, `gates/offline.py` stops a pytest run with SIGTERM, so pytest's own exit cleanup never runs, and pytest 9 keeps a stopped run's folder locked for three days before any later run may delete it (`LOCK_TIMEOUT` in `_pytest/pathlib.py`). Every red gate left up to three such folders, and nothing ever removed them. Fix both parts: in `pyproject.toml`, set `tmp_path_retention_policy = "failed"`, so a passing test's folder goes as soon as the test ends and only a failed test's folder stays for a look; and in `gates/steps.toml`, give each of the gate's three pytest steps its own scratch folder with `--basetemp .gate-tmp/<lane>`, which pytest clears at the start of its next run, so a run the gate stops leaves one small folder in the worktree and nothing in the shared temporary folder. The gate makes `.gate-tmp/` when a step names it, and `.gitignore` leaves it out. A test in `tests/test_gate.py` fails a pytest step without a `--basetemp` under `.gate-tmp/`, two steps that share one, or a `.gitignore` without the folder, and a test proves the gate makes the folder for a step that names it. README's gate section says where a run's scratch lives and how to keep every test's folder for one run (`-o tmp_path_retention_policy=all`). The 408 GB backlog is the user's to delete (the folders are pytest's, not the repo's); this ticket stops it growing.

Read first: `gates/offline.py` (`stop`, `run_step`, `main`); `gates/steps.toml` (the three pytest steps); `tests/test_gate.py` (`gate_steps`, `paths_tested`, the steps-file tests at the end); `tests/conftest.py` (`fixture_db` takes a lock in the basetemp's parent folder); `tests/test_lessons_page.py` line 31 (the shared story folder); README's gate section.

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** ops
**Phase:** P2
**Design review:** no

- [ ] `pyproject.toml` sets `tmp_path_retention_policy = "failed"`, and each pytest step in `gates/steps.toml` passes `--basetemp .gate-tmp/<lane>` with a folder of its own; `tests/test_gate.py` fails a steps file that breaks either rule, and `.gitignore` lists `.gate-tmp/`.
- [ ] The gate makes `.gate-tmp/` before a step that names it runs, proven by a throwaway repo whose only step passes when the folder exists; a full gate run on this change leaves no new folder in `$TMPDIR/pytest-of-<user>` and at most one folder per lane under `.gate-tmp/`.
- [ ] README's gate section says where the gate's pytest scratch lives, that a passing test's folder is removed at once, and how to keep every folder for one run.

## Comments

- October 26, 2026, orchestrator: opened at 02:40 PDT after the disk filled overnight and stopped every session. Built by the orchestrator itself in the worktree `.claude/worktrees/orch-73`, because no wave can run safely until it lands. The lasting fix for the orphaned Playwright servers stays with ticket 56 or 57; this ticket is only the pytest scratch.
