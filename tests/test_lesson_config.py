"""The single places ticket 29 adds or extends: the roles file (config/roles.toml), the lesson lists
(config/lessons.toml), the editions of the procurement rules (config/editions.toml) and the
thresholds file's [lesson_review] section. Each loads through one function in strata.config, and a
file that does not follow its shape stops with a sentence that names the file and the fix.

Expected values come from docs/PLAN.md section 11, the spec's user stories 89 to 95 and the 29
design brief, never from the files themselves.
"""

import datetime as dt
import shutil
from pathlib import Path

import pytest

from strata import config
from strata.config import ConfigError

ROOT = Path(__file__).resolve().parents[1]
ROLES_FIXTURE = ROOT / "tests" / "fixtures" / "roles.toml"


def copy(source: Path, tmp_path, old=None, new=None):
    target = tmp_path / source.name
    shutil.copy(source, target)
    if old is not None:
        text = target.read_text()
        assert old in text, f"{old!r} is not in {source.name}"
        target.write_text(text.replace(old, new, 1))
    return target


# ── The roles file ───────────────────────────────────────────────────────

def test_the_roles_file_names_the_two_lesson_reviewer_groups_and_what_each_may_do():
    """PLAN.md section 11: an accredited procurement specialist recommends; a lead procurement specialist
    decides. The 29 brief: a lead may also recommend, and either may cross-check."""
    roles = config.load_roles()

    accredited, lead = roles.groups["accredited_procurement_specialist"], roles.groups["lead_procurement_specialist"]
    assert accredited.role == "accredited procurement specialist"
    assert lead.role == "lead procurement specialist"
    assert set(accredited.acts) == {"recommend", "cross_check"}
    assert set(lead.acts) == {"recommend", "decide", "cross_check"}
    assert accredited.pages == lead.pages == ("lesson_review",)


def test_the_fixture_roles_name_the_reviewers_the_tests_need():
    """The 29 brief, section 13: an accredited procurement specialist for South Asia, leads for South Asia
    (one works on P130164, and two do not, so a lesson one of them recommended has a lead left to decide it),
    a reviewer for another region, and nobody else."""
    roles = config.load_roles(ROLES_FIXTURE)

    south_asia = [person for person in roles.people if "South Asia" in person.regions]
    assert sorted(person.role(roles) for person in south_asia) == [
        "accredited procurement specialist", "lead procurement specialist", "lead procurement specialist",
        "lead procurement specialist"]
    assert [person.name for person in south_asia if "P130164" in person.projects] != []
    elsewhere = [person for person in roles.people if "South Asia" not in person.regions]
    assert [person.regions for person in elsewhere] == [("Eastern and Southern Africa",)]


def test_a_viewer_is_found_by_the_email_the_app_forwards_whatever_its_case():
    roles = config.load_roles(ROLES_FIXTURE)
    first = roles.people[0]

    assert roles.person(first.email.upper()) == first
    assert roles.person("ana.example@worldbank.org") is None
    assert roles.person(None) is None


@pytest.mark.parametrize("old, new, says", [
    ('groups = ["accredited_procurement_specialist"]', 'groups = ["procurement_wizard"]',
     "names the group procurement_wizard, which"),
    ('projects = ["P130164"]', 'projects = ["130164"]', "must be a project ID"),
    ('acts = ["recommend", "cross_check"]', 'acts = ["recommend", "endorse"]', "endorse"),
    ('regions = ["South Asia"]', "regions = []", "regions"),
], ids=["unknown-group", "bad-project-id", "unknown-act", "no-region"])
def test_a_roles_file_of_the_wrong_shape_is_refused_with_a_sentence(tmp_path, old, new, says):
    path = copy(ROLES_FIXTURE, tmp_path, old, new)

    with pytest.raises(ConfigError, match=says):
        config.load_roles(path)


def test_a_person_listed_twice_is_refused(tmp_path):
    path = copy(ROLES_FIXTURE, tmp_path)
    text = path.read_text()
    first = text[text.index("[[people]]"):text.index("[[people]]", text.index("[[people]]") + 1)]
    path.write_text(text + "\n" + first)

    with pytest.raises(ConfigError, match="more than once"):
        config.load_roles(path)


# ── The lesson lists ─────────────────────────────────────────────────────

def test_the_lesson_lists_hold_the_two_kinds_and_closed_lists_of_risk_factors_and_stages():
    lists = config.load_lesson_lists()

    assert [kind.label for kind in lists.kinds] == ["What worked", "What didn't work"]
    assert "Procurement planning" in [stage.label for stage in lists.stages]
    assert len(lists.risk_factors) >= 5
    assert lists.risk_factor("cost_estimates").key == "cost_estimates"
    assert lists.example_projects == ()


def test_a_risk_factor_listed_twice_is_refused(tmp_path):
    path = copy(ROOT / "config" / "lessons.toml", tmp_path)
    path.write_text(path.read_text() + '\n[[risk_factors]]\nkey = "cost_estimates"\nlabel = "Again"\n')

    with pytest.raises(ConfigError, match="cost_estimates"):
        config.load_lesson_lists(path)


# ── The editions of the procurement rules ────────────────────────────────

def test_the_editions_file_names_the_2011_guidelines_the_showcase_project_followed():
    """P130164's PAD, PDF page 49, paragraph 21, names the "Guidelines: Procurement under IBRD Loans and
    IDA Credits" dated January 2011 (tests/ground_truth/values.toml, pad-procurement-guidelines)."""
    editions = config.load_editions()

    found = editions.named_in('in Section I of the "Guidelines: Procurement under IBRD Loans and IDA Credits" '
                              "(dated January 2011).")
    assert found is not None and "January 2011" in found.name
    assert editions.named_in("This paragraph names no rules.") is None


# ── The thresholds file's [lesson_review] section ────────────────────────

def test_the_lesson_review_thresholds_hold_the_clock_the_sample_and_the_windows():
    value = config.load_thresholds().value

    assert value("lesson_review.business_days") == 10  # spec story 91
    assert value("lesson_review.cross_check_share") == 0.1  # spec story 94
    assert value("lesson_review.decided_window_days") == 90  # the 29 brief, section 5.3
    assert value("lesson_review.quote_check_window_days") == 30  # the 29 brief, section 5.3
    assert value("lesson_review.likely_repeats_max") == 3  # the 29 brief, section 4.2
    holidays = value("lesson_review.holidays")
    assert isinstance(holidays, list) and all(isinstance(day, dt.date) for day in holidays)
