"""run-probes.sh runs every probe once, in order, with the env file, and goes on after a failure.

Each probe also runs alone with one command, and --dry-run runs it with canned answers and no
network. Both are checked here with the standard library only: the probes import the
Databricks SDK only inside their live adapters.
"""

import os
import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
DAYONE = REPO / "ops" / "dayone"
RUNNER = DAYONE / "run-probes.sh"
PROBES = ["probe_caps.py", "probe_genie.py", "probe_hosts.py", "probe_traces.py", "probe_azure_from_job.py",
          "probe_parse_pad.py", "probe_ai_search.py"]

FAKE_UV = r"""#!/bin/bash
echo "uv $*" >> "$FAKE_LOG"
case "$*" in *"$FAKE_FAILS"*) exit 1 ;; esac
"""


@pytest.fixture
def fake_uv(tmp_path):
    (tmp_path / "bin").mkdir()
    (tmp_path / "bin" / "uv").write_text(FAKE_UV)
    (tmp_path / "bin" / "uv").chmod(0o755)
    return tmp_path


def run_runner(place, *args, fails="nothing-fails"):
    env = {"PATH": f"{place / 'bin'}:{os.environ['PATH']}", "FAKE_LOG": str(place / "uv.log"), "FAKE_FAILS": fails}
    return subprocess.run(["bash", str(RUNNER), *args], env=env, capture_output=True, text=True, timeout=60)


def test_the_runner_passes_a_shell_syntax_check():
    done = subprocess.run(["bash", "-n", str(RUNNER)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr


def test_the_runner_runs_every_probe_once_in_order_with_the_env_file(fake_uv):
    done = run_runner(fake_uv, "--env-file", "/somewhere/main.env")
    assert done.returncode == 0, done.stdout + done.stderr
    calls = (fake_uv / "uv.log").read_text().splitlines()
    assert [re.search(r"probe_\w+\.py", call).group(0) for call in calls] == PROBES
    assert all(call.startswith("uv run --script ") and call.endswith("--env-file /somewhere/main.env")
               for call in calls)


def test_the_runner_goes_on_after_a_failed_probe_and_says_so(fake_uv):
    done = run_runner(fake_uv, "--env-file", "/somewhere/main.env", fails="probe_hosts.py")
    assert done.returncode == 1
    assert len((fake_uv / "uv.log").read_text().splitlines()) == len(PROBES)
    assert "probe_hosts.py" in done.stdout



def test_a_dry_run_says_it_wrote_nothing(fake_uv):
    done = run_runner(fake_uv, "--dry-run")
    assert done.returncode == 0, done.stdout + done.stderr
    assert "dry run" in done.stdout.splitlines()[-1]
    assert "The results are in" not in done.stdout

def test_the_runner_needs_an_env_file(fake_uv):
    done = run_runner(fake_uv)
    assert done.returncode == 2
    assert "--env-file" in done.stdout + done.stderr
    assert not (fake_uv / "uv.log").exists()


@pytest.mark.parametrize("probe", PROBES + ["dayone.py", "live.py", "workspace/reach_hosts.py",
                                            "workspace/azure_from_job.py", "workspace/probe_app/app.py"])
def test_every_python_file_compiles(probe, tmp_path):
    py_compile.compile(str(DAYONE / probe), cfile=str(tmp_path / "compiled.pyc"), doraise=True)


@pytest.mark.parametrize("probe", PROBES)
def test_every_probe_dry_runs_with_one_command_and_writes_nothing(probe, tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(REPO / "docs" / "day-one-results.md", results)
    done = subprocess.run([sys.executable, str(DAYONE / probe), "--dry-run", "--results", str(results)],
                          capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stdout + done.stderr
    assert "dry run, so I wrote nothing" in done.stdout
    assert results.read_text() == (REPO / "docs" / "day-one-results.md").read_text()


def test_every_probe_declares_its_dependencies_inline_for_uv():
    for probe in PROBES:
        head = (DAYONE / probe).read_text().split('"""', 1)[0]
        assert "# /// script" in head and "# dependencies = [" in head and "# ///" in head, probe


def test_every_command_in_the_results_document_names_a_file_that_exists():
    text = (REPO / "docs" / "day-one-results.md").read_text()
    commands = re.findall(r"^(?:Command: `|    )((?:bash|uv run --script) [^`\n]+)", text, re.M)
    assert len(commands) >= 12
    for command in commands:
        script = next(word for word in command.split() if word.startswith("ops/"))
        assert (REPO / script).is_file(), f"{command} names {script}, which does not exist"
