#!/usr/bin/env python3
"""Day-one tests: the results document, the shared settings and the .env reader.

The wizard calls this file with python3, the probes import it, and later tickets read the
results document through read_results() or path_kind(). It uses the standard library only,
so it runs anywhere Python 3.11 or later runs. The model deployments come from the model file,
config/models.toml, through strata.config.load_models(), which also uses only the standard library.

Commands:
  python3 ops/dayone/dayone.py init      Write the results document if it is missing.
  python3 ops/dayone/dayone.py record --test N --status STATUS --result TEXT [--evidence TEXT ...]
  python3 ops/dayone/dayone.py payg --status done|planned --who TEXT [--due YYYY-MM-DD]
  python3 ops/dayone/dayone.py payg-done Exit 0 when the subscription has moved to pay-as-you-go.
  python3 ops/dayone/dayone.py get caps.monthly_budget_usd
  python3 ops/dayone/dayone.py model agent             The agent role's deployment, from config/models.toml.
  python3 ops/dayone/dayone.py model embed dimensions  The embedding size.
  python3 ops/dayone/dayone.py field test-6 Status
  python3 ops/dayone/dayone.py show      Print each test's status and chosen path.

Each command takes --results PATH to work on a copy instead of the main checkout's document.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import subprocess
import sys
import tempfile
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
CONFIG_PATH = HERE / "dayone.toml"
SRC = HERE.parents[1] / "src"

# "waiting" means part of the test ran and the rest waits for something, such as the app.
STATUSES = ("not run", "waiting", "passed", "partly", "failed")
BLOCK = re.compile(r"<!-- dayone:(?P<id>[\w-]+) -->\n(?P<body>.*?)<!-- /dayone:(?P=id) -->", re.S)
FIELD = re.compile(r"^- (?P<name>[^:]+):(?: (?P<value>.*))?$")


class DayOneError(Exception):
    """A request the results document cannot take, with a reason a person can act on."""


@dataclass
class Outcome:
    """What one run of a test found."""

    status: str
    result: str
    evidence: list[str] = field(default_factory=list)
    path: str | None = None  # a chosen path that differs from the one the status implies


# ── Settings and places ──────────────────────────────────────────────────

BUDGET_PATH = HERE.parents[1] / "config" / "budget.toml"


def load_config(path: Path = CONFIG_PATH) -> dict:
    """dayone.toml, with the budget's values from config/budget.toml, their one home (ticket 45): the daily cost
    pull runs on the workspace, where only src and config are synced, so the budget lives there and the wizard
    and the probes read it under the names they always used."""
    with open(path, "rb") as handle:
        config = tomllib.load(handle)
    with open(BUDGET_PATH, "rb") as handle:
        budget = tomllib.load(handle)
    config.setdefault("payg", {}).update(deadline=budget["credit"]["ends_on"].isoformat(),
                                         credit_usd=budget["credit"]["usd"])
    config.setdefault("caps", {}).update(monthly_budget_usd=budget["monthly"]["usd"],
                                         budget_alert_percents=budget["monthly"]["alert_percents"],
                                         budget_forecast_percent=budget["monthly"]["forecast_percent"])
    config.setdefault("names", {}).update(budget=budget["monthly"]["name"],
                                          resource_group=budget["pull"]["resource_group"])
    return config


def models() -> dict:
    """Each model role's deployment, read from config/models.toml through strata.config.load_models().

    The model file is the one place that names a deployment (spec, "Ten single places"), so the
    wizard and the probes ask it here instead of keeping their own names.
    """
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    from strata.config import ConfigError, load_models

    try:
        return load_models()
    except ConfigError as error:
        raise DayOneError(str(error)) from error


def config_value(config: dict, dotted: str):
    value = config
    for part in dotted.split("."):
        if not isinstance(value, dict) or part not in value:
            raise DayOneError(f"dayone.toml has no setting named {dotted}.")
        value = value[part]
    return value


def main_checkout(start: Path = HERE) -> Path:
    """The main checkout's root, also when this file runs from a worktree."""
    try:
        done = subprocess.run(["git", "-C", str(start), "rev-parse", "--path-format=absolute", "--git-common-dir"],
                              capture_output=True, text=True, check=True, timeout=10)
        return Path(done.stdout.strip()).parent
    except (OSError, subprocess.SubprocessError):
        return HERE.parents[1]


