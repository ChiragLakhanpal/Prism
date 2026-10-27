#!/usr/bin/env python3
"""Strata's offline gate, which CLAUDE.md rule 6 requires. Git runs it through .githooks/.

It runs the steps listed in gates/steps.toml from the root of the tree it was started in.
A step with no lane runs alone, after everything before it has finished. Neighbouring steps
that have lanes run side by side, one thread per lane, and each lane runs its own steps in
order. When a step fails, the gate stops every other lane and prints that step's output.
The time limit in that file covers the whole run once the gate holds the lock: when it passes,
the gate stops every lane. When every staged file is Markdown, it runs only the steps marked
`always`, once it has checked that none of those files has changes that are not staged.
Otherwise it first checks that no tracked file has changes that are not staged. Either way the
tests see what the commit holds. Steps run with the network switched off for uv, npm and
Playwright. They also run without git's hook variables, so a test that builds its own repo
cannot touch the commit in progress.
A step that names the scratch folder .gate-tmp/, as the pytest steps do with --basetemp, finds
it made, since pytest needs the folder's parent to exist; .gitignore leaves it out (ticket 73).

One gate runs at a time on this computer. Before it starts its clock, the gate holds a lock on
a file in the temporary folder, or on the file that STRATA_GATE_LOCK names, and writes its
process id and the time into that file. A second gate waits for that lock, up to
lock_wait_seconds in gates/steps.toml, says which process holds it, and then gives up.

This file uses only the standard library, so it runs before anything is installed.
"""

import fcntl
import os
import re
import shutil
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


HOLDER = re.compile(r"process (\d+), since (.+)")


def holder(path):
    """The end of the waiting line that names the holder, such as ", which process 123 has held since
    2026-10-27 05:12:03", or "" when the file holds no such line yet."""
    try:
        found = HOLDER.fullmatch(Path(path).read_text().strip())
    except OSError:
        return ""
    return f", which process {found[1]} has held since {found[2]}" if found else ""


