"""The day-one results document: the ten tests from PLAN.md section 14, and how a result lands in it.

Expected questions come from PLAN.md itself, not from the code that writes the document.
"""

import datetime as dt
import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DAYONE_DIR = REPO / "ops" / "dayone"
sys.path.insert(0, str(DAYONE_DIR))

import dayone  # noqa: E402

RESULTS = REPO / "docs" / "day-one-results.md"
PLAN = REPO / "docs" / "PLAN.md"


def plan_day_one_tests():
    """PLAN.md section 14's numbered list, as {number: its first sentence}."""
    section = PLAN.read_text().split("## 14. Day-one tests", 1)[1].split("\n## ", 1)[0]
    items = re.findall(r"^(\d+)\. (.+)$", section, re.M)
    return {int(number): body.split(". ")[0].rstrip(".") + "." for number, body in items}


def section_of(text, number):
    """The text of one test's section, from its heading to the next heading."""
    match = re.search(rf"^### Test {number}\. .*?(?=^### |\Z)", text, re.M | re.S)
    assert match, f"the document has no section for test {number}"
    return match.group(0)


def record(results, *args):
    return subprocess.run([sys.executable, str(DAYONE_DIR / "dayone.py"), "record", "--results", str(results), *args],
                          capture_output=True, text=True)


def test_the_document_lists_the_ten_day_one_tests_from_the_plan():
    plan = plan_day_one_tests()
    assert sorted(plan) == list(range(1, 11))
    text = RESULTS.read_text()
    results = dayone.read_results(RESULTS)
    for number, question in plan.items():
        assert question in section_of(text, number)
        fields = results[f"test-{number}"]
        for name in ("Status", "Result", "Evidence", "Chosen path"):
            assert fields.get(name), f"test {number} has a blank {name}"


def waiting_problems(config, folder):
    """Why the template that config renders is not ready for the wizard, one sentence each; none when it is.

    The template is written to folder, so the committed document is free to hold the wizard's results.
    """
    rendered = folder / "day-one-results.md"
    rendered.write_text(dayone.render_document(config))
    text = rendered.read_text()
    problems = []
    for block_id, fields in sorted(dayone.read_results(rendered).items()):
        if not block_id.startswith("test-"):
            continue
        number = block_id.removeprefix("test-")
        if fields["Status"] != "not run":
            problems.append(f"Test {number} starts with the status {fields['Status']}, not \"not run\".")
        if not ("Not run yet" in fields["Result"] and "wizard" in fields["Result"]):
            problems.append(f"Test {number}'s result does not say it waits for the wizard.")
        if not fields["Chosen path"].startswith("Default"):
            problems.append(f"Test {number} does not start on its default path.")
        if not re.search(r"Command: `([^`]+)`", section_of(text, number)):
            problems.append(f"Test {number} names no command.")
    return problems


def test_before_the_wizard_runs_each_test_waits_with_the_command_that_fills_it(tmp_path):
    assert waiting_problems(dayone.load_config(), tmp_path) == []


def split_at_blocks(text):
    """The document cut at its marked blocks: the text between them, and each block as (id, its text)."""
    between, blocks, start = [], [], 0
    for match in dayone.BLOCK.finditer(text):
        between.append(text[start:match.start()])
        blocks.append((match["id"], match[0]))
        start = match.end()
    return between + [text[start:]], blocks


def is_long_date(text):
    """True for a date the way dayone.long_date writes it, such as October 24, 2026."""
    try:
        dt.datetime.strptime(text, "%B %d, %Y")
    except (TypeError, ValueError):
        return False
    return True


def recorded_problems(block_id, fields, template):
    """Why one block that differs from the template is not a result the wizard or a probe recorded.

    A recorded test keeps the template's fields in order and fills them: a status, a result, at least
    one Evidence line that is not the template's "None yet" line, a chosen path and the day it ran.
    A probe that could not get ready records "not run" the same way, with its evidence and its day.
    """
    if list(fields) != list(template):
        return [f"its fields are {', '.join(fields)}, not {', '.join(template)}."]
    if not block_id.startswith("test-"):
        return ["it differs from the template, and nothing records results in it."]
    problems = []
    if fields["Status"] not in dayone.STATUSES:
        problems.append(f"its Status, \"{fields['Status']}\", is not one of {', '.join(dayone.STATUSES)}.")
    for name in ("Result", "Chosen path"):
        if not fields[name]:
            problems.append(f"its {name} is blank.")
    evidence = fields["Evidence"] if isinstance(fields["Evidence"], list) else []
    if not [line for line in evidence if line.strip() and line not in template["Evidence"]]:
        problems.append("it has no Evidence line.")
    if not is_long_date(fields["Last run"]):
        problems.append(f"its Last run, \"{fields['Last run']}\", is not a date.")
    return problems


