"""Ticket 147: ProjectFacts, what a deep research reader knows of the project, built from the project's record: the
recorded or bronze page, else the live projects API through the same fetch, never from memory."""

import json

import pytest
from research_world import ROOT, answers

from strata.research.project import ProjectFacts, project_facts

RECORD = ROOT / "data" / "fixture" / "recorded" / "api" / "projects" / "P156634.json"


def test_the_demo_project_s_facts_come_from_its_recorded_record():
    facts = project_facts("P156634")

    assert (facts.project_id, facts.project_name, facts.country_code, facts.country_name) == (
        "P156634", "Water and Sanitation Development Project", "KE", "Kenya")
    assert (facts.sector_key, facts.sector_name, facts.status) == (
        "water", "Water, Sanitation and Waste Management", "Active")
    assert (facts.closing_date, facts.approval_date) == ("2026-10-31", "2017-04-26")
    assert {"CWWDA", "NWWDA", "MOWASSCO", "WSTF", "Tavevo"} <= set(facts.short_names)
    agencies = {agency.name: agency.short_names for agency in facts.implementing_agencies}
    assert agencies["Coast Water Works Development Agency"] == ("CWWDA",)
    assert "Ministry of Water, Sanitation and Irrigation" in agencies
    baricho = next(location for location in facts.locations if location.geo_loc_id == "200577")
    assert baricho.as_dict() == {"geo_loc_id": "200577", "name": "Baricho Sub-Location", "latitude": -3.1,
                                 "longitude": 39.78333}
    assert baricho.place == "Baricho"
    assert len(facts.locations) == 18
    assert {"Baricho", "Wajir", "Mombasa", "West Pokot", "Garissa"} <= set(facts.place_names)


def test_a_project_with_no_recorded_record_is_read_from_the_live_projects_api_through_the_fetch():
    body = json.loads(RECORD.read_text())["response"]
    body["projects"]["P999999"] = {**body["projects"].pop("P156634"), "id": "P999999"}
    url = "https://search.worldbank.org/api/v3/projects?format=json&id=P999999&fl=*"
    fetch = answers((url, (200, json.dumps(body))))

    facts = project_facts("P999999", fetch=fetch)

    assert isinstance(facts, ProjectFacts) and facts.project_id == "P999999"
    assert fetch.calls == [url]


def test_a_project_no_record_names_stops_with_a_sentence():
    with pytest.raises(LookupError, match="I found no record of P000000"):
        project_facts("P000000")
