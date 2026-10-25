"""The offline gate, tested the way it runs: as the pre-commit hook of a real git commit.

Each test builds a throwaway repo that holds this repo's hook and gate runner, with its own
list of steps, so a step can fail, sleep or plant a key without touching this repo.
"""

import fcntl
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import textwrap
import time
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def clean_env():
    """The environment without git's hook variables, so nested git calls act on their own repo.

    It also hides the person's global and system git settings, so a setting such as
    commit.gpgsign cannot make the throwaway commits fail or wait for a passphrase.
    """
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env.update(GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM="1")
    return env


def git(repo, *args, check=True):
    return subprocess.run(
        ["git", "-c", "user.name=Gate Test", "-c", "user.email=gate@example.org", *args],
        cwd=repo, capture_output=True, text=True, env=clean_env(), check=check,
    )


def commit(repo, message="Change"):
    """Run `git commit` with the hook; return the completed process."""
    return git(repo, "commit", "-m", message, check=False)


def head_count(repo):
    return int(git(repo, "rev-list", "--count", "HEAD").stdout.strip())


@pytest.fixture(autouse=True)
def gate_lock(tmp_path, monkeypatch):
    """A lock file of this test's own, so its gates never wait for a real gate or another test's gates.

    The gate that runs these tests holds the real lock, in the temporary folder, for its whole run.
    """
    path = tmp_path / "gate.lock"
    monkeypatch.setenv("STRATA_GATE_LOCK", str(path))
    return path


@pytest.fixture
def repo(tmp_path):
    """A repo with the gate installed and a first commit, ready for a steps file."""
    return make_repo(tmp_path / "repo")


def make_repo(path):
    path.mkdir()
    git(path, "init", "-q", "-b", "work")
    shutil.copytree(ROOT / ".githooks", path / ".githooks")
    (path / "gates").mkdir()
    for name in ("offline.py", "secret_scan.py"):
        shutil.copy(ROOT / "gates" / name, path / "gates" / name)
    git(path, "config", "core.hooksPath", ".githooks")
    write(path, "README.md", "# A throwaway repo\n")
    write(path, "gates/steps.toml", steps_file())
    git(path, "add", "-A")
    git(path, "commit", "-q", "--no-verify", "-m", "Start")
    return path


def write(repo, name, text):
    target = Path(repo) / name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(textwrap.dedent(text))


def steps_file(limit=120, steps=(), lock_wait=None):
    """A steps file: the secret scan always runs, then the given test steps.

    Each step is (name, run) or (name, run, lane). lock_wait sets how long the gate waits for the lock.
    """
    lines = [f"limit_seconds = {limit}"] + ([f"lock_wait_seconds = {lock_wait}"] if lock_wait else []) + [""]
    lines += ["[[step]]", 'name = "Scan for secrets"',
              'run = ["python3", "gates/secret_scan.py"]', "always = true", "git_env = true", ""]
    for name, run, *lane in steps:
        lines += ["[[step]]", f'name = "{name}"', f"run = {run}"]
        lines += [f'lane = "{lane[0]}"'] if lane else []
        lines += [""]
    return "\n".join(lines)


CHECK = ("Run the checks", '["python3", "check.py"]')


def test_a_commit_with_a_failing_test_is_blocked_and_goes_through_once_fixed(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "raise SystemExit('The total is 3, not 4.')\n")
    git(repo, "add", "-A")

    blocked = commit(repo)

    assert blocked.returncode != 0
    assert head_count(repo) == 1
    assert 'The step "Run the checks" exited with code 1.' in blocked.stdout + blocked.stderr
    assert "The total is 3, not 4." in blocked.stdout + blocked.stderr

    write(repo, "check.py", "print('The total is 4.')\n")
    git(repo, "add", "-A")

    passed = commit(repo)

    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert head_count(repo) == 2


def test_a_commit_that_leaves_its_fix_unstaged_is_blocked(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "raise SystemExit('The total is 3, not 4.')\n")
    git(repo, "add", "-A")
    write(repo, "check.py", "print('The total is 4.')\n")

    blocked = commit(repo)

    assert blocked.returncode != 0
    assert head_count(repo) == 1
    assert "Some changes to tracked files are not staged." in blocked.stdout + blocked.stderr


def test_a_step_that_cannot_find_a_command_says_to_run_the_install(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[("Build", '["sh", "-c", "strata-no-such-command"]')]))
    write(repo, "build.py", "print('ok')\n")
    git(repo, "add", "-A")

    done = commit(repo)

    assert done.returncode != 0
    assert head_count(repo) == 1
    assert "Run scripts/install, then commit again." in done.stdout + done.stderr


