"""Answers in French, Spanish and Portuguese at seam 3 (ticket 42): the verifier reads a sentence's numbers,
dates and number words in the language the answer was asked in (config/languages.toml), and checks them
against the records as it does in English. Quotes stay word for word in their source's language.

The sentences here cite nothing and no tool ran, so check 2 removes each one (no_source): check 1's reasons
alone show how the verifier read each number and date, as tests/test_answer_stream.py's check_1 does.
"""

import datetime as dt
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


# ── A scripted answer in French (the ticket's criterion 3) ───────────────

FRENCH_CASE = "p127203-fr-procurement-delays"


def ask_scripted(fixture_db, case_id):
    """Ask a scripted case over HTTP in the case's language, as the screen's ?lang= asks it."""
    from strata.agent.scripted import ScriptedAgent, ScriptedJudge, load_cases

    case = load_cases()[case_id]

    @contextmanager
    def engine_for(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    app = create_app(runner=answer_runner(lambda turn: ScriptedAgent(case), engine_for, today=lambda: case.as_of),
                     engine_for=engine_for, judge=ScriptedJudge(case), new_run_id=lambda: "run-0001")
    return events(ask_with(app, case.question, scope=case.scope, asof=case.as_of.isoformat(), lang=case.language))


def test_with_lang_fr_the_scripted_answer_is_written_in_french_and_its_quotes_stay_word_for_word(fixture_db):
    """The question is asked in English with lang=fr. The answer's sentences are in French, each quote is the French
    completion report's own words on its page, the answer says which language it was written in and which language
    the question was in, and all six checks pass with nothing removed."""
    from strata.config import load_languages
    from strata.knowledge.language import LangidDetector

    parsed = ask_scripted(fixture_db, FRENCH_CASE)

    [said] = of(parsed, "language")
    assert said == {"lang": "fr", "question_lang": "en"}
    assert [kind for kind, _ in parsed].index("language") < [kind for kind, _ in parsed].index("step")
    assert of(parsed, "removed") == []
    sentences = of(parsed, "sentence")
    assert len(sentences) == 4
    assert all(LangidDetector().detect(sentence["text"]).code == "fr" for sentence in sentences)
    never = load_languages().get("fr").never_write
    assert not [word for sentence in sentences for word in never if word in sentence["text"].lower()]
    # Each quote is word for word on its French page, and the evidence it cites is marked French.
    evidence = {item["id"]: item for item in of(parsed, "evidence")}
    quoted = [sentence for sentence in sentences if sentence["quote"]]
    assert len(quoted) == 2
    for sentence in quoted:
        cited = evidence[sentence["quote"]["evidence_id"]]
        assert cited["row"]["language"] == "fr"
        [mark] = [mark for mark in cited["highlights"] if mark["sentence"] == sentence["index"]]
        on_page = cited["row"]["text"][mark["start"]:mark["end"]]
        assert on_page == sentence["quote"]["text"] and f'"{on_page}"' in sentence["text"]
    checks = of(parsed, "checks")[0]
    assert checks["checks_run"] == [1, 2, 3, 4, 5, 6]
    assert checks["dates"] == {"total": 1, "matched": 1}
    assert checks["quotes"] == {"total": 2, "found": 2}
    assert checks["judge"]["judged"] == checks["judge"]["followed"] == 1
    assert [date["text"] for sentence in sentences for date in sentence["dates"]] == ["29 juillet 2021"]


# ── A scripted draft in French (the ticket's criterion 3) ────────────────

def test_with_lang_fr_review_notes_are_written_in_french_and_keep_their_language_in_the_word_file(writers_fixture_db,
                                                                                                   tmp_path):
    """The draft is asked for with lang=fr. Its notes are in French, all six checks pass with nothing removed, the
    draft says it was written in French, the plan's description is quoted in its own English words, and the Word
    file's note runs carry French proofing while its headings stay English. It runs on the fixture as the writer's
    French recording saw it (tests/writer_world.py, ticket 132)."""
    fixture_db = writers_fixture_db
    import io
    import zipfile
    from xml.etree import ElementTree

    from strata.knowledge.language import LangidDetector
    from test_drafts import ANA, NWWDA, act, call
    from test_drafts import events as draft_events

    app = drafting_app(fixture_db, tmp_path, "review-notes-nwwda-2026-10-09-fr")
    sent = draft_events(call(app, "POST", "/api/drafts", ANA, json={**NWWDA, "idempotency_key": "fr-1", "lang": "fr"}).text)
    [draft_id] = [data["draft_id"] for kind, data in sent if kind == "draft"]
    draft = call(app, "GET", f"/api/drafts/{draft_id}", ANA).json()

    assert draft["lang"] == "fr"
    assert draft["removed"] == [] and draft["checks"]["checks_run"] == [1, 2, 3, 4, 5, 6]
    sentences = [sentence for note in draft["notes"] for sentence in note["sentences"]]
    assert len(sentences) == draft["checks"]["sentences"]["written"] == 7
    assert all(LangidDetector().detect(sentence["text"]).code == "fr" for sentence in sentences)
    quoted = [sentence["text"] for sentence in sentences if '"' in sentence["text"]]
    description = next(note["description"] for note in draft["notes"]
                       if note["activity_reference_no"] == "KE-NWWDA-541055-CW-RFB")
    assert len(quoted) == 1 and "Tarbaj Water Supply" in description and '"Tarbaj Water Supply"' in quoted[0]

    act(app, draft_id, "check", "draft")
    exported = act(app, draft_id, "export", "checked").json()
    [docx] = [file["name"] for file in exported["export"]["files"] if file["name"].endswith(".docx")]
    parts = zipfile.ZipFile(io.BytesIO(call(app, "GET", f"/api/drafts/{draft_id}/files/{docx}", ANA).content))
    document = ElementTree.fromstring(parts.read("word/document.xml"))
    w = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

    def locale(run):
        found = run.find(f"{w}rPr/{w}lang")
        return None if found is None else found.get(f"{w}val")

    runs = [(("".join(t.text for t in run.iter(f"{w}t"))), locale(run)) for run in document.iter(f"{w}r")]
    french = [text for text, where in runs if where == "fr-FR"]
    assert sentences[0]["text"] in french
    # The quote keeps its source's English, and the headings and origin keep the Normal style's English.
    assert ("Tarbaj Water Supply", "en-US") in runs
    heading = next(text for text, _ in runs if text.startswith("Review notes on"))
    assert (heading, None) in runs and 'w:lang w:val="en-US"' in parts.read("word/styles.xml").decode()


def drafting_app(fixture_db, tmp_path, case):
    from strata.agent.runs import RunLog
    from strata.agent.scripted import WRITER_CASES, ScriptedAgent, load_cases
    from strata.config import load_roles
    from strata.drafts.store import DraftStore
    from strata.lakehouse import catalog
    from strata.server.access import Access, StaticGroups
    from strata.server.evidence import OpenedLog
    from test_drafts import GROUPS, Clock

    state_db = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)

    @contextmanager
    def reading(viewer):
        with DuckDBEngine.open(fixture_db, read_only=True) as engine:
            yield engine

    def state():
        return DuckDBEngine.open(state_db)

    clock = Clock(dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC))
    written = load_cases(WRITER_CASES)[case]
    numbers = iter(range(1, 100))
    return create_app(engine_for=reading, drafts=DraftStore(state), opened=OpenedLog(state, now=clock),
                      writers=lambda kind: ScriptedAgent(written), runs=RunLog(state),
                      access=Access(load_roles(), StaticGroups(GROUPS)), today=lambda: TODAY, now=clock,
                      new_draft_id=lambda: f"draft-{next(numbers):04d}", new_run_id=lambda: "run-0001")


