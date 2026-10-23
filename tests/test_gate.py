"""The offline gate, tested the way it runs: as the pre-commit hook of a real git commit.

Each test builds a throwaway repo that holds this repo's hook and gate runner, with its own
list of steps, so a step can fail, sleep or plant a key without touching this repo.
"""

import os
import shutil
import subprocess
import sys
import textwrap
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


@pytest.fixture
def repo(tmp_path):
    """A repo with the gate installed and a first commit, ready for a steps file."""
    path = tmp_path / "repo"
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


def steps_file(limit=120, steps=()):
    """A steps file: the secret scan always runs, then the given test steps."""
    lines = [f"limit_seconds = {limit}", ""]
    lines += ["[[step]]", 'name = "Scan for secrets"',
              'run = ["python3", "gates/secret_scan.py"]', "always = true", "git_env = true", ""]
    for name, run in steps:
        lines += ["[[step]]", f'name = "{name}"', f"run = {run}", ""]
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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__]))