def hold_lock(path, wait_limit, limit):
    """Wait until this gate holds the lock, and return the open file that holds it.

    The system lets go of the lock when the gate's process ends, however it ends. Return None
    when another gate still holds the lock after wait_limit seconds. Once it holds the lock, the
    gate writes its process id and the time into the file. That keeps the file's time fresh, so
    the system never removes it from the temporary folder as old while a gate holds it, and it
    lets a waiting gate say which process holds the lock.
    """
    try:
        handle = open(path, "a")  # "a" makes the file when it is missing and never empties the holder's line.
    except OSError as error:
        raise SystemExit(f"The gate could not open the lock {path}: {error.strerror}. "
                         f"Set {LOCK_VARIABLE} to a file in a folder you can write, or unset it.") from None
    started = time.monotonic()
    blocked = told = False

    def tell(who=""):
        print("Another gate is running on this computer, so this gate waits for it to finish. "
              f"It waits up to {duration(wait_limit)} for the lock {path}{who}.", flush=True)

    while True:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            blocked, waited, who = True, time.monotonic() - started, holder(path)
            # The holder writes its line just after it takes the lock, so give the line a second to appear.
            if not told and (who or waited >= min(1, wait_limit)):
                tell(who)
                told = True
            if waited >= wait_limit:
                handle.close()
                return None
            time.sleep(POLL_SECONDS)
            continue
        if blocked and not told:
            tell()
        handle.truncate(0)
        handle.write(f"process {os.getpid()}, since {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        handle.flush()
        if blocked:
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


def unstaged_changes(paths=()):
    """True when a tracked file in the working tree, or one of paths when it names some, differs from what the commit
    will hold."""
    done = subprocess.run(["git", "diff", "--quiet", "--", *paths], capture_output=True, text=True)
    if done.returncode not in (0, 1):
        raise SystemExit("The gate could not compare the working tree with the staged changes. "
                         f"Git said this: {done.stderr.strip()}")
    return done.returncode == 1


def only_markdown(files):
    return bool(files) and all(name.lower().endswith(MARKDOWN) for name in files)


def markdown_only_steps(steps):
    """The steps a commit of only Markdown runs: those marked `always`."""
    return [step for step in steps if step.get("always")]


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
        self.missing = {}  # the program each step could not start, by the step's name

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


def program(run):
    """The program a step starts: its first word or, after `env`, the first word that is not NAME=value.

    None when `env` takes an option, which this does not read, so the step starts and env reports what it lacks.
    """
    if os.path.basename(run[0]) != "env":
        return run[0]
    for arg in run[1:]:
        if arg.startswith("-"):
            return None
        if "=" not in arg:
            return arg
    return run[0]


# uv, npm and python3: scripts/install needs them and runs uv and npm itself, so it cannot be the first fix.
INSTALL = "Install it as the Install section of README.md says, then run scripts/install"


def run_lane(steps, run, done):
    """Run a lane's steps in order. Stop at the first one that does not pass, or when another lane stops.

    Set `done` at the end, however the lane ends. A step whose program is not on the PATH does not start, so its
    message names that program, even when the step starts it through `env` as the web lanes do.
    """
    try:
        for step in steps:
            if run.halt.is_set():
                return
            if step.get("lane") is None:
                run.say(f"- {step['name']} ...\n")
            step_started = time.monotonic()
            needed = program(step["run"])
            try:
                if needed is not None and shutil.which(needed) is None:
                    raise FileNotFoundError(2, "No such file or directory", needed)
                code, output = run_step(step, run)
            except FileNotFoundError as missing:
                run.missing[step["name"]] = missing.filename
                code, output = 127, f"{missing.filename} is not installed. {INSTALL}.\n"
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

    It waits in slices of POLL_SECONDS. macOS can hand Ctrl-C to a lane thread, and Python
    runs the handler in this thread only when this thread wakes, so a wait with no timeout
    would last until the lane ended (ticket 54's F1). The lanes must not block the signal
    instead, because the steps they start would inherit the block.
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
        wait_for(finished)
    except BaseException:  # On Ctrl-C, stop every lane here, because each step runs in its own session.
        run.halt.set()
        wait_for(finished)
        raise
    if run.crashed:
        raise run.crashed[0]


def wait_for(events):
    """Wait until every event is set, waking each POLL_SECONDS so a Ctrl-C that landed on another thread runs."""
    for event in events:
        while not event.wait(POLL_SECONDS):
            pass


def indent(text):
    return "".join(f"    {line}\n" for line in text.rstrip().splitlines())


def seconds(value):
    return f"{value:.1f} seconds"


def duration(value):
    """A setting in seconds as a person says it: "20 minutes" for 1200, "1 second" for 1, "90 seconds" for 90."""
    count, unit = (value / 60, "minute") if value >= 60 and value % 60 == 0 else (value, "second")
    return f"{count:g} {unit}" + ("" if count == 1 else "s")


def listed(names):
    return names[0] if len(names) == 1 else f"{', '.join(names[:-1])} and {names[-1]}"


def main():
    limit, lock_wait, steps = load_steps()
    if any(arg.startswith(str(SCRATCH)) for step in steps for arg in step["run"]):
        SCRATCH.mkdir(exist_ok=True)  # pytest's --basetemp needs the folder's parent to exist
    path = lock_path()
    lock = hold_lock(path, lock_wait, limit)  # Held until this process ends. The limit starts once it is held.
    if lock is None:
        print(f"The gate gave up after {duration(lock_wait)}, the wait limit in {STEPS_FILE}, because another gate "
              f"on this computer still holds the lock {path}, so commit again once that gate finishes.")
        return 1
    run = Run(limit)
    files = staged_files()
    markdown = only_markdown(files)
    # A Markdown-only commit checks only its own files, so a note commits beside unrelated work in progress.
    if files and unstaged_changes(files if markdown else ()):
        print("Some changes to tracked files are not staged. Stage them or stash them, then commit again, "
              "so the gate tests what you commit.")
        return 1
    if markdown:
        print("Only Markdown files are staged, so the gate runs only the steps marked always.")
        steps = markdown_only_steps(steps)

    for stage in stages(steps):
        run_stage(stage, run)
        if run.halt.is_set():
            break

    if run.failed:
        step, code = run.failed[0]
        took = seconds(time.monotonic() - run.started)
        if step["name"] in run.missing:
            print(f"The gate failed after {took}. The step \"{step['name']}\" could not start, because "
                  f"{run.missing[step['name']]} is not installed. {INSTALL} and commit again.")
            return 1
        advice = ("Code 127 means the step could not find a command. Run scripts/install, then commit again."
                  if code == 127 else "Fix what it reports and commit again.")
        print(f"The gate failed after {took}. The step \"{step['name']}\" exited with code {code}. {advice}")
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