def test_a_step_without_a_name_or_a_run_list_is_named_plainly(repo):
    write(repo, "gates/steps.toml", steps_file() + '\n[[step]]\nrun = ["true"]\n\n[[step]]\nname = "Build"\n')
    write(repo, "build.py", "print('ok')\n")
    git(repo, "add", "-A")

    unnamed = commit(repo)

    assert unnamed.returncode != 0
    assert "The step with no name in gates/steps.toml needs a name and a run list." in unnamed.stdout + unnamed.stderr

    write(repo, "gates/steps.toml", steps_file() + '\n[[step]]\nname = "Build"\n')
    git(repo, "add", "-A")

    no_run = commit(repo)

    assert no_run.returncode != 0
    assert 'The step "Build" in gates/steps.toml needs a name and a run list.' in no_run.stdout + no_run.stderr


def test_a_clean_merge_of_a_branch_with_a_failing_check_is_blocked(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "print('ok')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Add a passing check")
    git(repo, "switch", "-q", "-c", "ticket")
    write(repo, "check.py", "raise SystemExit('The merged check ran.')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Break the check on the ticket branch")
    git(repo, "switch", "-q", "work")
    before = git(repo, "rev-parse", "HEAD").stdout

    done = git(repo, "merge", "--no-ff", "-m", "Merge the ticket", "ticket", check=False)

    assert done.returncode != 0
    assert git(repo, "rev-parse", "HEAD").stdout == before
    assert "The merged check ran." in done.stdout + done.stderr


def test_a_merge_the_gate_stopped_stays_in_progress_and_finishes_after_the_install(repo):
    write(repo, ".gitignore", ".installed\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Ignore the stand-in for installed packages")
    git(repo, "switch", "-q", "-c", "ticket")
    needs_a_package = ("Build", '["sh", "-c", "test -f .installed || exit 127"]')
    write(repo, "gates/steps.toml", steps_file(steps=[needs_a_package]))
    write(repo, "build.py", "print('ok')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Add a step that needs a new package")
    git(repo, "switch", "-q", "work")
    before = git(repo, "rev-parse", "HEAD").stdout

    stopped = git(repo, "merge", "--no-ff", "-m", "Merge the ticket", "ticket", check=False)

    assert stopped.returncode != 0
    assert "Run scripts/install, then commit again." in stopped.stdout + stopped.stderr
    assert git(repo, "rev-parse", "HEAD").stdout == before
    assert git(repo, "rev-parse", "-q", "--verify", "MERGE_HEAD", check=False).returncode == 0

    write(repo, ".installed", "")  # what scripts/install does in a real checkout
    finished = git(repo, "commit", "--no-edit", check=False)

    assert finished.returncode == 0, finished.stdout + finished.stderr
    assert len(git(repo, "rev-list", "--parents", "-n", "1", "HEAD").stdout.split()) == 3


def test_the_gate_prints_its_total_time(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "print('ok')\n")
    git(repo, "add", "-A")

    done = commit(repo)

    assert done.returncode == 0, done.stdout + done.stderr
    assert "The gate passed in" in done.stdout + done.stderr
    assert "seconds" in done.stdout + done.stderr


def test_a_commit_of_only_markdown_skips_the_tests(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "raise SystemExit('The tests ran.')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Add a failing check")
    write(repo, "docs/notes.md", "# Notes\n\nOnly words changed.\n")
    git(repo, "add", "-A")

    done = commit(repo)

    output = done.stdout + done.stderr
    assert done.returncode == 0, output
    assert "The tests ran." not in output
    assert "Only Markdown files are staged" in output


def test_a_commit_that_renames_a_code_file_to_markdown_runs_the_tests(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "raise SystemExit('The tests ran.')\n")
    write(repo, "test_totals.py", "def test_total():\n    assert 2 + 2 == 4\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Add a failing check and a test file")
    git(repo, "mv", "test_totals.py", "test_totals.md")

    done = commit(repo)

    assert done.returncode != 0
    assert "The tests ran." in done.stdout + done.stderr


def test_a_commit_with_code_beside_markdown_runs_the_tests(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "raise SystemExit('The tests ran.')\n")
    write(repo, "docs/notes.md", "# Notes\n")
    git(repo, "add", "-A")

    done = commit(repo)

    assert done.returncode != 0
    assert "The tests ran." in done.stdout + done.stderr