def document_problems(text, config):
    """Why a results document is not the template that config renders plus recorded results; none when it is.

    The text outside the marked blocks must be exactly the rendering's, so it never drifts from dayone.toml.
    Each block is either the rendering's text or a result the wizard or a probe recorded.
    """
    template = dayone.render_document(config)
    between, blocks = split_at_blocks(text)
    template_between, template_blocks = split_at_blocks(template)
    ids, template_ids = [i for i, _ in blocks], [i for i, _ in template_blocks]
    if ids != template_ids:
        return [f"The document's blocks are {', '.join(ids)}, but dayone.toml renders {', '.join(template_ids)}."]
    problems = []
    for after, mine, theirs in zip(["the start", *ids], between, template_between):
        if mine != theirs:
            line = next(a for a, b in zip(mine.splitlines() + [""], theirs.splitlines() + [""]) if a != b)
            problems.append(f"After {after}, the text differs from what dayone.toml renders, at: {line!r}")
    fields, template_fields = dayone.parse_blocks(text), dayone.parse_blocks(template)
    for (block_id, mine), (_, theirs) in zip(blocks, template_blocks):
        if block_id == "summary":
            if mine != dayone.block("summary", dayone.summary_table(config, fields)):
                problems.append("Block summary: the table does not match the test blocks below it.")
        elif mine != theirs:
            found = recorded_problems(block_id, fields[block_id], template_fields[block_id])
            problems += [f"Block {block_id}: {problem}" for problem in found]
    return problems


def test_the_committed_document_matches_what_the_settings_file_describes():
    """The committed document is the template dayone.toml renders, plus any results the wizard or a probe recorded."""
    assert document_problems(RESULTS.read_text(), dayone.load_config()) == []


def fresh_template(tmp_path):
    results = tmp_path / "results.md"
    results.write_text(dayone.render_document(dayone.load_config()))
    return results


def test_a_recorded_result_needs_an_evidence_line_and_a_dated_last_run(tmp_path):
    config, results = dayone.load_config(), fresh_template(tmp_path)
    day = dt.date(2026, 10, 24)
    dayone.record_test(results, 4, dayone.Outcome("passed", "The hybrid query returned 3 passages.",
                                                  ["Endpoint strata-search is ONLINE."]), day)
    recorded = results.read_text()
    assert document_problems(recorded, config) == []

    no_evidence = recorded.replace("  - Endpoint strata-search is ONLINE.\n", "")
    assert document_problems(no_evidence, config) == ["Block test-4: it has no Evidence line."]
    undated = recorded.replace("- Last run: October 24, 2026", "- Last run: never")
    assert document_problems(undated, config) == ["Block test-4: its Last run, \"never\", is not a date."]

    dayone.record_test(results, 4, dayone.Outcome("passed", "It worked."), day)
    assert document_problems(results.read_text(), config) == ["Block test-4: it has no Evidence line."]


def test_the_document_says_to_run_the_wizard_first_and_dates_the_pay_as_you_go_step():
    text = RESULTS.read_text()
    first_section = text.split("\n## ", 2)[1]
    assert "bash ops/wizard/strata-setup.sh" in first_section
    payg = dayone.read_results(RESULTS)["payg"]
    assert "November 10, 2026" in payg["Deadline"]
    assert payg["Who"]