def default_results_path(config: dict | None = None) -> Path:
    """The results document in the checkout this file lives in, so results travel with the branch."""
    config = config or load_config()
    return HERE.parents[1] / config["results_document"]


def default_env_path() -> Path:
    """The main checkout's .env: secrets live only there (CLAUDE.md rule 7)."""
    return main_checkout() / ".env"


def load_env(path: Path) -> dict[str, str]:
    """Read KEY=VALUE lines the way the wizard writes them, without printing anything."""
    values: dict[str, str] = {}
    for raw in Path(path).read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.removeprefix("export ").strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] == "'":
            value = value[1:-1].replace("'\\''", "'")
        elif len(value) >= 2 and value[0] == value[-1] == '"':
            value = value[1:-1]
        values[key] = value
    return values


def missing_keys(env: dict[str, str], keys) -> list[str]:
    return [key for key in keys if not env.get(key)]


NUMBER_WORDS = ("no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")


def count_words(count: int, noun: str, plural: str | None = None) -> str:
    """A count such as "four alerts" or "12 alerts": words up to nine, numerals from 10 (DESIGN.md 7, item 12)."""
    number = NUMBER_WORDS[count] if 0 <= count <= 9 else f"{count:,}"
    return f"{number} {noun if count == 1 else plural or noun + 's'}"


def long_date(day: dt.date) -> str:
    return f"{day:%B} {day.day}, {day.year}"


def parse_day(text: str) -> dt.date:
    try:
        return dt.date.fromisoformat(text)
    except ValueError as error:
        raise DayOneError(f"{text} is not a date in the form YYYY-MM-DD.") from error


def optional_day(text: str | None) -> dt.date | None:
    """A typed date, or None when none was typed. main parses dates itself, so a bad one gets one sentence."""
    return parse_day(text) if text else None


# ── Paths the build takes ────────────────────────────────────────────────

NO_GAP_FILL = "Undecided. PLAN.md section 14 names no gap fill for this test, so the user decides."


def chosen_path(test: dict, status: str) -> str:
    if status == "not run":
        return f"Default, until a result says otherwise. {test['default_path']}"
    if status == "waiting":
        return f"Default, until the rest of this test runs. {test['default_path']}"
    if status == "passed":
        return f"Default. {test['default_path']}"
    if test["gap_fill"]:
        return f"Gap fill. {test['gap_fill']}"
    return NO_GAP_FILL


def path_kind(number: int, results: Path | None = None) -> str:
    """For later tickets: "default", "gap fill" or "undecided" for one test."""
    fields = read_results(results or default_results_path())[f"test-{number}"]
    return fields["Chosen path"].split(".", 1)[0].split(",", 1)[0].lower()


# ── The document ─────────────────────────────────────────────────────────

def render_fields(fields: list[tuple[str, str | list[str]]]) -> str:
    lines = []
    for name, value in fields:
        if isinstance(value, list):
            lines.append(f"- {name}:")
            lines.extend(f"  - {one_line(item)}" for item in value)
        else:
            lines.append(f"- {name}: {one_line(value)}")
    return "\n".join(lines) + "\n"


def one_line(text: str) -> str:
    return " ".join(str(text).split())


def test_fields(test: dict, outcome: Outcome, day: dt.date | None) -> list[tuple[str, str | list[str]]]:
    return [
        ("Status", outcome.status),
        ("Result", outcome.result),
        ("Evidence", outcome.evidence or ["None yet. The command above fills it."]),
        ("Chosen path", outcome.path or chosen_path(test, outcome.status)),
        ("Last run", long_date(day) if day else "never"),
    ]


NOT_RUN = Outcome("not run", "Not run yet, because it needs the wizard first.")


def summary_table(config: dict, blocks: dict[str, dict]) -> str:
    rows = ["| Test | What it checks | Status | Chosen path |", "|---|---|---|---|"]
    for number, test in sorted(config["tests"].items(), key=lambda item: int(item[0])):
        fields = blocks.get(f"test-{number}", {})
        kind = fields.get("Chosen path", "Default").split(".", 1)[0].split(",", 1)[0]
        rows.append(f"| {number} | {test['title']} | {fields.get('Status', 'not run')} | {kind} |")
    return "\n".join(rows) + "\n"