def test_the_gate_fails_when_a_run_takes_longer_than_its_limit(repo):
    write(repo, "gates/steps.toml", steps_file(limit=2, steps=[("Sleep", '["python3", "slow.py"]')]))
    write(repo, "slow.py", "import time\ntime.sleep(30)\n")
    git(repo, "add", "-A")

    done = commit(repo)

    output = done.stdout + done.stderr
    assert done.returncode != 0
    assert head_count(repo) == 1
    assert "longer than 2 seconds" in output
    assert 'It stopped during "Sleep".' in output


def test_a_step_that_makes_its_own_repo_leaves_the_commit_alone(repo):
    nested = textwrap.dedent("""\
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                subprocess.run(["git", "-C", tmp, "-c", "user.name=n", "-c", "user.email=n@example.org",
                                "-c", "commit.gpgsign=false", *args],
                               check=True, capture_output=True)
            git("init", "-q")
            open(tmp + "/inner.txt", "w").write("inner")
            git("add", "inner.txt")
            git("commit", "-q", "-m", "Inner")
        """)
    write(repo, "gates/steps.toml", steps_file(steps=[("Make a repo", '["python3", "nested.py"]')]))
    write(repo, "nested.py", nested)
    git(repo, "add", "-A")

    done = commit(repo)

    assert done.returncode == 0, done.stdout + done.stderr
    files = git(repo, "ls-tree", "-r", "--name-only", "HEAD").stdout.split()
    assert "nested.py" in files
    assert "inner.txt" not in files


def fake_databricks_token():
    """Built at run time, so the key's shape never sits in a file the history scan reads."""
    return "dapi" + "0123456789abcdef" * 2


def test_a_planted_key_blocks_the_commit_and_it_passes_once_removed(repo):
    write(repo, "settings.py", f'TOKEN_FOR_DEMO = "{fake_databricks_token()}"\n')
    git(repo, "add", "-A")

    blocked = commit(repo)

    output = blocked.stdout + blocked.stderr
    assert blocked.returncode != 0
    assert "settings.py, line 1" in output
    assert "a Databricks personal access token" in output
    assert fake_databricks_token() not in output, "the scan must not print the key itself"

    write(repo, "settings.py", "TOKEN_FOR_DEMO = None\n")
    git(repo, "add", "-A")

    passed = commit(repo)

    assert passed.returncode == 0, passed.stdout + passed.stderr


def test_a_key_added_by_commit_all_is_caught(repo):
    write(repo, "settings.py", "TOKEN_FOR_DEMO = None\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Add settings")
    write(repo, "settings.py", f'TOKEN_FOR_DEMO = "{fake_databricks_token()}"\n')

    blocked = git(repo, "commit", "-a", "-m", "Change settings without staging first", check=False)

    assert blocked.returncode != 0
    assert "settings.py" in blocked.stdout + blocked.stderr


