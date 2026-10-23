#!/usr/bin/env python3
"""Strata's offline gate, which CLAUDE.md rule 6 requires. Git runs it through .githooks/.

It runs the steps listed in gates/steps.toml, in order, from the root of the tree it
was started in. It stops at the first step that fails, prints the total time, and fails
when the whole run takes longer than the limit in that file. When every staged file is
Markdown, it runs only the steps marked `always`. Otherwise it first checks that no
tracked file has changes that are not staged, so the tests see what the commit holds.
Steps run with the network switched off for uv, npm and Playwright. They also run without
git's hook variables, so a test that builds its own repo cannot touch the commit in progress.

This file uses only the standard library, so it runs before anything is installed.
"""

import os
import signal
import subprocess
import sys
import time
import tomllib
from pathlib import Path

STEPS_FILE = Path("gates/steps.toml")
MARKDOWN = (".md", ".markdown")
STEP_KEYS = {"name", "run", "always", "git_env", "show"}
OFFLINE = {
    "UV_OFFLINE": "1",
    "npm_config_offline": "true",
    "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1",
}


def load_steps(path=STEPS_FILE):
    with open(path, "rb") as handle:
        config = tomllib.load(handle)
    steps = config.get("step", [])
    for step in steps:
        unknown = set(step) - STEP_KEYS
        if unknown or "name" not in step or not isinstance(step.get("run"), list):
            raise SystemExit(f"The step {step.get('name', 'with no name')!r} in {path} needs a name and a run list. "
                             f"It can use only these keys: {', '.join(sorted(STEP_KEYS))}.")
    return float(config.get("limit_seconds", 120)), steps


def staged_files():
    # --no-renames lists both names of a renamed file, so a code file renamed to Markdown still counts as code.
    done = subprocess.run(["git", "diff", "--cached", "--name-only", "--no-renames", "-z"],
                          capture_output=True, text=True, check=True)
    return [name for name in done.stdout.split("\0") if name]


def unstaged_changes():
    """True when a tracked file in the working tree differs from what the commit will hold."""
    done = subprocess.run(["git", "diff", "--quiet"], capture_output=True, text=True)
    if done.returncode not in (0, 1):
        raise SystemExit("The gate could not compare the working tree with the staged changes. "
                         f"Git said this: {done.stderr.strip()}")
    return done.returncode == 1


def only_markdown(files):
    return bool(files) and all(name.lower().endswith(MARKDOWN) for name in files)


def step_env(keep_git):
    env = {k: v for k, v in os.environ.items() if keep_git or not k.startswith("GIT_")}
    env.update(OFFLINE)
    return env


def stop(process):
    """Stop a step and everything it started. Ask first, so test runners can shut their servers down."""
    for sig, grace in ((signal.SIGTERM, 5), (signal.SIGKILL, None)):
        try:
            os.killpg(process.pid, sig)
        except ProcessLookupError:
            break
        try:
            return process.communicate(timeout=grace)[0]
        except subprocess.TimeoutExpired:
            continue
    return process.communicate()[0]


def run_step(step, seconds_left):
    """Run one step in its own process group. Return (exit code or None on timeout, output)."""
    process = subprocess.Popen(step["run"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               env=step_env(step.get("git_env", False)), start_new_session=True)
    try:
        output, _ = process.communicate(timeout=max(seconds_left, 0.01))
        return process.returncode, output
    except subprocess.TimeoutExpired:
        return None, stop(process)
    except BaseException:  # On Ctrl-C, stop the step here, because it runs in its own session.
        stop(process)
        raise


def indent(text):
    return "".join(f"    {line}\n" for line in text.rstrip().splitlines())


def seconds(value):
    return f"{value:.1f} seconds"


def main():
    started = time.monotonic()
    limit, steps = load_steps()
    files = staged_files()
    if only_markdown(files):
        print("Only Markdown files are staged, so the gate skips the tests.")
        steps = [step for step in steps if step.get("always")]
    elif files and unstaged_changes():
        print("Some changes to tracked files are not staged. Stage them or stash them, then commit again, "
              "so the gate tests what you commit.")
        return 1

    for step in steps:
        print(f"- {step['name']} ...", flush=True)
        step_started = time.monotonic()
        try:
            code, output = run_step(step, limit - (step_started - started))
        except FileNotFoundError as missing:
            code, output = 127, f"{missing.filename} is not installed. Run scripts/install first.\n"
        took = time.monotonic() - step_started
        if code is None:
            print(indent(output), end="")
            print(f"The gate failed because it ran longer than {limit:g} seconds, the limit in {STEPS_FILE}. "
                  f"It stopped during \"{step['name']}\".")
            return 1
        if code != 0:
            print(indent(output), end="")
            print(f"The gate failed after {seconds(time.monotonic() - started)}. The step \"{step['name']}\" "
                  f"exited with code {code}. Fix what it reports and commit again.")
            return 1
        if step.get("show"):
            print(indent(output), end="")
        print(f"  passed in {seconds(took)}.")

    total = time.monotonic() - started
    if total > limit:
        print(f"The gate failed because it took {seconds(total)}, and the limit in {STEPS_FILE} is {limit:g} seconds.")
        return 1
    print(f"The gate passed in {seconds(total)}.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nThe gate was stopped before it finished, so the commit did not go through.")
        sys.exit(130)
