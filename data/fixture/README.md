# The fixture

The fixture is a small, real, offline copy of the World Bank sources behind Strata's demo and showcase. Every offline test reads it, and the gate builds it into `data/out/fixture.duckdb` with no network.

- The demo plan is the Northern Water Works Development Agency's Procurement Plan of October 9, 2026 for the Kenya Water and Sanitation Development Project (P156634). The project has many more plan versions than the fixture holds. It keeps only the ones the tests need:
  - the agency's plan of April 21, 2021, the first to list KE-NWWDA-229129-CW-RFB, and its version just before it, of December 7, 2020;
  - the agency's plan of March 5, 2026, the first to list KE-NWWDA-541055-CW-RFB, and its version just before it, of July 21, 2025;
  - the Ministry of Water and Irrigation's plan of November 8, 2019, the first to list NWWDA-WSDP-03-2019-2020, its version just before it, of August 26, 2019, and its plan of April 30, 2020;
  - the Coast Water Services Board's plan of August 17, 2026, the first to list KE-CWSB-567630-CW-DIR, and its version just before it, of July 31, 2026;
  - the Kilifi - Mariakani Water and Sewerage Company's latest plan, of March 19, 2025, which marks three comparables Canceled.

  It also holds the project's PAD and its 19 ISRs, every notice and award for the project, and its credits' monthly history.
- The showcase is the India Rajasthan Road Sector Modernization Project (P130164): its PAD (a scan), its 13 ISRs, the ICR of October 10, 2019, IEG's ICR Review of March 27, 2020 and its re-issue of May 4, 2023, its notices and its awards from the FY2001 to FY2016 dataset.
- The comparable works packages are 52 Kenya works packages under Request for Bids: 45 signed, three canceled and four still open. `tests/ground_truth/values.toml` lists them with the default criteria.
  - 48 come from P156634's notices and awards. Two of the signed ones have no row in the awards dataset, and only their award notices give the signing date. The three canceled ones are marked Canceled in their agency's plan of March 19, 2025.
  - The four still open come from P176758 and P170941. The fixture holds every notice for each of the four and every award row for the two projects. Their bids were due after October 9, 2026, the demo plan's date.
- CPIA and WGI cover Kenya and India. IEG ratings and IDA credits cover the two projects.

## What is here

| Path | What it holds |
|---|---|
| `sources.toml` | Every source: where it comes from, the file it is recorded in, and the dataset whose attribution and license line the file carries |
| `recorded/api/` | API responses, one JSON file each, with the keys `source`, `license`, `recorded`, `about` and `response` |
| `recorded/documents/<project>/<name>.txt` | The text the World Bank publishes for a document, byte for byte, after a few header lines |
| `recorded/documents/<project>/<name>.pages.txt` | The text of each PDF page of the same document, one page after each form feed, read from the PDF's text layer |
| `recorded/documents/<project>/<name>.words.json` | For each Procurement Plan (`words = true` in `sources.toml`), every word on each PDF page with its box, read with poppler's `pdftotext -bbox`. Offline, the layout parser reads the plans' tables from these words, because `ai_parse_document` runs only on the workspace |
| `placeholder/` | Five plan rows that ticket 01 typed in. Ticket 08 replaces them with rows read from the recorded plans |

The gate loads these files into the schema `strata.recorded`. The `recorded` schema is the fixture's copy of the sources, not a catalog layer. The public-date check covers bronze, silver, gold and ops, which ticket 07 builds from it.

Every recorded file starts with its source and its license line, which is CC BY 4.0. Notices keep their contact names, emails and phone numbers on purpose, because the lakehouse must strip them at ingestion (CLAUDE.md rule 8).

The pages file exists because the published text does not always mark pages. The text of the newest plans has no form feeds at all, and the P130164 PAD's text has none either. The pages file gives every document the PDF page numbers that citations need.

## Before demo day

The October 9, 2026 plan is the ground truth for the demo, and `values.toml` keeps the plan's own values. Two of its rows disagree with the awards dataset:

- KE-NWWDA-541055-CW-RFB. The plan shows no signed contract. The awards dataset shows contract 1903781, signed June 22, 2026 at US$1,287,515.60, and award notice OP00474946 was published on October 13, 2026.
- KE-NWWDA-541062-CW-RFQ. The plan says Pending Implementation. The awards dataset shows contract 1903551, signed May 11, 2026.

Refresh the fixture and recheck both rows' signals before the demo. Then decide whether the demo still leads with "no signed contract" for KE-NWWDA-541055-CW-RFB, or tells the story of the plan and the award row disagreeing. `values.toml` records the award rows as `award-541055-signed`, `award-541055-amount`, `award-notice-541055` and `award-541062-signed`.

The four comparables still open may be signed or canceled after their bids are due in October and November 2026. A refresh then fails the comparable test for that package. Move it to signed (with `contract`, `signed` and `review_type`) or canceled in `values.toml`, and update the counts. If fewer than three stay open, record another Kenya works package under Request for Bids that was still open on the plan's date.

## Refresh it

Run the recording command. It needs the network, so it is never a gate step.

    uv run python -m strata.fixture.record

It fetches every source again and prints a diff against the recorded files. It writes nothing until you run it again with `--write`. A file whose content did not change keeps its Recorded date. The command ignores the `as_of_date` that Finances One stamps on each row every day. To refresh a few sources, pass `--only` with part of their file names, for example `--only P156634`. Recording a plan's words needs poppler's `pdftotext` on this computer (`brew install poppler`).

After a refresh, run the gate. The tests in `tests/test_ground_truth_values.py` check every value in `tests/ground_truth/values.toml` against the recorded files, so a source that changed shows up as a failing value. Update that value only when the source really changed, and say so in the commit.

## Add a source

Add a `[[source]]` entry to `sources.toml`, then record it with `--only` and `--write`. The size limits in `sources.toml` keep the gate well under two minutes, and a test checks them.