def test_a_key_in_the_history_fails_the_gate_even_when_only_markdown_is_staged(repo):
    write(repo, "old.cfg", f"DATABRICKS_TOKEN={fake_databricks_token()}\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "An old mistake")
    git(repo, "rm", "-q", "old.cfg")
    git(repo, "commit", "-q", "--no-verify", "-m", "Remove the file but not its history")
    write(repo, "notes.md", "# Notes\n")
    git(repo, "add", "-A")

    done = commit(repo)

    output = done.stdout + done.stderr
    assert done.returncode != 0
    assert "old.cfg" in output
    assert "a Databricks personal access token" in output
    assert "An old mistake" in output


@pytest.mark.parametrize("line", [
    "AZURE_OPENAI_API_KEY={key}",
    'api_key = "{key}"',
    '{{"api_key": "{key}"}}',
    "client_secret='{key}'",
    "APPLICATIONINSIGHTS_CONNECTION_STRING=InstrumentationKey={guid};IngestionEndpoint=https://example.org/",
    "conn = 'DefaultEndpointsProtocol=https;AccountName=strata;AccountKey={b64};EndpointSuffix=core.windows.net'",
    "-----BEGIN {kind} KEY-----",
])
def test_each_key_shape_in_the_example_environment_file_is_caught(repo, line):
    planted = line.format(
        key="a1b2c3d4" * 4,
        guid="12345678-1234-1234-1234-123456789abc",
        b64="Zm9vYmFy" * 8 + "==",
        kind="RSA " + "PRIVATE",
    )
    write(repo, "planted.txt", planted + "\n")
    git(repo, "add", "-A")

    done = commit(repo)

    assert done.returncode != 0, f"not caught: {line}"
    assert "planted.txt" in done.stdout + done.stderr


@pytest.mark.parametrize("line", [
    "DATABRICKS_TOKEN=",
    'token = request.headers.get("x-forwarded-access-token")',
    'DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]',
    "FOUNDRY_PROJECT_ENDPOINT=https://wb-strata.services.ai.azure.com/api/projects/Strata",
    "STRATA_MODEL_AGENT=gpt-5.4-mini",
])
def test_ordinary_lines_pass_the_secret_scan(repo, line):
    write(repo, "ordinary.txt", line + "\n")
    git(repo, "add", "-A")

    done = commit(repo)

    assert done.returncode == 0, done.stdout + done.stderr


def test_the_secret_scan_fails_when_git_cannot_read_the_changes(tmp_path):
    outside = tmp_path / "not-a-repo"
    outside.mkdir()
    env = clean_env() | {"GIT_CEILING_DIRECTORIES": str(tmp_path.resolve())}

    done = subprocess.run([sys.executable, str(ROOT / "gates" / "secret_scan.py")],
                          cwd=outside, capture_output=True, text=True, env=env)

    assert done.returncode != 0
    assert "found no keys" not in done.stdout
    assert "could not read the changes from git" in done.stdout


def test_no_gate_script_hides_a_standard_library_module():
    """Python puts a script's own folder first on its path, so gates/secrets.py would hide `secrets`."""
    names = {path.stem for path in (ROOT / "gates").glob("*.py")}
    assert not names & sys.stdlib_module_names


def test_the_hook_finds_the_root_from_a_worktree(repo, tmp_path):
    write(repo, "gates/steps.toml", steps_file(steps=[CHECK]))
    write(repo, "check.py", "print('ok')\n")
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "--no-verify", "-m", "Add a passing check")
    tree = tmp_path / "tree"
    git(repo, "worktree", "add", "-q", "-b", "ticket", str(tree))
    write(tree, "check.py", "raise SystemExit('The worktree copy ran.')\n")
    git(tree, "add", "-A")

    done = git(tree, "commit", "-m", "Break the check in the worktree", check=False)

    assert done.returncode != 0
    assert "The worktree copy ran." in done.stdout + done.stderr


# Lanes. Each step below runs step.py, which notes in log.txt when it starts and finishes,
# waits, and can fail. The tests run the hook by hand, as a person does, to read its exit code.

STEP = """\
    import os, sys, time
    name, seconds = sys.argv[1], float(sys.argv[2])
    def note(word):
        with open("log.txt", "a") as log:
            log.write(f"{name} {word} {os.getpid()}\\n")
    note("started")
    time.sleep(seconds)
    note("finished")
    if sys.argv[3:] == ["fail"]:
        raise SystemExit(f"{name} found a total of 3, not 4.")
    """


def wait(name, seconds, lane=None, fails=False):
    """A step that waits, then passes or fails."""
    run = json.dumps(["python3", "step.py", name, str(seconds)] + (["fail"] if fails else []))
    return (name, run, lane) if lane else (name, run)


def run_gate(repo, steps, limit=120):
    """Write the steps file and step.py, run the hook by hand, and time it."""
    write(repo, "gates/steps.toml", steps_file(limit=limit, steps=steps))
    write(repo, "step.py", STEP)
    started = time.monotonic()
    done = subprocess.run([".githooks/pre-commit"], cwd=repo, capture_output=True, text=True, env=clean_env())
    return done, time.monotonic() - started


def test_steps_in_different_lanes_run_side_by_side_and_steps_in_one_lane_take_turns(repo):
    apart, apart_seconds = run_gate(repo, [wait("A", 2, lane="one"), wait("B", 2, lane="two")])
    shared, shared_seconds = run_gate(repo, [wait("A", 2, lane="one"), wait("B", 2, lane="one")])

    assert apart.returncode == 0, apart.stdout + apart.stderr
    assert shared.returncode == 0, shared.stdout + shared.stderr
    assert apart_seconds < 3.5, apart.stdout
    assert shared_seconds > 4, shared.stdout


def logged(repo):
    """The lines step.py wrote, such as "A started", in the order the steps wrote them."""
    return [" ".join(line.split()[:2]) for line in (repo / "log.txt").read_text().splitlines()]


def test_a_step_with_no_lane_waits_for_the_lanes_before_it_and_the_steps_after_it_wait_for_it(repo):
    done, _ = run_gate(repo, [wait("A", 0.6, lane="one"), wait("B", 0.3, lane="two"), wait("Alone", 0.3),
                              wait("C", 0, lane="one"), wait("D", 0, lane="two")])

    assert done.returncode == 0, done.stdout + done.stderr
    log = logged(repo)
    assert {"A finished", "B finished"} <= set(log[:log.index("Alone started")]), log
    assert {"C started", "D started"} <= set(log[log.index("Alone finished"):]), log