def payg_fields(config: dict, status: str, day: dt.date | None, who: str | None = None) -> list:
    deadline = long_date(parse_day(config["payg"]["deadline"]))
    return [
        ("Step", "Move the Azure subscription from the free credit to pay-as-you-go."),
        ("Deadline", f"Before {deadline}, when the free credit ends."),
        ("Who", who or config["payg"]["who"]),
        ("Status", status),
        ("Last updated", long_date(day) if day else "never"),
    ]


def caps_fields_not_checked() -> list:
    return [
        ("Status", "not checked"),
        ("Deployments", ["None checked yet. The command above fills this in."]),
        ("Budget", "Not checked yet."),
        ("Subscription offer", "Not checked yet."),
        ("Last checked", "never"),
    ]


def block(block_id: str, body: str) -> str:
    return f"<!-- dayone:{block_id} -->\n{body}<!-- /dayone:{block_id} -->"


def render_document(config: dict) -> str:
    deadline = long_date(parse_day(config["payg"]["deadline"]))
    parts = [
        "# Day-one results\n",
        "This document records what the day-one tests in PLAN.md section 14 found, and the path the build "
        "takes for each one. A later ticket that depends on a test reads its \"Chosen path\" line, or calls "
        "`path_kind()` in `ops/dayone/dayone.py`. Only the wizard and the probes change the marked "
        "blocks.\n",
        "## Run the wizard first\n",
        "The owner of the Databricks workspace and the Azure subscription runs the wizard first, in their "
        "own terminal, from the main checkout:\n",
        "    bash ops/wizard/strata-setup.sh\n",
        "The wizard fills `.env`, saves the app's secrets in the Databricks secret scope "
        f"`{config['names']['secret_scope']}`, walks through the Azure caps and the budget, and answers "
        "tests 6, 7, 8 and 9. Its last stage offers to run the probes, which answer tests 1, 2, 3, 4, 5 "
        "and 10 and read the caps behind test 8. To run all the probes later, run this from the main "
        "checkout:\n",
        "    bash ops/dayone/run-probes.sh --env-file .env\n",
        "Each probe also runs alone, with the command under its test. Every probe writes its result into "
        "this document, so commit the document on build/strata after a run.\n",
        "## Summary\n",
        block("summary", summary_table(config, {})) + "\n",
        "## Pay-as-you-go\n",
        f"The free Azure credit of about US${config['payg']['credit_usd']} ends on {deadline}. The subscription "
        "moves to pay-as-you-go "
        "before then (PLAN.md section 2). The last Azure stage of the wizard records who takes this step "
        "and when.\n",
        block("payg", render_fields(payg_fields(config, "Not done yet.", None))) + "\n",
        "## Azure caps and budget\n",
        "Budgets only send email, so hard caps stop the spend: a tokens-per-minute limit on each model "
        "deployment, and a daily cap on Application Insights. The probe reads each deployment's limit, the "
        "budget and its notifications, and the subscription's offer. The caps themselves are set in "
        "`ops/dayone/dayone.toml`.\n",
        "Command: `uv run --script ops/dayone/probe_caps.py --env-file .env`\n",
        block("caps", render_fields(caps_fields_not_checked())) + "\n",
        "## The ten tests\n",
    ]
    for number, test in sorted(config["tests"].items(), key=lambda item: int(item[0])):
        if_fails = test["gap_fill"] or "PLAN.md section 14 names no gap fill, so the user decides."
        parts += [
            f"### Test {number}. {test['title']}\n",
            f"{test['question']}\n",
            f"- If it passes: {test['default_path']}\n- If it fails: {if_fails}\n",
            f"Command: `{test['command']}`\n",
            block(f"test-{number}", render_fields(test_fields(test, NOT_RUN, None))) + "\n",
        ]
    return "\n".join(parts + left_in_workspace(config))


def last_part(name: str) -> str:
    return name.rsplit(".", 1)[-1]