def test_a_failed_parse_test_switches_to_content_understanding_and_leaves_the_others(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    before = dayone.read_results(results)

    done = record(results, "--test", "3", "--status", "failed",
                  "--result", "ai_parse_document stopped after 40 of 212 pages.",
                  "--evidence", "Statement 01ef-77 ended with an error.")
    assert done.returncode == 0, done.stderr

    after = dayone.read_results(results)
    assert after["test-3"]["Status"] == "failed"
    assert after["test-3"]["Chosen path"].startswith("Gap fill")
    assert "Content Understanding" in after["test-3"]["Chosen path"]
    assert after["test-3"]["Evidence"] == ["Statement 01ef-77 ended with an error."]
    assert {k: v for k, v in after.items() if k != "test-3"} == {k: v for k, v in before.items() if k != "test-3"}
    summary_row = next(line for line in results.read_text().splitlines() if line.startswith("| 3 |"))
    assert "failed" in summary_row and "Gap fill" in summary_row


def test_a_failed_test_with_no_named_gap_fill_leaves_the_path_to_the_user(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    assert record(results, "--test", "5", "--status", "failed", "--result", "Genie did not answer.",
                  "--evidence", "The conversation ended with FAILED.").returncode == 0
    assert dayone.read_results(results)["test-5"]["Chosen path"].startswith("Undecided")


def test_recording_the_same_result_twice_leaves_the_same_document(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    args = ("--test", "4", "--status", "passed", "--result", "The hybrid query returned 3 passages.",
            "--evidence", "Endpoint strata-search is ONLINE.", "--evidence", "Index answered a HYBRID query.",
            "--date", "2026-10-24")
    record(results, *args)
    once = results.read_text()
    record(results, *args)
    assert results.read_text() == once
    assert dayone.read_results(results)["test-4"]["Last run"] == "October 24, 2026"


def test_a_planned_pay_as_you_go_step_records_its_date_and_who_takes_it(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    done = subprocess.run([sys.executable, str(DAYONE_DIR / "dayone.py"), "payg", "--results", str(results),
                           "--status", "planned", "--who", "The subscription owner", "--due", "2026-11-03"],
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    payg = dayone.read_results(results)["payg"]
    assert "November 3, 2026" in payg["Status"]
    assert payg["Who"] == "The subscription owner"


def test_a_pay_as_you_go_date_after_the_credit_ends_is_refused(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    done = subprocess.run([sys.executable, str(DAYONE_DIR / "dayone.py"), "payg", "--results", str(results),
                           "--status", "planned", "--who", "The subscription owner", "--due", "2026-11-12"],
                          capture_output=True, text=True)
    assert done.returncode != 0
    assert "November 10, 2026" in done.stderr
    assert results.read_text() == RESULTS.read_text()


def test_a_badly_formed_date_gets_a_plain_sentence_and_no_traceback(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    for typed in ("11/03/2026", "2026-13-01"):
        done = subprocess.run([sys.executable, str(DAYONE_DIR / "dayone.py"), "payg", "--results", str(results),
                               "--status", "planned", "--who", "The subscription owner", "--due", typed],
                              capture_output=True, text=True)
        assert done.returncode == 1
        assert done.stderr.strip() == f"{typed} is not a date in the form YYYY-MM-DD."
    assert results.read_text() == RESULTS.read_text()


def test_a_badly_formed_test_date_gets_the_same_one_sentence(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    done = record(results, "--test", "6", "--status", "passed", "--result", "It worked.", "--date", "23/10/2026")
    assert done.returncode == 1
    assert done.stderr.strip() == "23/10/2026 is not a date in the form YYYY-MM-DD."
    assert results.read_text() == RESULTS.read_text()


def test_the_document_lists_what_the_probes_leave_in_the_workspace():
    text = RESULTS.read_text()
    assert "## What the probes leave in the workspace" in text
    section = text.split("## What the probes leave in the workspace", 1)[1].split("\n## ", 1)[0]
    for name in ("`strata`", "`strata-dayone`", "`workspace.strata_dayone`", "`strata-search`"):
        assert name in section, name
    assert "- A conversation in the Genie space you chose in the wizard, which asks \"How many trips are in the table?\"" \
        in section
    assert ("- Read access for the app `strata` to the secret scope `strata`. The app reads only "
            "`APPLICATIONINSIGHTS_CONNECTION_STRING`, but Databricks grants access to the whole scope, which also "
            "holds `AZURE_OPENAI_API_KEY`.") in section
    assert "workspace.default" not in text


def payg_done(results):
    return subprocess.run([sys.executable, str(DAYONE_DIR / "dayone.py"), "payg-done", "--results", str(results)],
                          capture_output=True, text=True).returncode


def test_payg_done_answers_whether_the_subscription_moved(tmp_path):
    results = tmp_path / "results.md"
    shutil.copy(RESULTS, results)
    assert payg_done(results) == 1
    dayone.record_payg(results, "planned", "The subscription owner", dayone.parse_day("2026-11-03"))
    assert payg_done(results) == 1
    dayone.record_payg(results, "done", "The subscription owner", None)
    assert payg_done(results) == 0
    dayone.record_payg(results, "shows pay-as-you-go", "The subscription owner", None)
    assert payg_done(results) == 0