def pid_of(repo, name):
    return next(int(line.split()[2]) for line in (repo / "log.txt").read_text().splitlines()
                if line.startswith(f"{name} started"))


def was_still_running(pid):
    """True when the process is alive. It is then stopped, so a failing test leaves nothing behind."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    os.kill(pid, signal.SIGKILL)
    return True


def test_a_failing_step_stops_the_other_lanes_and_prints_its_output(repo):
    done, took = run_gate(repo, [wait("Check", 0.5, lane="one", fails=True), wait("Long", 30, lane="two")])

    output = done.stdout + done.stderr
    assert not was_still_running(pid_of(repo, "Long"))
    assert done.returncode == 1, output
    assert took < 10, output
    assert "Check found a total of 3, not 4." in output
    assert 'The step "Check" exited with code 1.' in output


def test_the_limit_covers_the_whole_run_and_stops_every_lane(repo):
    # "Short" alone fits in the limit, but not after the step before it.
    steps = [wait("Warm up", 1), wait("Short", 1.5, lane="one"), wait("Long", 30, lane="two")]

    done, took = run_gate(repo, steps, limit=2)

    output = done.stdout + done.stderr
    assert not was_still_running(pid_of(repo, "Short"))
    assert not was_still_running(pid_of(repo, "Long"))
    assert done.returncode == 1, output
    assert took < 10, output
    assert "The gate failed because it ran longer than 2 seconds, the limit in gates/steps.toml." in output
    assert 'It stopped during "Short" and "Long".' in output


def test_ctrl_c_stops_every_lane(repo):
    write(repo, "gates/steps.toml", steps_file(steps=[wait("A", 30, lane="one"), wait("B", 30, lane="two")]))
    write(repo, "step.py", STEP)
    gate = subprocess.Popen([".githooks/pre-commit"], cwd=repo, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, env=clean_env())
    for _ in range(100):
        if (repo / "log.txt").exists() and len(logged(repo)) == 2:
            break
        time.sleep(0.05)
    time.sleep(0.5)  # Ctrl-C lands while the gate waits on the lanes, as when a person presses it.

    gate.send_signal(signal.SIGINT)
    output, _ = gate.communicate(timeout=20)

    assert not was_still_running(pid_of(repo, "A"))
    assert not was_still_running(pid_of(repo, "B"))
    assert gate.returncode == 130, output
    assert '"A" was stopped' in output and '"B" was stopped' in output, output
    assert "The gate was stopped before it finished, so the commit did not go through." in output


def test_a_lane_that_is_not_a_quoted_name_stops_the_gate_with_a_plain_message(repo):
    write(repo, "gates/steps.toml", steps_file() + '\n[[step]]\nname = "Build"\nrun = ["true"]\nlane = 2\n')

    done = subprocess.run([".githooks/pre-commit"], cwd=repo, capture_output=True, text=True, env=clean_env())

    assert done.returncode != 0
    assert 'The lane of the step "Build" in gates/steps.toml must be a name in quotes, such as lane = "python".' \
        in done.stdout + done.stderr


# One gate at a time. Each gate below runs hold.py, which notes in a log that both gates share
# when its step starts and when it finishes.

HOLD = """\
    import sys, time
    log, name = sys.argv[1], sys.argv[2]
    def note(word):
        with open(log, "a") as handle:
            handle.write(f"{name} {word}\\n")
    note("started")
    time.sleep(2)
    note("finished")
    """

# What a gate prints when another gate holds the lock.
WAITING = "Another gate is running on this computer, so this gate waits for it to finish."


def test_two_gates_started_together_take_turns_and_each_limit_starts_when_its_gate_holds_the_lock(repo, tmp_path):
    shared_log = tmp_path / "steps.txt"
    trees = {"A": repo, "B": make_repo(tmp_path / "other")}
    # Each step takes 2 seconds, so each gate fits in its 3.5-second limit once it holds the lock,
    # but the gate that waits takes longer than that in all.
    for name, tree in trees.items():
        hold = json.dumps(["python3", "hold.py", str(shared_log), name])
        write(tree, "gates/steps.toml", steps_file(limit=3.5, steps=[("Hold", hold)]))
        write(tree, "hold.py", HOLD)

    started = time.monotonic()
    gates = {name: subprocess.Popen([".githooks/pre-commit"], cwd=tree, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, env=clean_env())
             for name, tree in trees.items()}
    output, took = {}, {}
    for name, gate in gates.items():
        output[name] = gate.communicate(timeout=60)[0]
        took[name] = time.monotonic() - started

    log = shared_log.read_text().splitlines()
    first, second = log[0].split()[0], log[-1].split()[0]
    assert log == [f"{first} started", f"{first} finished", f"{second} started", f"{second} finished"], output
    assert gates[first].returncode == 0, output[first]
    assert gates[second].returncode == 0, output[second]
    assert WAITING not in output[first]
    assert WAITING in output[second]
    assert "Its 3.5-second limit starts now." in output[second]
    # The waiting gate ran longer than its limit in all, and passed, so its limit started when it held the lock.
    assert took[second] > 3.5, output[second]


def test_a_gate_that_cannot_get_the_lock_in_time_stops_with_one_sentence(repo, gate_lock):
    write(repo, "gates/steps.toml", steps_file(lock_wait=1, steps=[CHECK]))
    write(repo, "check.py", "raise SystemExit('The checks ran.')\n")

    with open(gate_lock, "a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        started = time.monotonic()
        done = subprocess.run([".githooks/pre-commit"], cwd=repo, capture_output=True, text=True, env=clean_env())
        took = time.monotonic() - started

    output = done.stdout + done.stderr
    assert done.returncode != 0, output
    assert (f"The gate gave up after 1 seconds, the wait limit in gates/steps.toml, because another gate "
            f"on this computer still holds the lock {gate_lock}.") in output
    assert "The checks ran." not in output
    assert 1 <= took < 10, output


# This repo's own steps file.

def gate_steps():
    with open(ROOT / "gates" / "steps.toml", "rb") as handle:
        return tomllib.load(handle)["step"]


# The test folders whose tests may read the fixture database, so they must run after its build.
# ops/bundle/tests reads it through ops/bundle/check.py when the database exists.
FIXTURE_READERS = (Path("tests"), Path("ops/bundle/tests"))


def folders_in_testpaths():
    with open(ROOT / "pyproject.toml", "rb") as handle:
        return [Path(path) for path in tomllib.load(handle)["tool"]["pytest"]["ini_options"]["testpaths"]]


def paths_tested(step):
    """The paths a pytest step names after "pytest", or every folder in testpaths when it names none."""
    if "pytest" not in step["run"]:
        return []
    args = step["run"][step["run"].index("pytest") + 1:]
    named = [Path(arg) for arg in args if not arg.startswith("-") and (ROOT / arg).exists()]
    return named or folders_in_testpaths()


def overlap(one, other):
    """Whether two paths are the same, or one lies inside the other."""
    return one == other or one in other.parents or other in one.parents


def reads_the_fixture_database(step):
    return any(overlap(path, reader) for path in paths_tested(step) for reader in FIXTURE_READERS)


def steps_that_may_start_before_the_fixture_build(steps):
    build = next(i for i, step in enumerate(steps) if "gates/build_fixture.py" in step["run"])
    early = []
    for i, step in enumerate(steps):
        if not reads_the_fixture_database(step):
            continue
        lanes = steps[build].get("lane"), step.get("lane")
        alone_between = any("lane" not in other for other in steps[build + 1:i])
        if i < build or not (None in lanes or lanes[0] == lanes[1] or alone_between):
            early.append(step["name"])
    return early


def gate_steps_per_test_folder(steps):
    """For each folder in testpaths, how many steps run some or all of its tests."""
    tested = [path for step in steps for path in paths_tested(step)]
    return {folder: sum(overlap(folder, path) for path in tested) for folder in folders_in_testpaths()}


def test_the_fixture_database_is_built_before_the_python_tests_that_read_it():
    steps = gate_steps()

    assert any(reads_the_fixture_database(step) for step in steps), "no step runs the tests that read the fixture database"
    assert steps_that_may_start_before_the_fixture_build(steps) == []


def test_each_test_folder_in_pyproject_runs_in_exactly_one_gate_step():
    runs = gate_steps_per_test_folder(gate_steps())

    assert runs and all(count == 1 for count in runs.values()), runs


def workers(step):
    """How many pytest-xdist workers a step asks for: the number after --numprocesses, or one."""
    run = step["run"]
    return int(run[run.index("--numprocesses") + 1]) if "--numprocesses" in run else 1


def test_the_python_tests_that_read_the_fixture_database_run_on_pytest_xdist_workers():
    """The python lane sets the gate's total, and every ticket adds tests under tests/."""
    readers = [step for step in gate_steps() if reads_the_fixture_database(step)]

    assert readers and all(workers(step) > 1 for step in readers), [step["run"] for step in readers]


