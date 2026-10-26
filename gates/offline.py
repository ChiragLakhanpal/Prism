#!/usr/bin/env python3
"""Strata's offline gate, which CLAUDE.md rule 6 requires. Git runs it through .githooks/.

It runs the steps listed in gates/steps.toml from the root of the tree it was started in.
A step with no lane runs alone, after everything before it has finished. Neighbouring steps
that have lanes run side by side, one thread per lane, and each lane runs its own steps in
order. When a step fails, the gate stops every other lane and prints that step's output.
The time limit in that file covers the whole run: when it passes, the gate stops every lane.
When every staged file is Markdown, it runs only the steps marked `always`. Otherwise it
first checks that no tracked file has changes that are not staged, so the tests see what the
commit holds. Steps run with the network switched off for uv, npm and Playwright. They also
run without git's hook variables, so a test that builds its own repo cannot touch the commit
in progress.
A step that names the scratch folder .gate-tmp/, as the pytest steps do with --basetemp, finds
it made, since pytest needs the folder's parent to exist; .gitignore leaves it out (ticket 73).

One gate runs at a time on this computer. Before it starts its clock, the gate holds a lock on
a file in the temporary folder, or on the file that STRATA_GATE_LOCK names. A second gate waits
for that lock, up to lock_wait_seconds in gates/steps.toml, and then gives up.

This file uses only the standard library, so it runs before anything is installed.
"""

import fcntl
import os
import signal
import subprocess
import sys
import tempfile
import threading
import time
import tomllib
from pathlib import Path

STEPS_FILE = Path("gates/steps.toml")
# The lock that lets one gate run at a time on this computer. It lives outside the repo, because
# each worktree is its own copy of the repo. The gate's own tests name their own file instead.
LOCK_FILE = Path(tempfile.gettempdir()) / "strata-gate.lock"
LOCK_VARIABLE = "STRATA_GATE_LOCK"
SCRATCH = Path(".gate-tmp")  # the steps' scratch folder, where the pytest steps' --basetemp folders live (ticket 73)
MARKDOWN = (".md", ".markdown")
STEP_KEYS = {"name", "run", "always", "git_env", "show", "lane"}
OFFLINE = {
    "UV_OFFLINE": "1",
    "npm_config_offline": "true",
    "PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD": "1",
}
# How often a running step checks whether it must stop, because the limit passed or another lane failed.
POLL_SECONDS = 0.2


def load_steps(path=STEPS_FILE):
    with open(path, "rb") as handle:
        config = tomllib.load(handle)
    steps = config.get("step", [])
    for step in steps:
        unknown = set(step) - STEP_KEYS
        if unknown or "name" not in step or not isinstance(step.get("run"), list):
            label = f"\"{step['name']}\"" if "name" in step else "with no name"
            raise SystemExit(f"The step {label} in {path} needs a name and a run list. "
                             f"It can use only these keys: {', '.join(sorted(STEP_KEYS))}.")
        if "lane" in step and not (isinstance(step["lane"], str) and step["lane"].strip()):
            raise SystemExit(f"The lane of the step \"{step['name']}\" in {path} must be a name in quotes, "
                             "such as lane = \"python\".")
    return float(config.get("limit_seconds", 120)), float(config.get("lock_wait_seconds", 1200)), steps


def lock_path():
    return Path(os.environ.get(LOCK_VARIABLE) or LOCK_FILE)


def hold_lock(path, wait_limit, limit):
    """Wait until this gate holds the lock, and return the open file that holds it.

    The system lets go of the lock when the gate's process ends, however it ends. Return None
    when another gate still holds the lock after wait_limit seconds.
    """
    handle = open(path, "a")  # "a" makes the file when it is missing and never empties it.
    started = time.monotonic()
    waiting = False
    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            if not waiting:
                print("Another gate is running on this computer, so this gate waits for it to finish. "
                      f"It waits up to {wait_limit:g} seconds for the lock {path}.", flush=True)
                waiting = True
            if time.monotonic() - started >= wait_limit:
                handle.close()
                return None
            time.sleep(POLL_SECONDS)
            continue
        if waiting:
            print(f"This gate waited {seconds(time.monotonic() - started)} for the other gate. "
                  f"Its {limit:g}-second limit starts now.", flush=True)
        return handle


def stages(steps):
    """Split the steps into stages that run one after another.

    A step with no lane is a stage on its own. A run of neighbouring steps with lanes is one
    stage. Each stage maps a lane's name to its steps in file order; a lone step's lane is None.
    """
    found = []
    for step in steps:
        lane = step.get("lane")
        if lane is None or not found or None in found[-1]:
            found.append({})
        found[-1].setdefault(lane, []).append(step)
    return found


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


# What run_step returns in place of an exit code when the gate stopped the step itself.
OVER_LIMIT, STOPPED = "over the limit", "stopped"
# How a step in a lane ended, as the gate prints it. Any other exit code means it failed.
ENDINGS = {0: "passed in", STOPPED: "was stopped after", OVER_LIMIT: "was stopped by the limit after"}