def left_in_workspace(config: dict) -> list[str]:
    names = config["names"]
    return [
        "## What the probes leave in the workspace\n",
        "The probes make these things and leave them in place. Most of them make a second run quicker. They "
        "change nothing else in the workspace.\n",
        f"- The app `{names['app']}`, which runs the probe app until the app shell ticket deploys Strata "
        "over it.\n"
        f"- The folder `{names['workspace_folder']}` in your user folder, with the code that the jobs and the "
        "app run.\n"
        f"- The schema `{names['schema']}`, with the volume `{last_part(names['volume'])}` for the PAD, the table "
        f"`{last_part(names['search_table'])}` and the index `{last_part(names['search_index'])}`.\n"
        f"- The AI Search endpoint `{names['ai_search_endpoint']}`, which Strata keeps for its own index.\n"
        "- One-time job runs whose names start with `strata-dayone`, in the workspace's job run history.\n"
        f"- A conversation in the Genie space that GENIE_SPACE_ID names, which asks \"{config['genie']['question']}\"\n"
        f"- Read access for the app `{names['app']}` to the secret scope `{names['secret_scope']}`. The app reads "
        "only `APPLICATIONINSIGHTS_CONNECTION_STRING`, but Databricks grants access to the whole scope, which also "
        "holds `AZURE_OPENAI_API_KEY`.\n",
    ]


def read_results(path: Path) -> dict[str, dict]:
    """Every marked block except the summary, as {block id: {field: text or list of lines}}."""
    return parse_blocks(Path(path).read_text())


def parse_blocks(text: str) -> dict[str, dict]:
    blocks = {}
    for match in BLOCK.finditer(text):
        if match["id"] == "summary":
            continue
        fields: dict[str, str | list[str]] = {}
        current = None
        for line in match["body"].splitlines():
            found = FIELD.match(line)
            if found:
                current = found["name"]
                fields[current] = found["value"] or []
            elif line.startswith("  - ") and isinstance(fields.get(current), list):
                fields[current].append(line[4:])
        blocks[match["id"]] = fields
    return blocks


def write_atomically(path: Path, text: str) -> None:
    path = Path(path)
    handle, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    with os.fdopen(handle, "w") as out:
        out.write(text)
    os.replace(temporary, path)


def ensure_document(path: Path, config: dict) -> None:
    if not Path(path).exists():
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        write_atomically(path, render_document(config))


def record_block(path: Path, block_id: str, fields: list, config: dict | None = None) -> None:
    """Replace one marked block's fields and refresh the summary table."""
    config = config or load_config()
    ensure_document(path, config)
    text = Path(path).read_text()
    if f"<!-- dayone:{block_id} -->" not in text:
        raise DayOneError(f"{path} has no block named {block_id}. Run `dayone.py init` on a fresh copy.")
    text = BLOCK.sub(lambda m: block(block_id, render_fields(fields)) if m["id"] == block_id else m[0], text)
    summary = summary_table(config, parse_blocks(text))
    text = BLOCK.sub(lambda m: block("summary", summary) if m["id"] == "summary" else m[0], text)
    write_atomically(path, text)


def record_test(path: Path, number: int, outcome: Outcome, day: dt.date | None = None,
                config: dict | None = None) -> None:
    config = config or load_config()
    if outcome.status not in STATUSES:
        raise DayOneError(f"{outcome.status} is not a status. Use one of: {', '.join(STATUSES)}.")
    test = config["tests"].get(str(number))
    if test is None:
        raise DayOneError(f"There is no day-one test {number}. The tests are 1 to {len(config['tests'])}.")
    record_block(path, f"test-{number}", test_fields(test, outcome, day or dt.date.today()), config)


# The two pay-as-you-go statuses that mean the step is done, and the text each one records.
PAYG_DONE = {"done": "Done on {day}.", "shows pay-as-you-go": "The subscription showed pay-as-you-go on {day}."}