# Edits to the steps file that the two checks above must catch: each adds a second pytest step,
# in a new lane named web, that runs tests a step in another lane already runs and that may read the
# fixture database while the python lane is still building it.
SECOND_PYTEST_STEPS = {
    "every folder in testpaths": [],
    "a folder inside tests": ["tests/ground_truth"],
    "a file inside tests": ["tests/test_fixture.py"],
    "the bundle tests": ["ops/bundle/tests"],
    "every folder under ops": ["ops"],
}


@pytest.mark.parametrize("paths", SECOND_PYTEST_STEPS.values(), ids=SECOND_PYTEST_STEPS.keys())
def test_a_second_pytest_step_in_another_lane_fails_both_steps_file_checks(paths):
    extra = {"name": "Extra", "run": ["uv", "run", "--frozen", "pytest", *paths], "lane": "web"}
    steps = [*gate_steps(), extra]

    assert steps_that_may_start_before_the_fixture_build(steps) == ["Extra"]
    assert any(count > 1 for count in gate_steps_per_test_folder(steps).values())


# A pytest-xdist group keeps its tests on one worker only under --dist loadgroup. Under
# --dist worksteal, which the gate's pytest steps use, a group mark does nothing.
GROUP_MARK = re.compile(r"\bmark\.xdist_group\(")


