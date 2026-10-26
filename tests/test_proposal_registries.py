"""The registries the proposal reads beside the app and the deck (ticket 46; the 46 brief, sections 5, 7, 11.4 and 12):
the addresses the panel opens, the rubric map, the change drill and what is designed but not built.

Expected values come from docs/assessment.md, the spec's "Ten single places" and docs/PLAN.md section 15, never
from the files under test.
"""

import datetime as dt
import re
import subprocess
from pathlib import Path

import pytest

from strata import config
from strata.config import ConfigError
from strata.proposal import register

ROOT = Path(__file__).resolve().parents[1]


def write(tmp_path, name, text):
    path = tmp_path / name
    path.write_text(text)
    return path


# ── The addresses ────────────────────────────────────────────────────────

def test_the_deck_and_the_proposal_take_their_addresses_from_the_app_and_the_repo(tmp_path):
    urls = config.load_urls(write(tmp_path, "urls.toml", 'app = "https://strata-1.aws.databricksapps.com/"\n'
                                  'dashboard = ""\nrepo = "https://github.com/someone/strata"\n'))
    assert urls.app == "https://strata-1.aws.databricksapps.com"
    assert urls.deck == "https://strata-1.aws.databricksapps.com/present"
    assert urls.dashboard is None
    assert urls.proposal == "https://github.com/someone/strata/blob/main/docs/proposal.md"


def test_an_address_left_empty_leaves_what_it_derives_empty_too(tmp_path):
    urls = config.load_urls(write(tmp_path, "urls.toml", 'app = ""\ndashboard = ""\nrepo = ""\n'))
    assert (urls.app, urls.deck, urls.repo, urls.proposal) == (None, None, None, None)


def test_an_address_that_is_not_https_names_its_key_and_the_fix(tmp_path):
    with pytest.raises(ConfigError, match=r"In urls.toml, app must be an https address"):
        config.load_urls(write(tmp_path, "urls.toml", 'app = "strata.example"\ndashboard = ""\nrepo = ""\n'))


def test_the_committed_addresses_load():
    urls = config.load_urls()
    for name in ("app", "dashboard", "repo"):
        value = getattr(urls, name)
        assert value is None or value.startswith("https://")


# ── The rubric map ───────────────────────────────────────────────────────

def assessment_rubric() -> list[tuple[str, int, list[str]]]:
    """The rubric table in docs/assessment.md, section 5: each dimension, its points and its criteria."""
    text = (ROOT / "docs" / "assessment.md").read_text()
    rows = re.findall(r"^\| \*\*(.+?)\*\*\s*\| (\d+) \| (.+?) \|$", text, re.M)
    return [(name.strip(), int(points), [part.strip().rstrip(".") for part in criteria.split(";")])
            for name, points, criteria in rows]


def test_the_rubric_registry_holds_the_assessment_rubric_word_for_word():
    rubric = config.load_rubric()
    table = assessment_rubric()
    assert len(table) == 4
    assert [(d.rubric_name, d.points) for d in rubric.dimensions] == [(name, points) for name, points, _ in table]
    assert [[c.rubric for c in d.criteria] for d in rubric.dimensions] == [criteria for _, _, criteria in table]
    assert sum(d.points for d in rubric.dimensions) == rubric.total == 100
    assert sum(len(d.criteria) for d in rubric.dimensions) == 13


def test_the_rubric_map_names_dimensions_and_criteria_in_sentence_case_as_the_46_brief_gives_them():
    # The 46 brief, section 7.2: the rubric's words in sentence case, with "validation" dropped (rule 19).
    rubric = config.load_rubric()
    assert [d.name for d in rubric.dimensions] == [
        "System and knowledge architecture", "Analytical and AI methodology", "Domain alignment and data use",
        "Operationalization and scalability"]
    assert [c.says for d in rubric.dimensions for c in d.criteria] == [
        "Robustness of multimodal data ingestion",
        "Depth and scalability of the knowledge graph or relational schema design",
        "Effective handling of unstructured text and document hierarchy",
        "Soundness of predictive risk modeling",
        "Sophistication of the retrieval pipeline",
        "Practical mitigation of hallucinations",
        "Strict citation and grounding mechanics",
        "Effective use of the specified open development data sources",
        "Deep understanding of public procurement stages",
        "Realistic handling of missing or incomplete reporting",
        "Feasibility of the deployment roadmap",
        "Concrete metrics and KPIs",
        "Clarity of continuous learning and data feedback loops"]


