"""The retrieval loop's recorded answers (ticket 32): tests/record_retrieval_api.py writes the answers the feedback
row's, Passage reports' and Judging's screen tests and the gallery serve, from one story on the fixture; the routes
must still answer with them word for word, so the screens and the server cannot drift apart."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_screens_recorded_retrieval_answers_are_what_the_routes_answer(fixture_db, tmp_path):
    from record_retrieval_api import answers

    for name, text in answers(tmp_path).items():
        assert text == (ROOT / "tests" / "fixtures" / "api" / name).read_text(), (
            f"{name} is out of date. Check the change, then write the files again: "
            "uv run --frozen python tests/record_retrieval_api.py")