def marks_a_group(step):
    """Whether a test file a pytest step runs marks tests that must share one worker."""
    files = [file for path in paths_tested(step) for file in
             ([ROOT / path] if (ROOT / path).is_file() else (ROOT / path).rglob("*.py"))]
    return any(GROUP_MARK.search(file.read_text()) for file in files)


def test_a_pytest_step_whose_tests_must_share_a_worker_runs_with_loadgroup():
    steps = [step for step in gate_steps() if "pytest" in step["run"]]

    unkept = [step["name"] for step in steps if marks_a_group(step) and "loadgroup" not in step["run"]]

    assert steps and unkept == []


def test_the_group_check_finds_a_group_mark_in_a_test_file(tmp_path, monkeypatch):
    monkeypatch.setattr(sys.modules[__name__], "ROOT", tmp_path)
    # Joined here, so this file never holds the mark it looks for and the check above never finds it.
    mark = "@pytest.mark." + "xdist_group('port')"
    write(tmp_path, "suite/test_alone.py", f"import pytest\n\n{mark}\ndef test_x():\n    pass\n")
    write(tmp_path, "other/test_free.py", "def test_y():\n    pass\n")

    assert marks_a_group({"run": ["pytest", "--dist", "worksteal", "suite"]})
    assert not marks_a_group({"run": ["pytest", "--dist", "worksteal", "other"]})


# The web lanes. Each builds the app and the gallery into a folder of its own under web/, which
# STRATA_WEB_OUT names (web/out-dirs.ts; web/dist when it is unset), and runs its share of the
# Playwright tests against that build, so no lane serves files that another lane is rebuilding.

def web_script(step):
    """The script in web/package.json that a step runs with npm, such as "build" or "test", or None."""
    argv = step["run"]
    if not {"npm", "run", "--prefix"} <= set(argv) or argv[argv.index("--prefix") + 1] != "web":
        return None
    return next((arg for arg in argv[argv.index("run") + 1:] if not arg.startswith("-")), None)


def web_folder(step):
    """The folder under web/ that a web step builds into or serves."""
    named = [arg.split("=", 1)[1] for arg in step["run"] if arg.startswith("STRATA_WEB_OUT=")]
    return named[0] if named else "dist"


def shard(step):
    """The share of the Playwright tests a step runs, as (current, total); (1, 1) is every test."""
    for arg in step["run"]:
        if arg.startswith("--shard="):
            current, total = arg.removeprefix("--shard=").split("/")
            return int(current), int(total)
    return 1, 1


def web_build_problems(steps):
    """What would let a Playwright run test files it did not build: a lane whose web steps name two
    folders, a lane that runs the tests before it builds the app and the gallery, or two lanes that
    build into one folder."""
    lanes = {}
    for step in steps:
        if web_script(step) in ("build", "build:gallery", "test"):
            lanes.setdefault(step.get("lane"), []).append(step)
    problems, owner = [], {}
    for lane, found in lanes.items():
        folders = sorted({web_folder(step) for step in found})
        if len(folders) > 1:
            problems.append(f"the {lane} lane names {', '.join(folders)}")
        for folder in folders:
            if folder in owner:
                problems.append(f"the {owner[folder]} and {lane} lanes both build {folder}")
            owner[folder] = lane
        scripts = [web_script(step) for step in found]
        if "test" in scripts:
            tests_at = scripts.index("test")
            problems += [f"the {lane} lane tests before {build}" for build in ("build", "build:gallery")
                         if build not in scripts[:tests_at]]
    return problems


