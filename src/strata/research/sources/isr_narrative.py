"""isr_narrative: what the World Bank's own last two ISRs say about implementation (ticket 147). No network.

From strata.gold.passage, as of the run's day: the passages of the newest ISRs (settings.reports, two) whose section is
Implementation Status and Key Decisions, and the passages of the results indicators that hold the "Comments on
achieving targets" (config/research.toml names both by section number and, for an ISR from before 2020, by name).
Each passage is one item cited to its document and PDF page, with the PDF's address at that page.
"""

from __future__ import annotations

import datetime as dt

from strata.config import ResearchSource
from strata.research.items import iso, make_item
from strata.research.project import ProjectFacts
from strata.research.sources import SourceResult, as_of, long_date, rows

STATUS = "Implementation Status and Key Decisions"
RESULTS = "Results indicators, comments on achieving targets"


def _in(section: str, paths, names) -> bool:
    section = (section or "").strip()
    return (any(section == path or section.startswith(path + ".") for path in paths)
            or any(section.lower().startswith(name.lower()) for name in names))


def section_of(passage: dict, settings: dict) -> str | None:
    """Which kept section a passage is in, or None."""
    section = passage["section_path"]
    if _in(section, settings.get("status_paths", ()), settings.get("status_sections", ())):
        return STATUS
    if (_in(section, settings.get("results_paths", ()), settings.get("results_sections", ()))
            and settings.get("results_phrase", "").lower() in (passage["text"] or "").lower()):
        return RESULTS
    return None


def read(source: ResearchSource, project: ProjectFacts, fetch, engine, now: dt.datetime) -> SourceResult:
    settings = source.settings
    if engine is None:
        return SourceResult(source.key, [], False, "no database", "Prism had no lakehouse to read the ISRs from.")
    passages = rows(engine, "isr_passages", project_id=project.project_id, as_of=as_of(now),
                    document_type=settings.get("document_type", "Implementation Status and Results Report"))
    newest = list(dict.fromkeys(passage["document_id"] for passage in passages))[:int(settings.get("reports", 2))]
    page = settings.get("documents_page", "").format(project_id=project.project_id)
    items = []
    for passage in passages:
        section = section_of(passage, settings) if passage["document_id"] in newest else None
        if section is None:
            continue
        pdf_page = passage["pdf_page"]
        url = f"{passage['pdf_url']}#page={pdf_page}" if passage["pdf_url"] and pdf_page else page
        report = passage["report_number"] or passage["document_id"]
        items.append(make_item(
            project=project, source=source, item_key=f"{passage['document_id']}-p{pdf_page}-{passage['paragraph']}",
            public_from=passage["public_from"], published=passage["document_date"],
            title=f"ISR {report}, {long_date(passage['document_date'])}: {section}, page {pdf_page}",
            text=passage["text"], url=url, read_on=as_of(now), author="World Bank", url_of_source=page or None))
    dates = sorted({iso(passage["document_date"]) for passage in passages if passage["document_id"] in newest},
                   reverse=True)
    note = (f"Prism read {len(items)} passages of the {len(newest)} newest ISRs, of "
            f"{' and '.join(long_date(day) for day in dates)}." if newest else
            f"The lakehouse holds no ISR of {project.project_id} made public by {long_date(as_of(now))}.")
    return SourceResult(source.key, items, True, "read", note)