def test_each_criterion_names_where_the_proposal_answers_it_and_what_you_can_open():
    rubric = config.load_rubric()
    for dimension in rubric.dimensions:
        assert dimension.summary
        for criterion in dimension.criteria:
            assert criterion.answered_in, criterion.says
            assert 1 <= len(criterion.open) <= 3, criterion.says


def test_a_dimension_whose_points_are_not_whole_numbers_names_the_fix(tmp_path):
    text = (ROOT / "config" / "rubric.toml").read_text().replace("points = 30", 'points = "thirty"', 1)
    with pytest.raises(ConfigError, match=r"points must be a whole number"):
        config.load_rubric(write(tmp_path, "rubric.toml", text))


# ── The change drill ─────────────────────────────────────────────────────

def test_the_change_drill_lists_plan_section_15s_ten_changes_in_order():
    drills = config.load_change_drills()
    assert [drill.change for drill in drills] == [
        "Add a data source", "Add a tool", "Change a signal threshold", "Add a country to the slice",
        "Swap the model", "Reorder the evidence ladder", "Add a field to the package form", "Reword copy",
        "Add a benchmark or must-refuse question", "Add a dashboard tile"]


def test_each_drill_names_a_place_and_a_test_that_exist():
    for drill in config.load_change_drills():
        assert (ROOT / drill.place).exists(), drill.place
        assert (ROOT / drill.proved_by).exists(), drill.proved_by


# ── The rehearsal record (ticket 49) ─────────────────────────────────────

REHEARSAL = """
[[rehearsals]]
change = "Swap the model"
example = "The agent's deployment changed from one model to another."
branch = "drill-49/05-swap-the-model"
commit = "0123456789abcdef0123456789abcdef01234567"
started_at = 2026-10-26T10:00:05-07:00
gate_started_at = 2026-10-26T10:03:50-07:00
finished_at = 2026-10-26T10:06:06-07:00
gate_seconds = 131.4
"""


def test_a_rehearsal_gives_its_whole_minutes_rounded_up_and_the_day_it_finished(tmp_path):
    [rehearsal] = register.load_rehearsals(write(tmp_path, "rehearsals.toml", REHEARSAL)).values()

    assert rehearsal.change == "Swap the model"
    assert rehearsal.minutes == 7  # 6 minutes 1 second never reads as 6
    assert rehearsal.measured_on == dt.date(2026, 10, 26)
    assert (rehearsal.branch, rehearsal.commit[:7], rehearsal.gate_seconds) == (
        "drill-49/05-swap-the-model", "0123456", 131.4)


def test_a_rehearsal_gives_the_seconds_its_edits_took_before_the_gate_started(tmp_path):
    """The 49 review's B1: git dates a commit before its pre-commit hook runs, so the commit's date is when the
    edits were done and the gate began. From 10:00:05 to 10:03:50 is 3 minutes 45 seconds."""
    [rehearsal] = register.load_rehearsals(write(tmp_path, "rehearsals.toml", REHEARSAL)).values()

    assert rehearsal.editing_seconds == 225


def test_a_later_rehearsal_runs_on_a_drill_branch_not_tied_to_ticket_49(tmp_path):
    path = write(tmp_path, "rehearsals.toml", REHEARSAL.replace("drill-49/05", "drill/05"))

    assert register.load_rehearsals(path)["Swap the model"].branch == "drill/05-swap-the-model"