def record_payg(path: Path, status: str, who: str, due: dt.date | None, day: dt.date | None = None,
                config: dict | None = None) -> None:
    config = config or load_config()
    day = day or dt.date.today()
    deadline = parse_day(config["payg"]["deadline"])
    if status in PAYG_DONE:
        text = PAYG_DONE[status].format(day=long_date(day))
    elif status == "planned":
        if due is None:
            raise DayOneError("A planned step needs a date. Pass --due YYYY-MM-DD.")
        if due >= deadline:
            raise DayOneError(f"The date must come before {long_date(deadline)}, when the free credit ends.")
        text = f"Planned for {long_date(due)}."
    else:
        raise DayOneError(f"{status} is not a pay-as-you-go status. Use done, planned or shows pay-as-you-go.")
    record_block(path, "payg", payg_fields(config, text, day, who), config)


def payg_done(path: Path) -> bool:
    """Whether the results document records the move to pay-as-you-go as done."""
    status = read_results(path).get("payg", {}).get("Status", "")
    return any(status.startswith(text.split("{", 1)[0]) for text in PAYG_DONE.values())


# ── What every probe shares ──────────────────────────────────────────────

class ProbeError(Exception):
    """One step of a probe failed in the workspace or in Azure. The message says which and why."""


class SetupError(ProbeError):
    """The probe could not reach the thing it tests, so the test did not run."""


def not_run(error: SetupError, evidence=()) -> Outcome:
    """A test the probe could not start. Its status stays "not run", so its chosen path stays the default."""
    return Outcome("not run", "The probe could not get ready, so the test did not run. The evidence says what "
                              "went wrong. Fix it, then run the probe again.", [*evidence, str(error)])


WIZARD_FIRST = "Run the wizard first: bash ops/wizard/strata-setup.sh"


def probe_args(argv: list[str] | None, description: str | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(description or "").strip().split("\n\n")[0])
    parser.add_argument("--env-file", type=Path, default=None,
                        help="The main checkout's .env, which the wizard filled. That file is the default.")
    parser.add_argument("--results", type=Path, default=None,
                        help="The results document. The default is docs/day-one-results.md in this checkout.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Use canned answers instead of Databricks and Azure, print the result, and write nothing.")
    return parser.parse_args(argv)


def probe_env(args: argparse.Namespace, needs) -> dict[str, str]:
    """The env file's values for a live run, or example values for a dry run."""
    if args.dry_run:
        example = load_env(HERE.parents[1] / ".env.example")
        return {key: value or f"dry-run-{key.lower()}" for key, value in example.items()}
    path = args.env_file or default_env_path()
    if not Path(path).is_file():
        raise DayOneError(f"There is no env file at {path}. {WIZARD_FIRST}")
    env = load_env(path)
    missing = missing_keys(env, needs)
    if missing:
        raise DayOneError(f"{path} has no value for {', '.join(missing)}. {WIZARD_FIRST}")
    return env


def show_outcome(title: str, outcome: Outcome, path_text: str | None = None) -> None:
    print(title)
    print(f"  Status: {outcome.status}")
    print(f"  Result: {outcome.result}")
    print("  Evidence:")
    for line in outcome.evidence:
        print(f"    - {line}")
    if path_text:
        print(f"  Chosen path: {path_text}")


def report_test(number: int, outcome: Outcome, args: argparse.Namespace, config: dict) -> int:
    """Print one test's outcome and, unless this is a dry run, write it in the results document.

    A run that did not get far enough to test anything never replaces an earlier result.
    """
    test = config["tests"][str(number)]
    show_outcome(f"Test {number}. {test['title']}", outcome, outcome.path or chosen_path(test, outcome.status))
    code = 0 if outcome.status == "passed" else 1
    if args.dry_run:
        print("This was a dry run, so I wrote nothing.")
        return code
    results = args.results or default_results_path(config)
    earlier = read_results(results).get(f"test-{number}", {}).get("Status") if Path(results).exists() else None
    if outcome.status == "not run" and earlier not in (None, "not run"):
        print(f"I kept the earlier result ({earlier}) in {results}, because this run did not get far enough "
              "to test anything.")
    else:
        record_test(results, number, outcome, config=config)
        print(f"I wrote this result in {results}.")
    return code


