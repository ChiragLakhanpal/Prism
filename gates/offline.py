#!/usr/bin/env python3
"""Strata's offline gate (CLAUDE.md rule 6), run by .githooks/pre-commit.

It runs the steps listed in gates/steps.toml, in order, from the root of the tree it
was started in. It stops at the first step that fails, prints the total time, and fails
when the whole run takes longer than the limit in that file. When every staged file is
Markdown, it runs only the steps marked `always`. Steps run with the network switched
off for uv, npm and Playwright, and without git's hook variables, so a test that builds
its own repo cannot touch the commit in progress.

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
    "STRATA_OFFLINE": "1",
}


def load_steps(path=STEPS_FILE):
    with open(path, "rb") as handle:
        config = tomllib.load(handle)
    steps = config.get("step", [])
    for step in steps:
        unknown = set(step) - STEP_KEYS
        if unknown or "name" not in step or not isinstance(step.get("run"), list):
            raise SystemExit(f"{path}: the step {step.get('name', '(unnamed)')!r} needs a name and a run list, "
                             f"and only these keys: {', '.join(sorted(STEP_KEYS))}.")
    return float(config.get("limit_seconds", 120)), steps


def staged_files():
    done = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"],
                          capture_output=True, text=True, check=True)
    return [name for name in done.stdout.split("\0") if name]


def only_markdown(files):
    return bool(files) and all(name.lower().endswith(MARKDOWN) for name in files)


def step_env(keep_git):
    env = {k: v for k, v in os.environ.items() if keep_git or not k.startswith("GIT_")}
    env.update(OFFLINE)
    return env


def run_step(step, seconds_left):
    """Run one step in its own process group. Return (exit code or None on timeout, output)."""
    process = subprocess.Popen(step["run"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               env=step_env(step.get("git_env", False)), start_new_session=True)
    try:
        output, _ = process.communicate(timeout=max(seconds_left, 0.01))
        return process.returncode, output
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        output, _ = process.communicate()
        return None, output


def indent(text):
    return "".join(f"    {line}\n" for line in text.rstrip().splitlines())


def seconds(value):
    return f"{value:.1f} seconds"


def main():
    started = time.monotonic()
    limit, steps = load_steps()
    if only_markdown(staged_files()):
        print("Only Markdown files are staged, so the gate skips the tests.")
        steps = [step for step in steps if step.get("always")]

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
            print(f"The gate failed: it ran longer than {limit:g} seconds, the limit in {STEPS_FILE}, "
                  f"during \"{step['name']}\".")
            return 1
        if code != 0:
            print(indent(output), end="")
            print(f"The gate failed in {seconds(time.monotonic() - started)}: \"{step['name']}\" "
                  f"exited with code {code}. Fix what it reports and commit again.")
            return 1
        if step.get("show"):
            print(indent(output), end="")
        print(f"  passed in {seconds(took)}.")

    total = time.monotonic() - started
    if total > limit:
        print(f"The gate failed: it took {seconds(total)}, longer than {limit:g} seconds, the limit in {STEPS_FILE}.")
        return 1
    print(f"The gate passed in {seconds(total)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
