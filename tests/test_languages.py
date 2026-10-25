"""Answers in French, Spanish and Portuguese at seam 3 (ticket 42): the verifier reads a sentence's numbers,
dates and number words in the language the answer was asked in (config/languages.toml), and checks them
against the records as it does in English. Quotes stay word for word in their source's language.

The sentences here cite nothing and no tool ran, so check 2 removes each one (no_source): check 1's reasons
alone show how the verifier read each number and date, as tests/test_answer_stream.py's check_1 does.
"""

import tomllib
from contextlib import contextmanager
from pathlib import Path

from strata import languages
from strata.agent.loop import answer_runner
from strata.config import load_tools
from strata.lakehouse.engine import DuckDBEngine
from strata.server.app import create_app
from test_answer_stream import (TODAY, Answers, CallsThenAnswers, EverySentenceFollows, ask_with, check_1, claim,
                                events, no_engine, of, removed_reasons)

TRUTH = {entry["id"]: entry for entry in
         tomllib.loads((Path(__file__).parent / "ground_truth" / "values.toml").read_text())["value"]}
NWWDA_PLAN = {"project_id": "P156634", "implementing_agency": "Northern Water Works Development Agency",
              "plan_date": "2026-10-09", "as_of": "2026-10-23"}


def read_in(language, *sentences):
    """How check 1 read each sentence of an answer asked for in this language."""
    parsed = events(ask_with(create_app(runner=answer_runner(lambda turn: Answers(*(claim(s) for s in sentences)),
                                                             no_engine)), lang=language))
    return check_1(parsed)


def test_a_french_answer_s_numbers_and_dates_are_read_in_french():
    """French groups digits with a narrow no-break space or a space and writes a decimal comma, and writes its
    months in lower case: "1 287 515,60" is one number and "22 juin 2026" one date. In an English answer the
    same digits are three numbers."""
    sentence = "Le contrat a été signé le 22 juin 2026 pour 1 287 515,60 dollars, et 12,5 % restait à payer."

    failed, _ = read_in("fr", sentence)

    assert failed == [[("date_not_in_records", "22 juin 2026"), ("number_not_in_records", "1 287 515,60"),
                       ("number_not_in_records", "12,5")]]
    english, _ = read_in("en", sentence)
    assert [text for _, text in english[0]] == ["22", "2026", "1", "287", "515", "60", "12", "5"]


def test_numbers_written_as_words_are_read_in_the_answer_s_language_and_its_article_is_not_a_number():
    """Ticket 13 read number words only in English, so "trois" and "cuarenta" went unchecked in a French or
    Spanish answer. Each language's words are now numbers a record must hold, joined as the language joins
    them, and the word for one is left alone, since it is also the language's article ("un marché")."""
    french, _ = read_in("fr", "Trois marchés ont été relancés.", "Un marché a été signé.",
                        "Quatre-vingt-dix offres et vingt et une plaintes sont arrivées.")
    spanish, _ = read_in("es", "Se firmaron cuarenta y cinco contratos.", "Una obra se volvió a licitar.")
    portuguese, _ = read_in("pt", "Foram assinados dois mil contratos.", "Um contrato foi assinado.")

    assert french == [[("number_not_in_records", "Trois")],
                      [("number_not_in_records", "Quatre-vingt-dix"), ("number_not_in_records", "vingt et une")]]
    assert spanish == [[("number_not_in_records", "cuarenta y cinco")]]
    assert portuguese == [[("number_not_in_records", "dois mil")]]


def test_a_joiner_between_two_counts_keeps_them_two_numbers():
    """"Trois et quatre marchés" names two counts, so each must be in a record; "vingt et un" is one number."""
    failed, _ = read_in("fr", "Trois et quatre marchés ont été signés.")

    assert failed == [[("number_not_in_records", "Trois"), ("number_not_in_records", "quatre")]]


def ask_in(fixture_db, language, agent, judge=None):
    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    return events(ask_with(create_app(runner=answer_runner(lambda turn: agent, engine_for, tools=load_tools(),
                                                           today=lambda: TODAY), engine_for=engine_for, judge=judge),
                           lang=language))


def test_a_french_sentence_whose_numbers_and_dates_a_cited_record_holds_is_kept(fixture_db):
    """The plan of October 9, 2026 estimates KE-NWWDA-541055-CW-RFB at 1,230,000.00 and plans its signing for April
    24, 2026 (values.toml). Written the French way, both match the plan row, and a French amount the row does not
    hold is removed."""
    estimated = languages.format_number(TRUTH["plan-541055-estimated"]["value"], "fr", 2)
    signing = languages.format_date(TRUTH["plan-541055-planned-signing"]["value"], "fr")
    assert (estimated, signing) == ("1\u202f230\u202f000,00", "24 avril 2026")

    def answer(outputs):
        [row] = [row["evidence_id"] for row in outputs[0]["rows"]
                 if row["activity_reference_no"] == "KE-NWWDA-541055-CW-RFB"]
        return [claim(f"Le plan estime KE-NWWDA-541055-CW-RFB à {estimated} US$ et prévoit sa signature le {signing}.",
                      kind="record", evidence_ids=[row]),
                claim("Le plan l'estime à 1\u202f300\u202f000,00 US$.", kind="record", evidence_ids=[row])]

    parsed = ask_in(fixture_db, "fr", CallsThenAnswers([("check_plan", NWWDA_PLAN)], answer), EverySentenceFollows())

    assert [sentence["text"][:8] for sentence in of(parsed, "sentence")] == ["Le plan "]
    [kept] = of(parsed, "sentence")
    assert [number["text"] for number in kept["numbers"]] == [estimated]
    assert all(found["evidence_id"] for found in kept["numbers"] + kept["dates"])
    assert removed_reasons(parsed) == [[("number_not_in_records", "1\u202f300\u202f000,00")]]