def run_probe(number: int, argv, doc: str | None, needs, live, canned, check, service=None) -> int:
    """The command line every single-test probe shares.

    live(env, config) and canned(env, config) build the probe's adapter for a real run and a dry
    run; check(service, env, config) returns the Outcome. Tests pass their own adapter as service.
    """
    args = probe_args(argv, doc)
    config = load_config()
    try:
        env = probe_env(args, needs)
        if service is None:
            service = canned(env, config) if args.dry_run else live(env, config)
        outcome = check(service, env, config)
    except (DayOneError, ProbeError) as error:
        print(error, file=sys.stderr)
        return 2
    return report_test(number, outcome, args, config)


# ── Command line ─────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dayone.py", description=__doc__.split("\n\n")[0])
    parser.add_argument("--results", type=Path, help="The results document. The default is this checkout's.")
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("init", "show"):
        commands.add_parser(name).add_argument("--results", type=Path, default=argparse.SUPPRESS)
    one = commands.add_parser("record", help="Record one test's result.")
    one.add_argument("--results", type=Path, default=argparse.SUPPRESS)
    one.add_argument("--test", type=int, required=True)
    one.add_argument("--status", required=True, choices=STATUSES)
    one.add_argument("--result", required=True)
    one.add_argument("--evidence", action="append", default=[])
    one.add_argument("--path", help="A chosen path that differs from the one the status implies.")
    one.add_argument("--date", help="The day of the result, as YYYY-MM-DD. The default is today.")
    payg = commands.add_parser("payg", help="Record the pay-as-you-go step.")
    payg.add_argument("--results", type=Path, default=argparse.SUPPRESS)
    payg.add_argument("--status", required=True, choices=("done", "planned", "shows pay-as-you-go"))
    payg.add_argument("--who", required=True)
    payg.add_argument("--due", help="The day the step is planned for, as YYYY-MM-DD.")
    payg.add_argument("--date", help="The day of this record, as YYYY-MM-DD. The default is today.")
    commands.add_parser("payg-done", help="Exit 0 when the subscription has moved to pay-as-you-go.").add_argument(
        "--results", type=Path, default=argparse.SUPPRESS)
    get = commands.add_parser("get", help="Print one setting from dayone.toml.")
    get.add_argument("key")
    model = commands.add_parser("model", help="Print one role's deployment, or its size, from config/models.toml.")
    model.add_argument("role")
    model.add_argument("field", nargs="?", default="deployment", choices=("deployment", "dimensions"))
    one_field = commands.add_parser("field", help="Print one field of one block, such as test-6 Status.")
    one_field.add_argument("--results", type=Path, default=argparse.SUPPRESS)
    one_field.add_argument("block")
    one_field.add_argument("name")
    args = parser.parse_args(argv)

    config = load_config()
    results = args.results or default_results_path(config)
    try:
        if args.command == "init":
            if Path(results).exists():
                print(f"{results} already exists, so I left it as it is.")
            else:
                ensure_document(results, config)
                print(f"I wrote {results}.")
        elif args.command == "show":
            for block_id, fields in read_results(results).items():
                print(f"{block_id}: {fields.get('Status', '')}. {fields.get('Chosen path', '')}".rstrip(". "))
        elif args.command == "record":
            outcome = Outcome(args.status, args.result, args.evidence, args.path)
            record_test(results, args.test, outcome, optional_day(args.date), config)
        elif args.command == "payg":
            record_payg(results, args.status, args.who, optional_day(args.due), optional_day(args.date), config)
        elif args.command == "payg-done":
            return 0 if payg_done(results) else 1
        elif args.command == "field":
            value = read_results(results).get(args.block, {}).get(args.name)
            if value is None:
                raise DayOneError(f"{results} has no field {args.name} in block {args.block}.")
            print("\n".join(value) if isinstance(value, list) else value)
        elif args.command == "model":
            found = models()
            if args.role not in found:
                raise DayOneError(f"config/models.toml has no role named {args.role}. "
                                  f"Its roles are: {', '.join(found)}.")
            value = getattr(found[args.role], args.field)
            if value is None:
                raise DayOneError(f"config/models.toml gives the {args.role} role no {args.field}.")
            print(value)
        elif args.command == "get":
            value = config_value(config, args.key)
            if isinstance(value, dict):
                print("\n".join(value))
            elif isinstance(value, list):
                print("\n".join(str(item) for item in value))
            else:
                print(value)
    except DayOneError as error:
        print(error, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