# ── Where the language of answers and drafts comes from (the 42 brief, section 6.1) ──

def identity(app, headers, address=""):
    from test_drafts import call

    language = call(app, "GET", f"/api/me{address}", headers).json()["language"]
    assert [choice["code"] for choice in language.pop("choices")] == ["en", "fr", "es", "pt"]
    return language


def settings_app(tmp_path, groups=None, roles=None):
    from strata.config import load_roles
    from strata.lakehouse import catalog
    from strata.server.access import Access, StaticGroups
    from strata.server.viewer_settings import SettingsStore
    from test_drafts import GROUPS, Clock

    state_db = tmp_path / "state.duckdb"
    with DuckDBEngine.open(state_db) as engine:
        catalog.build(engine)
    clock = Clock(dt.datetime(2026, 10, 23, 14, 0, tzinfo=dt.UTC))
    return create_app(settings=SettingsStore(lambda: DuckDBEngine.open(state_db)), now=clock,
                      access=Access(roles or load_roles(), StaticGroups(groups or GROUPS)))


def test_a_link_s_language_comes_first_then_the_saved_choice_then_the_team_s_then_english(tmp_path):
    """A link never changes the saved choice; a value no working language matches is named unknown, and the language
    in effect falls back to the saved choice."""
    import dataclasses

    from strata.config import load_roles
    from test_drafts import ANA, BEN, call

    roles = load_roles()
    kenya = next(team for team in roles.teams if "strata-team-kenya-water" in team.groups)
    french_team = dataclasses.replace(roles, teams=tuple(dataclasses.replace(team, working_language="fr")
                                                         if team.key == kenya.key else team for team in roles.teams))
    app = settings_app(tmp_path, roles=french_team)

    assert identity(app, ANA) == {"code": "fr", "source": "team", "saved": None, "team": "fr", "link": None,
                                  "saved_readable": True}
    assert call(app, "PUT", "/api/me/working-language", ANA, json={"code": "es"}).status_code == 204
    assert identity(app, ANA) | {"team": None} == {"code": "es", "source": "saved", "saved": "es", "team": None,
                                                   "link": None, "saved_readable": True}
    assert identity(app, ANA, "?lang=PT_br")["code"] == "pt"
    linked = identity(app, ANA, "?lang=fra")
    assert (linked["code"], linked["source"], linked["saved"], linked["link"]) == ("fr", "link", "es", "fr")
    unknown = identity(app, ANA, "?lang=xx")
    assert (unknown["code"], unknown["source"], unknown["link"]) == ("es", "saved", "unknown")
    # A link never saved anything, and Ben, on the same team, has his own choice: none yet.
    assert identity(app, ANA)["saved"] == "es"
    assert identity(app, BEN)["code"] == "fr"