@pytest.mark.parametrize("old, new, says", [
    ('change = "Swap the model"', 'change = "Swap the agent"', r"Swap the agent, which config/change_drills\.toml "
                                                                r"does not list"),
    ("finished_at = 2026-10-26T10:06:06-07:00", "finished_at = 2026-10-26T09:06:06-07:00",
     r"finished_at must come after started_at"),
    ('branch = "drill-49/05-swap-the-model"', 'branch = "strata/49-change-drills-and-rehearsal"',
     r"branch must start with drill/"),
    ("gate_seconds = 131.4\n", "", r"needs gate_seconds"),
    ("gate_started_at = 2026-10-26T10:03:50-07:00\n", "", r"needs gate_started_at"),
    ("gate_started_at = 2026-10-26T10:03:50-07:00", "gate_started_at = 2026-10-26T09:59:00-07:00",
     r"gate_started_at must fall between started_at and finished_at"),
    ("gate_started_at = 2026-10-26T10:03:50-07:00", "gate_started_at = 2026-10-26T10:07:00-07:00",
     r"gate_started_at must fall between started_at and finished_at"),
    ('commit = "0123456789abcdef0123456789abcdef01234567"', "commit = 1234567",
     r"rehearsal 1's commit must be text"),
    ('example = "The agent\'s deployment changed from one model to another."', "example = 5",
     r"rehearsal 1's example must be text"),
], ids=["unknown-change", "backwards", "ticket-branch", "no-gate-time", "no-gate-start", "gate-before-start",
        "gate-after-finish", "commit-a-number", "example-a-number"])
def test_a_rehearsal_of_the_wrong_shape_is_refused_with_a_sentence(tmp_path, old, new, says):
    with pytest.raises(register.RegisterError, match=says):
        register.load_rehearsals(write(tmp_path, "rehearsals.toml", REHEARSAL.replace(old, new)))


def test_two_rehearsals_of_one_drill_are_refused(tmp_path):
    with pytest.raises(register.RegisterError, match=r"Swap the model is rehearsed twice"):
        register.load_rehearsals(write(tmp_path, "rehearsals.toml", REHEARSAL + REHEARSAL))


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True)


def held_here(rehearsal: register.Rehearsal) -> bool:
    """Whether this clone holds the drill commit. A clone without the drill branches' objects skips the checks."""
    return git("cat-file", "-e", f"{rehearsal.commit}^{{commit}}").returncode == 0


def test_no_rehearsal_left_its_change_on_this_branch():
    """Criterion 3 of ticket 49: each drill ran on a throwaway branch, and none of its commits reached the branch
    being tested, the integration branch included. git cherry also finds the change under another hash, as a
    cherry-pick or a squash would leave it: "+" means no commit on HEAD makes the same change."""
    for rehearsal in filter(held_here, register.load_rehearsals().values()):
        merged = git("merge-base", "--is-ancestor", rehearsal.commit, "HEAD")
        assert merged.returncode == 1, f"{rehearsal.branch}'s commit {rehearsal.commit[:7]} is on this branch"
        cherry = git("cherry", "HEAD", rehearsal.commit, f"{rehearsal.commit}^")
        assert cherry.returncode == 0, cherry.stderr
        assert cherry.stdout.splitlines() == [f"+ {rehearsal.commit}"], (
            f"{rehearsal.branch}'s change is on this branch under another commit")


def test_each_rehearsal_s_gate_start_is_its_commit_s_own_date():
    """The editing time Annex 1 gives is gate_started_at less started_at, so gate_started_at must be the date git
    gave the drill commit, which it sets before the pre-commit hook runs the gate."""
    for rehearsal in filter(held_here, register.load_rehearsals().values()):
        dated = dt.datetime.fromisoformat(git("log", "-1", "--format=%aI", rehearsal.commit).stdout.strip())
        assert rehearsal.gate_started_at == dated, rehearsal.change


# ── Designed, not built ──────────────────────────────────────────────────

ITEM = """
[[items]]
key = "hazard_model"
name = "The early-warning model"
route = "/projects/P156634"
paragraph = "m2-time-estimates"
exists_now = "Strata shows fixed signals."
"""


def test_an_item_designed_but_not_built_names_its_route_and_its_paragraph(tmp_path):
    items = config.load_designed_not_built(write(tmp_path, "designed_not_built.toml", ITEM))
    assert [(item.key, item.route, item.paragraph) for item in items] == [
        ("hazard_model", "/projects/P156634", "m2-time-estimates")]
    assert items[0].copy_key == "designedNotBuilt.items.hazard_model"


def test_an_item_with_a_route_outside_the_app_names_the_fix(tmp_path):
    with pytest.raises(ConfigError, match=r"route must be an address in the app"):
        config.load_designed_not_built(write(tmp_path, "designed_not_built.toml",
                                             ITEM.replace('"/projects/P156634"', '"https://example.org"')))


def test_the_committed_list_loads():
    assert isinstance(config.load_designed_not_built(), tuple)
