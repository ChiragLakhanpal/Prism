"""The Genie probe (test 5): the conversation API answers, and it answers as the token's user."""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "ops" / "dayone"))

import dayone  # noqa: E402
import probe_genie  # noqa: E402
from dayone import ProbeError, SetupError  # noqa: E402


class FakeGenie:
    def __init__(self, me="1001", status="COMPLETED", asked_by="1001", answer="There are 21,932 trips.",
                 error=None, refuse=None, signed_out=False):
        self.me, self.status, self.asked_by, self.answer, self.error, self.refuse = (
            me, status, asked_by, answer, error, refuse)
        self.questions = []
        self.signed_out = signed_out

    def user_id(self):
        if self.signed_out:
            raise SetupError("Reading the token's user failed: 401 Unauthorized")
        return self.me

    def ask(self, space_id, question):
        self.questions.append((space_id, question))
        if self.refuse:
            raise ProbeError(self.refuse)
        return {"status": self.status, "user_id": self.asked_by, "conversation_id": "c-77", "message_id": "m-88",
                "answer": self.answer, "error": self.error}


@pytest.fixture
def place(tmp_path):
    # A probe's first run starts from the template, whatever results the committed document holds.
    dayone.ensure_document(tmp_path / "results.md", dayone.load_config())
    (tmp_path / "probe.env").write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\n"
                                        "DATABRICKS_TOKEN='dapi-x'\nGENIE_SPACE_ID='01f0abc'\n")
    return tmp_path


def run(place, genie):
    code = probe_genie.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                            service=genie)
    return code, dayone.read_results(place / "results.md")["test-5"]


def test_an_answer_as_the_tokens_user_passes(place):
    genie = FakeGenie()
    code, test5 = run(place, genie)
    assert code == 0
    assert test5["Status"] == "passed"
    assert genie.questions == [("01f0abc", "How many contracts were signed in each fiscal year, and for how much in US dollars?")]
    assert any("c-77" in line for line in test5["Evidence"])
    assert test5["Chosen path"].startswith("Default")


def test_an_answer_recorded_under_another_user_fails(place):
    code, test5 = run(place, FakeGenie(asked_by="2002"))
    assert code == 1
    assert test5["Status"] == "failed"
    assert "another user" in test5["Result"]
    assert test5["Chosen path"].startswith("Undecided")


def test_a_conversation_that_does_not_complete_fails_with_its_error(place):
    code, test5 = run(place, FakeGenie(status="FAILED", error="The warehouse is stopped."))
    assert code == 1
    assert test5["Status"] == "failed"
    assert any("The warehouse is stopped." in line for line in test5["Evidence"])


def test_a_refused_call_is_recorded_as_a_failure(place):
    code, test5 = run(place, FakeGenie(refuse="Asking Genie failed: PERMISSION_DENIED"))
    assert code == 1
    assert test5["Status"] == "failed"
    assert any("PERMISSION_DENIED" in line for line in test5["Evidence"])


def test_a_missing_space_id_stops_before_writing(place, capsys):
    (place / "probe.env").write_text("DATABRICKS_HOST='https://dbc-1.cloud.databricks.com'\n")
    before = (place / "results.md").read_text()
    code = probe_genie.main(["--env-file", str(place / "probe.env"), "--results", str(place / "results.md")],
                            service=FakeGenie())
    assert code == 2
    assert "GENIE_SPACE_ID" in capsys.readouterr().err
    assert (place / "results.md").read_text() == before


def test_a_token_databricks_refuses_leaves_test_5_not_run(place):
    genie = FakeGenie(signed_out=True)
    code, test5 = run(place, genie)
    assert code == 1
    assert test5["Status"] == "not run"
    assert genie.questions == []
    assert any("401 Unauthorized" in line for line in test5["Evidence"])
