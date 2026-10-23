# The fixture

The fixture is a small, real, offline copy of the World Bank sources behind Strata's demo and showcase. Every offline test reads it, and the gate builds it into `data/out/fixture.duckdb` with no network.

- The demo plan is the Northern Water Works Development Agency's Procurement Plan of October 9, 2026 for the Kenya Water and Sanitation Development Project (P156634). The project has many more plan versions than the fixture holds. It keeps only the ones the tests need:
  - four of the agency's earlier versions: April 21, 2021, the first to list KE-NWWDA-229129-CW-RFB, and March 5, 2026, the first to list KE-NWWDA-541055-CW-RFB, each with the agency's version just before it;
  - two Ministry of Water and Irrigation versions that list NWWDA-WSDP-03-2019-2020;
  - the Coast Water Services Board's plan of August 17, 2026, the first to list KE-CWSB-567630-CW-DIR, and its version just before it, of July 31, 2026.

  It also holds the project's PAD and its 19 ISRs, every notice and award for the project, and its credits' monthly history.
- The showcase is the India Rajasthan Road Sector Modernization Project (P130164): its PAD (a scan), its 13 ISRs, the ICR of October 10, 2019, IEG's ICR Review of March 27, 2020 and its re-issue of May 4, 2023, its notices and its awards from the FY2001 to FY2016 dataset.
- The comparable works packages are the 48 Kenya works packages under Request for Bids in P156634's notices and awards: 45 signed and three still open. Two of the signed ones have no row in the awards dataset, and only their award notices give the signing date. `tests/ground_truth/values.toml` lists them with the default criteria.
- CPIA and WGI cover Kenya and India. IEG ratings and IDA credits cover the two projects.

## What is here

| Path | What it holds |
|---|---|
| `sources.toml` | Every source: where it comes from, the file it is recorded in, and the dataset whose attribution and license line the file carries |
| `recorded/api/` | API responses, one JSON file each, with the keys `source`, `license`, `recorded`, `about` and `response` |
| `recorded/documents/<project>/<name>.txt` | The text the World Bank publishes for a document, byte for byte, after a few header lines |
| `recorded/documents/<project>/<name>.pages.txt` | The text of each PDF page of the same document, one page after each form feed, read from the PDF's text layer |
| `placeholder/` | Five plan rows that ticket 01 typed in. Ticket 08 replaces them with rows read from the recorded plans |

The gate loads these files into the schema `strata.recorded`. The `recorded` schema is the fixture's copy of the sources, not a catalog layer. The public-date check covers bronze, silver, gold and ops, which ticket 07 builds from it.

Every recorded file starts with its source and its license line, which is CC BY 4.0. Notices keep their contact names, emails and phone numbers on purpose, because the lakehouse must strip them at ingestion (CLAUDE.md rule 8).

The pages file exists because the published text does not always mark pages. The text of the newest plans has no form feeds at all, and the P130164 PAD's text has none either. The pages file gives every document the PDF page numbers that citations need.

## Before demo day

The October 9, 2026 plan is the ground truth for the demo, and `values.toml` keeps the plan's own values. Two of its rows disagree with the awards dataset:

- KE-NWWDA-541055-CW-RFB. The plan shows no signed contract. The awards dataset shows contract 1903781, signed June 22, 2026 at US$1,287,515.60, and award notice OP00474946 was published on October 13, 2026.
- KE-NWWDA-541062-CW-RFQ. The plan says Pending Implementation. The awards dataset shows contract 1903551, signed May 11, 2026.

Refresh the fixture and recheck both rows' signals before the demo. Then decide whether the demo still leads with "no signed contract" for KE-NWWDA-541055-CW-RFB, or tells the story of the plan and the award row disagreeing. `values.toml` records the award rows as `award-541055-signed`, `award-541055-amount`, `award-notice-541055` and `award-541062-signed`.

## Refresh it

Run the recording command. It needs the network, so it is never a gate step.

    uv run python -m strata.fixture.record

It fetches every source again and prints a diff against the recorded files. It writes nothing until you run it again with `--write`. A file whose content did not change keeps its Recorded date. The command ignores the `as_of_date` that Finances One stamps on each row every day. To refresh a few sources, pass `--only` with part of their file names, for example `--only P156634`.

After a refresh, run the gate. The tests in `tests/test_ground_truth_values.py` check every value in `tests/ground_truth/values.toml` against the recorded files, so a source that changed shows up as a failing value. Update that value only when the source really changed, and say so in the commit.

## Add a source

Add a `[[source]]` entry to `sources.toml`, then record it with `--only` and `--write`. The size limits in `sources.toml` keep the gate well under two minutes, and a test checks them.
