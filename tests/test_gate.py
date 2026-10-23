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
    """The environment without git's hook variables, so nested git calls act on their own repo."""
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


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
    for name in ("offline.py", "secrets.py"):
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
              'run = ["python3", "gates/secrets.py"]', "always = true", "git_env = true", ""]
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
    assert "Run the checks" in blocked.stdout + blocked.stderr
    assert "The total is 3, not 4." in blocked.stdout + blocked.stderr

    write(repo, "check.py", "print('The total is 4.')\n")
    git(repo, "add", "-A")

    passed = commit(repo)

    assert passed.returncode == 0, passed.stdout + passed.stderr
    assert head_count(repo) == 2


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


def test_a_step_that_makes_its_own_repo_leaves_the_commit_alone(repo):
    nested = textwrap.dedent("""\
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as tmp:
            def git(*args):
                subprocess.run(["git", "-C", tmp, "-c", "user.name=n", "-c", "user.email=n@example.org", *args],
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