def shard_problems(steps):
    """What would leave a Playwright test out or run it twice: shards that do not count 1 to N once
    each, or two shards in one lane, where they would take turns instead of running side by side."""
    found = [step for step in steps if web_script(step) == "test"]
    shards = sorted(shard(step) for step in found)
    total = shards[-1][1] if shards else 0
    problems = []
    if shards != [(current, total) for current in range(1, total + 1)]:
        problems.append(f"the shards are {', '.join(f'{c}/{t}' for c, t in shards) or 'missing'}")
    if len({step.get("lane") for step in found}) < len(found):
        problems.append("two shards share a lane")
    return problems


def test_each_web_lane_tests_the_app_and_gallery_it_built_in_a_folder_of_its_own():
    steps = gate_steps()

    assert len([step for step in steps if web_script(step) == "test"]) >= 2
    assert web_build_problems(steps) == []


def test_the_playwright_shards_run_every_test_once_in_lanes_side_by_side():
    assert shard_problems(gate_steps()) == []


def in_web_2(script=None):
    """Picks the web-2 lane's steps, or only the one that runs this npm script."""
    return lambda step: step.get("lane") == "web-2" and script in (None, web_script(step))


def edit(steps, find, change):
    """A copy of the steps, with change applied to a copy of each step that find picks."""
    return [change(dict(step)) if find(step) else step for step in steps]


def without(steps, find):
    return [step for step in steps if not find(step)]


def renamed(folder):
    return lambda step: step | {"run": [f"STRATA_WEB_OUT={folder}" if arg.startswith("STRATA_WEB_OUT=") else arg
                                        for arg in step["run"]]}


def resharded(spec):
    return lambda step: step | {"run": [spec if arg.startswith("--shard=") else arg for arg in step["run"]]}


# Edits to the steps file that the two checks above must catch, each with the check that catches it.
BAD_WEB_EDITS = {
    "both lanes build into one folder":
        (lambda steps: edit(steps, in_web_2(), renamed("dist-1")), web_build_problems),
    "a lane tests another lane's folder":
        (lambda steps: edit(steps, in_web_2("test"), renamed("dist-1")), web_build_problems),
    "a lane tests before it builds the gallery":
        (lambda steps: without(steps, in_web_2("build:gallery")), web_build_problems),
    "a shard left out":
        (lambda steps: without(steps, in_web_2("test")), shard_problems),
    "a shard run twice":
        (lambda steps: edit(steps, in_web_2(), resharded("--shard=1/2")), shard_problems),
    "a third shard that runs nowhere":
        (lambda steps: edit(steps, in_web_2(), resharded("--shard=2/3")), shard_problems),
    "both shards in one lane":
        (lambda steps: edit(steps, in_web_2(), lambda step: step | {"lane": "web-1"}), shard_problems),
}


@pytest.mark.parametrize("bad, check", BAD_WEB_EDITS.values(), ids=BAD_WEB_EDITS.keys())
def test_a_bad_edit_to_the_web_lanes_fails_its_check(bad, check):
    assert check(bad(gate_steps())) != []


# The screen tests run axe only through web/tests/axe.ts, whose scans cost about half of axe's default
# run and find the same violations (ticket 55). web/tests/axe.spec.ts compares the two, so it builds
# axe's default run as well.
AXE_RUNNERS = {"axe.ts", "axe.spec.ts"}
BUILDS_A_SCAN = re.compile(r"\bnew\s+AxeBuilder\b")


def own_axe_scans(web):
    """The test and capture files under web, other than the helper and its spec, that build an axe scan
    of their own."""
    return sorted(path.relative_to(web).as_posix() for folder in ("tests", "capture") for path in (web / folder).rglob("*.ts")
                  if path.name not in AXE_RUNNERS and BUILDS_A_SCAN.search(path.read_text()))


def test_every_axe_scan_in_the_screen_tests_runs_through_the_one_helper():
    assert own_axe_scans(ROOT / "web") == []


def test_the_axe_check_finds_a_spec_that_builds_its_own_scan(tmp_path):
    write(tmp_path, "tests/axe.ts", "export const scan = (page) => new AxeBuilder({ page }).analyze();\n")
    write(tmp_path, "tests/page.spec.ts", "const results = await new AxeBuilder({ page }).analyze();\n")
    write(tmp_path, "tests/other.spec.ts", "const results = await scan(page);\n")

    assert own_axe_scans(tmp_path) == ["tests/page.spec.ts"]


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
