"""The live scripts as the first live runs met them (ticket 66): what each script installs, and the services its
readers and tools reach, proven offline with stand-ins for the network.

The live agent's scripts (ops/agent/refuse_live.py, ops/agent/ask_live.py) run the app's /api/ask stream, which
detects the question's language with py3langid (src/strata/knowledge/language.py), so each script's inline
dependency list must name it at the pin pyproject.toml holds: `uv run --script` installs only what that list names.
"""

import re
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
ANSWER_STREAM_SCRIPTS = ("ops/agent/refuse_live.py", "ops/agent/ask_live.py")


def inline_dependencies(path: Path) -> list[str]:
    """The dependencies a script's inline metadata block (# /// script ... # ///) names, as uv reads them."""
    block = re.search(r"^# /// script\n(.*?)^# ///$", path.read_text(), re.S | re.M).group(1)
    return tomllib.loads("".join(line.removeprefix("#").removeprefix(" ") + "\n"
                                 for line in block.splitlines()))["dependencies"]


def pinned(name: str) -> str:
    """The project's pin for a package, from pyproject.toml."""
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    return next(entry for entry in project["dependencies"] if entry.split("==")[0] == name)


@pytest.mark.parametrize("script", ANSWER_STREAM_SCRIPTS)
def test_a_script_that_runs_the_answer_stream_installs_the_language_detector(script):
    assert pinned("py3langid") in inline_dependencies(ROOT / script)