def test_choosing_a_language_takes_only_a_working_language_and_a_signed_in_viewer(tmp_path):
    from test_drafts import ANA, call

    app = settings_app(tmp_path)

    assert call(app, "PUT", "/api/me/working-language", ANA, json={"code": "de"}).json() == {"code": "unknown_language"}
    assert call(app, "PUT", "/api/me/working-language", ANA, json={"code": "FR"}).status_code == 400
    assert call(app, "PUT", "/api/me/working-language", {}, json={"code": "fr"}).status_code == 401
    assert call(create_app(), "PUT", "/api/me/working-language", ANA, json={"code": "fr"}).status_code == 503


def test_an_english_answer_judged_against_a_french_paragraph_says_so_in_its_check_line(fixture_db):
    """A model judged the summary across two languages, which is weaker than an exact match, so the checks say how many
    judged sentences on screen cite a source in another language (the 42 brief, section 5.5). The quote keeps the
    report's French words, and an English answer to an English question sends no language event."""
    parsed = ask_scripted(fixture_db, "p127203-en-procurement-delays")

    assert of(parsed, "removed") == [] and of(parsed, "language") == []
    checks = of(parsed, "checks")[0]
    assert (checks["shown"]["judged"], checks["shown"]["cross_language"]) == (1, 1)
    quoted = [sentence for sentence in of(parsed, "sentence") if sentence["quote"]]
    [cited] = [item for item in of(parsed, "evidence") if item["id"] == quoted[0]["quote"]["evidence_id"]]
    assert cited["row"]["language"] == "fr" and quoted[0]["quote"]["text"] in cited["row"]["text"]
    # An answer in one language with nothing judged across languages sends what it always sent.
    english = ask_scripted(fixture_db, "p130164-rebidding")
    assert "cross_language" not in of(english, "checks")[0]["shown"]
