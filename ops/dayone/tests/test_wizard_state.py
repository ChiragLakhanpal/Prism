"""The wizard's one read of its settings and the results document (ticket 56).

A run of the wizard started about 78 Python processes, one for each setting, model name and status it
showed, and 21 runs in ops/wizard/tests started 1,637, which held the ops lane up on a busy computer. Now
the wizard starts dayone.py once with `state`, which writes the results document if it is missing and
prints every value as a bash assignment. These tests check that the wizard's own lookups read back, for
every setting and model it names, what `get` and `model` print, and for every block, what `field` and
`payg-done` say.
"""

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DAYONE = REPO / "ops" / "dayone" / "dayone.py"
WIZARD = REPO / "ops" / "wizard" / "strata-setup.sh"
sys.path.insert(0, str(DAYONE.parent))

import dayone  # noqa: E402

# The wizard's lookups, each written on one line so a test can run it without running the wizard.
LOOKUPS = ("setting", "model_value", "test_status", "payg_done")


def lookups():
    found = {name: re.search(rf"^{name}\(\) {{.*}}$", WIZARD.read_text(), re.M) for name in LOOKUPS}
    assert all(found.values()), [name for name, line in found.items() if not line]
    return "\n".join(line[0] for line in found.values())


def what_the_wizard_reads():
    """The settings and model values the wizard shows, as it names them in its text."""
    text = WIZARD.read_text()
    settings = sorted(set(re.findall(r"\$\(setting ([a-z0-9_.]+)\)", text)))
    models = sorted(set(re.findall(r"\$\(model_value ([a-z]+(?: dimensions)?)\)", text)))
    assert len(settings) > 20 and len(models) >= 5, (settings, models)
    return settings, models


def printed(capsys, argv):
    """What one dayone.py command prints, run in this process, and its exit code."""
    code = dayone.main(argv)
    return capsys.readouterr().out.rstrip("\n"), code


def through_the_wizard(results, calls):
    """Each call's output through the wizard's lookups, after one `state` run, in a single bash."""
    state = subprocess.run([sys.executable, str(DAYONE), "--results", str(results), "state"],
                           capture_output=True, text=True, check=True).stdout
    script = "\n".join([state, lookups(), *(f"printf '%s\\0' \"$({call})\"" for call in calls)])
    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True, check=True)
    return dict(zip(calls, done.stdout.split("\0")))


def test_one_state_run_gives_the_wizard_every_setting_and_model_it_shows(tmp_path, capsys):
    results = tmp_path / "results.md"
    settings, models = what_the_wizard_reads()
    calls = [f"setting {key}" for key in settings] + [f"model_value {model}" for model in models]

    seen = through_the_wizard(results, calls + ["setting payg.deadline_long"])

    for key in set(settings) - {"payg.deadline_long"}:
        assert seen[f"setting {key}"] == printed(capsys, ["get", key])[0], key
    for model in models:
        assert seen[f"model_value {model}"] == printed(capsys, ["model", *model.split()])[0], model
    # The credit's last day written out, as the wizard says it in stage 12.
    deadline = dayone.load_config()["payg"]["deadline"]
    assert seen["setting payg.deadline_long"] == dayone.long_date(dayone.parse_day(deadline))
    # Like init, state writes the results document when it is missing.
    assert dayone.read_results(results)["test-7"]["Status"] == "not run"


def test_the_state_carries_each_tests_status_and_whether_pay_as_you_go_is_done(tmp_path, capsys):
    results = tmp_path / "results.md"
    printed(capsys, ["--results", str(results), "init"])
    printed(capsys, ["--results", str(results), "record", "--test", "7", "--status", "passed", "--result", "It works.",
                     "--evidence", "databricks current-user me returned the user ID 42."])
    printed(capsys, ["--results", str(results), "payg", "--status", "done", "--who", "The subscription owner"])
    blocks = [f"test-{number}" for number in range(1, 11)]

    seen = through_the_wizard(results, [f"test_status {block[5:]}" for block in blocks] + ["payg_done && echo yes"])

    for block in blocks:
        assert seen[f"test_status {block[5:]}"] == printed(capsys, ["--results", str(results), "field", block, "Status"])[0]
    assert seen["test_status 7"] == "passed"
    assert seen["payg_done && echo yes"] == "yes"
    assert printed(capsys, ["--results", str(results), "payg-done"])[1] == 0


def test_a_setting_the_wizard_misnames_stops_it_with_one_sentence(tmp_path):
    state = subprocess.run([sys.executable, str(DAYONE), "--results", str(tmp_path / "results.md"), "state"],
                           capture_output=True, text=True, check=True).stdout
    script = "\n".join(["set -eu", state, lookups(), 'value=$(setting names.no_such_name)', 'echo "went on"'])

    done = subprocess.run(["bash", "-c", script], capture_output=True, text=True)

    assert done.returncode != 0
    assert "went on" not in done.stdout
    assert done.stderr.strip() == "dayone.toml has no setting named names.no_such_name."
