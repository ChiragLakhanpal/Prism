"""The proposal's command (ticket 46). Run it from the repo's root:

    uv run python -m strata.proposal build      docs/proposal.md and its figures, from docs/proposal/snapshot.json
    uv run python -m strata.proposal check      what the gate checks on every commit, Markdown included
    uv run python -m strata.proposal readme     print the README's links for the panel; --write writes them
    uv run python -m strata.proposal pull --database data/out/fixture.duckdb --out /tmp/snapshot.json
                                                a snapshot from a DuckDB file, to try the build on this computer

The real snapshot comes from the workspace (ops/proposal/pull_live.py), never from the fixture: the fixture's numbers
are not findings (the spec, "Wireframe numbers"), so a snapshot pulled from a DuckDB file must go to a path you name.
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from strata.config import ConfigError, load_urls
from strata.proposal import build as builder
from strata.proposal import numbers, readme, register, snapshot

ROOT = Path(__file__).resolve().parents[3]
PROPOSAL = ROOT / "docs" / "proposal.md"
SOURCE = builder.SOURCE_FILE
PLACEHOLDER = re.compile(r"\{([rs]):([^{}|\\]+)(?:\\?\|[^{}]*)?\}")
CONDITION = re.compile(r"\{when:(?:un)?measured:([^{}]+)\}")


def _commit() -> str:
    found = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True)
    return found.stdout.strip() or "unknown"


def lint(path: Path) -> list[str]:
    """The proposal's copy lint (web/lint/proposal.ts) on one file: a line per problem."""
    found = subprocess.run(["node", str(ROOT / "web" / "lint" / "proposal.ts"), str(path)], capture_output=True,
                           text=True)
    return [line for line in found.stdout.splitlines() if line.strip()]


def source_problems(source: str) -> list[str]:
    """What the gate checks in docs/proposal/source.md: each {r:}, {s:} and {when:measured:} names a register entry,
    and every other number is excepted, since a typed number has no source."""
    results, settings = register.load_results(), register.load_settings()
    problems = []
    for kind, key in PLACEHOLDER.findall(source):
        if kind == "r" and key not in results:
            problems.append(f"docs/proposal/source.md cites the result {key}, which is not in "
                            "docs/proposal/results.toml.")
        if kind == "s" and key not in settings:
            problems.append(f"docs/proposal/source.md cites the setting {key}, which is not in "
                            "docs/proposal/settings.toml.")
    for key in CONDITION.findall(source):
        if key not in results:
            problems.append(f"docs/proposal/source.md keeps a line on the result {key}, which is not in "
                            "docs/proposal/results.toml.")
    sourced = re.sub(r"\{[rs]:[^{}]*\}", "[0](#r-placeholder)", source)
    unsourced = re.sub(r"\{(?:#|[a-z¶]+:)[^{}]*\}|\{[a-z-]+(?::[a-z-]+)?\}", " ", sourced)
    problems += [found.sentence() for found in numbers.unsourced(unsourced)]
    return problems


def register_problems() -> list[str]:
    """Each register entry points at a file that exists."""
    problems = []
    for key, result in register.load_results().items():
        if not (ROOT / result.query_file).exists():
            problems.append(f"Result {key}'s query, {result.query_file}, does not exist.")
        if result.meta and not (ROOT / "src" / "strata" / "proposal" / "sql" / result.meta).exists():
            problems.append(f"Result {key}'s meta query, {result.meta}, does not exist.")
        if result.target and result.target not in register.load_settings():
            problems.append(f"Result {key}'s target, {result.target}, is not in docs/proposal/settings.toml.")
    for key, setting in register.load_settings().items():
        if setting.enforced_by and not (ROOT / setting.enforced_by).exists():
            problems.append(f"Setting {key} is enforced by {setting.enforced_by}, which does not exist.")
    return problems


def proposal_problems(text: str) -> list[str]:
    """What the gate checks in a built docs/proposal.md: the number check, paragraphs numbered without gaps, and
    every in-page link reaching an anchor."""
    problems = [found.sentence() for found in numbers.unsourced(text)]
    numbered = [int(n) for n in re.findall(r'<a id="p(\d+)"></a>', text)]
    if numbered != list(range(1, len(numbered) + 1)):
        problems.append("The proposal's paragraph numbers do not run from 1 without gaps. Build it again.")
    anchors = set(re.findall(r'<a id="([^"]+)"></a>', text))
    for target in sorted(set(re.findall(r'\]\(#([^)\s"]+)', text) + re.findall(r'href="#([^"]+)"', text))):
        if target not in anchors:
            problems.append(f"The proposal links to {target}, which is not in the proposal.")
    return problems


def check() -> int:
    problems = register_problems() + source_problems(SOURCE.read_text())
    if PROPOSAL.exists():
        problems += proposal_problems(PROPOSAL.read_text())
    found = readme.problem()
    if found:
        problems.append(found)
    for problem in problems:
        print(problem)
    return 1 if problems else 0


def build(args) -> int:
    path = Path(args.snapshot)
    if not path.exists():
        print(f"The proposal did not build. There is no snapshot at {path}. Pull one from the workspace with "
              "uv run --script ops/proposal/pull_live.py, which writes docs/proposal/snapshot.json.")
        return 1
    try:
        built = builder.build(SOURCE.read_text(), builder.Inputs(snapshot=snapshot.read(path), commit=_commit()))
    except (builder.BuildError, ConfigError, register.RegisterError) as error:
        print(error)
        return 1
    with tempfile.TemporaryDirectory() as folder:
        trial = Path(folder) / "proposal.md"
        trial.write_text(built.markdown)
        problems = lint(trial)
    if problems:
        print("The proposal did not build. Its copy lint found:")
        print("\n".join(problems))
        return 1
    out = Path(args.out)
    builder.write(built, out)
    print(f"Wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} and {len(built.figures)} figures.")
    return 0


def pull(args) -> int:
    from strata.lakehouse.engine import DuckDBEngine

    out = Path(args.out).resolve()
    if out == snapshot.SNAPSHOT_FILE.resolve():
        print("A snapshot from a DuckDB file holds no findings, so it never goes to docs/proposal/snapshot.json. "
              "Name another path, or pull from the workspace with ops/proposal/pull_live.py.")
        return 1
    with DuckDBEngine.open(args.database, read_only=True) as engine:
        found = snapshot.pull(engine, dt.date.today(), source=str(args.database))
    snapshot.write(found, out)
    missing = [key for key, result in found["results"].items() if not result["measured"]]
    print(f"Wrote {out}. Not measured: {', '.join(missing) or 'none'}.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m strata.proposal", description=__doc__.split("\n\n")[0])
    commands = parser.add_subparsers(dest="command", required=True)
    making = commands.add_parser("build", help="build docs/proposal.md and its figures from the snapshot")
    making.add_argument("--snapshot", default=str(snapshot.SNAPSHOT_FILE))
    making.add_argument("--out", default=str(PROPOSAL))
    commands.add_parser("check", help="what the gate checks: the source, the built proposal and the README's links")
    links = commands.add_parser("readme", help="the README's links for the panel, from config/urls.toml")
    links.add_argument("--write", action="store_true")
    pulling = commands.add_parser("pull", help="a snapshot from a DuckDB file, to a path you name")
    pulling.add_argument("--database", required=True)
    pulling.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    if args.command == "check":
        return check()
    if args.command == "build":
        return build(args)
    if args.command == "pull":
        return pull(args)
    if args.write:
        readme.write(load_urls())
        print("Wrote README.md's links for the panel.")
    else:
        print(readme.links(load_urls()), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
