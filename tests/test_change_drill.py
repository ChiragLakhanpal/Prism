"""The change drill's runbook (ticket 49): docs/change-drill.md has an entry for each drill in
config/change_drills.toml, in its order, and each entry names the same one place and the same proving test, so the
runbook cannot define the ten places a second time (CLAUDE.md rule 4). Each entry also names the test in that file
that proves the change, and that test exists.
"""

import re
from pathlib import Path

from strata import config

ROOT = Path(__file__).resolve().parents[1]
RUNBOOK = ROOT / "docs" / "change-drill.md"


def entries(text: str) -> dict[str, str]:
    """Each drill's entry, by its heading's change: '## 3. Change a signal threshold'."""
    parts = re.split(r"^## (\d+)\. (.+)$", text, flags=re.M)
    return {parts[i + 1].strip(): parts[i + 2] for i in range(1, len(parts) - 2, 3)}


def named_test(entry: str) -> tuple[str, str]:
    """The proving test's file and the test's name, from '- **Proved by.** `file`, `test`'."""
    found = re.search(r"^- \*\*Proved by\.\*\* `([^`]+)`, `([^`]+)`", entry, flags=re.M)
    assert found, "an entry needs a line: - **Proved by.** `file`, `test name`"
    return found.group(1), found.group(2)


def test_the_runbook_has_an_entry_for_each_drill_in_the_registry_s_order():
    drills = config.load_change_drills()

    assert list(entries(RUNBOOK.read_text())) == [drill.change for drill in drills]


def test_each_entry_names_the_registry_s_one_place_and_proving_test_and_that_test_exists():
    found = entries(RUNBOOK.read_text())
    for drill in config.load_change_drills():
        entry = found[drill.change]
        assert re.search(rf"^- \*\*The one place\.\*\* `{re.escape(drill.place)}`$", entry, flags=re.M), drill.change
        file, test = named_test(entry)
        assert file == drill.proved_by, drill.change
        source = (ROOT / file).read_text()
        if file.endswith(".py"):
            assert re.search(rf"^def {re.escape(test)}\(", source, flags=re.M), f"{file} has no test {test}"
        else:
            assert f'test("{test}"' in source or f"test(`{test}`" in source, f"{file} has no test {test}"


def test_each_entry_gives_its_steps_and_the_live_part_left_for_the_workspace():
    for change, entry in entries(RUNBOOK.read_text()).items():
        assert "**Steps.**" in entry, change
        assert re.search(r"^1\. ", entry, flags=re.M), change
        assert "**On the workspace.**" in entry, change