class Run:
    """One run of the gate. Its lanes share the deadline, the signal to stop, and the screen."""

    def __init__(self, limit):
        self.started = time.monotonic()
        self.limit = limit
        self.halt = threading.Event()
        self.screen = threading.Lock()
        self.failed = []  # (step, exit code) for each step that failed, in the order they finished
        self.over = []  # the steps the limit stopped
        self.crashed = []  # errors the gate itself hit inside a lane

    def seconds_left(self):
        return self.limit - (time.monotonic() - self.started)

    def say(self, text):
        with self.screen:
            print(text, end="", flush=True)

    def finish(self, step, code, output, took):
        """Note how a step ended and print its lines together. A step that did not pass stops every lane."""
        lane = step.get("lane")
        shown = "" if code == STOPPED or (code == 0 and not step.get("show")) else indent(output)
        if lane is None:  # A lone step printed its name when it started, as the gate always has.
            lines = shown + (f"  passed in {took}.\n" if code == 0 else "")
        else:
            lines = f"- \"{step['name']}\" {ENDINGS.get(code, 'failed after')} {took}, in the {lane} lane.\n{shown}"
        with self.screen:
            if code == OVER_LIMIT:
                self.over.append(step)
            elif code not in (0, STOPPED):
                self.failed.append((step, code))
            if code != 0:
                self.halt.set()
            print(lines, end="", flush=True)


def run_step(step, run):
    """Run one step in its own process group, so stopping it stops everything it started.

    Return (exit code, output). In place of the code, return OVER_LIMIT when the limit passed,
    or STOPPED when another lane failed or the person pressed Ctrl-C.
    """
    process = subprocess.Popen(step["run"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               env=step_env(step.get("git_env", False)), start_new_session=True)
    try:
        while True:
            try:
                output, _ = process.communicate(timeout=min(POLL_SECONDS, max(run.seconds_left(), 0.01)))
                return process.returncode, output
            except subprocess.TimeoutExpired:
                if run.seconds_left() <= 0:
                    return OVER_LIMIT, stop(process)
                if run.halt.is_set():
                    return STOPPED, stop(process)
    except BaseException:  # If the gate itself breaks, stop the step here, because it runs in its own session.
        stop(process)
        raise


def run_lane(steps, run, done):
    """Run a lane's steps in order. Stop at the first one that does not pass, or when another lane stops.

    Set `done` at the end, however the lane ends.
    """
    try:
        for step in steps:
            if run.halt.is_set():
                return
            if step.get("lane") is None:
                run.say(f"- {step['name']} ...\n")
            step_started = time.monotonic()
            try:
                code, output = run_step(step, run)
            except FileNotFoundError as missing:
                code, output = 127, f"{missing.filename} is not installed. Run scripts/install first.\n"
            run.finish(step, code, output, seconds(time.monotonic() - step_started))
            if code != 0:
                return
    except BaseException as error:  # main() raises it again, so the gate fails as loudly as it would without lanes.
        run.crashed.append(error)
        run.halt.set()
    finally:
        done.set()


def run_stage(stage, run):
    """Run one stage: a lone step, or a lane for each name in the stage, side by side.

    The gate waits on each lane's `done` event, not on its thread. When Ctrl-C breaks into
    Thread.join, Python can report a lane that is still running as finished, and the gate
    would then exit before that lane stopped its step. The lanes start inside the `try`, so
    Ctrl-C between two starts still stops the lanes that started.
    """
    lanes = [lane for lane in stage if lane is not None]
    if lanes:
        run.say(f"- The gate runs the {listed(lanes)} {'lanes side by side' if len(lanes) > 1 else 'lane'}.\n")
    finished = []
    try:
        for steps in stage.values():
            done = threading.Event()
            threading.Thread(target=run_lane, args=(steps, run, done)).start()
            finished.append(done)
        for done in finished:
            done.wait()
    except BaseException:  # On Ctrl-C, stop every lane here, because each step runs in its own session.
        run.halt.set()
        for done in finished:
            done.wait()
        raise
    if run.crashed:
        raise run.crashed[0]


def indent(text):
    return "".join(f"    {line}\n" for line in text.rstrip().splitlines())


def seconds(value):
    return f"{value:.1f} seconds"


def listed(names):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def main():
    limit, lock_wait, steps = load_steps()
    if any(arg.startswith(str(SCRATCH)) for step in steps for arg in step["run"]):
        SCRATCH.mkdir(exist_ok=True)  # pytest's --basetemp needs the folder's parent to exist
    path = lock_path()
    lock = hold_lock(path, lock_wait, limit)  # Held until this process ends. The limit starts once it is held.
    if lock is None:
        print(f"The gate gave up after {lock_wait:g} seconds, the wait limit in {STEPS_FILE}, because another gate "
              f"on this computer still holds the lock {path}.")
        return 1
    run = Run(limit)
    files = staged_files()
    if only_markdown(files):
        print("Only Markdown files are staged, so the gate skips the tests.")
        steps = [step for step in steps if step.get("always")]
    elif files and unstaged_changes():
        print("Some changes to tracked files are not staged. Stage them or stash them, then commit again, "
              "so the gate tests what you commit.")
        return 1

    for stage in stages(steps):
        run_stage(stage, run)
        if run.halt.is_set():
            break

    if run.failed:
        step, code = run.failed[0]
        advice = ("Code 127 means the step could not find a command. Run scripts/install, then commit again."
                  if code == 127 else "Fix what it reports and commit again.")
        print(f"The gate failed after {seconds(time.monotonic() - run.started)}. The step \"{step['name']}\" "
              f"exited with code {code}. {advice}")
        return 1
    if run.over:
        names = listed([f"\"{step['name']}\"" for step in sorted(run.over, key=steps.index)])
        print(f"The gate failed because it ran longer than {limit:g} seconds, the limit in {STEPS_FILE}. "
              f"It stopped during {names}.")
        return 1

    total = time.monotonic() - run.started
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
