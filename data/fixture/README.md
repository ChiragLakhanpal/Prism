# The fixture

The fixture is a small, real, offline copy of the World Bank sources behind Strata's demo and showcase. Every offline test reads it, and the gate builds it into `data/out/fixture.duckdb` with no network.

- The demo plan is the Northern Water Works Development Agency's Procurement Plan of October 9, 2026 for the Kenya Water and Sanitation Development Project (P156634). The fixture also holds the agency's earlier plan versions, the Coast Water Services Board's plan of August 17, 2026 (the first to list KE-CWSB-567630-CW-DIR), the project's PAD and its 19 ISRs, every notice and award for the project, and its credits' monthly history.
- The showcase is the India Rajasthan Road Sector Modernization Project (P130164): its PAD (a scan), its 13 ISRs, the ICR of October 10, 2019, IEG's ICR Review of March 27, 2020 and its re-issue of May 4, 2023, its notices and its awards from the FY2001 to FY2016 dataset.
- The comparable works packages are the 48 Kenya works packages under Request for Bids in P156634's notices and awards: 45 signed and 3 still open. Two of the signed ones have no row in the awards dataset, and only their award notices give the signing date. `tests/ground_truth/values.toml` lists them with the default criteria.
- IEG ratings, IDA credits, CPIA and WGI cover Kenya and India.

## What is here

| Path | What it holds |
|---|---|
| `sources.toml` | Every source: where it comes from, the file it is recorded in, and the dataset whose attribution and license line the file carries |
| `recorded/api/` | API responses, one JSON file each, with the keys `source`, `license`, `recorded`, `about` and `response` |
| `recorded/documents/<project>/<name>.txt` | The text the World Bank publishes for a document, byte for byte, after a few header lines |
| `recorded/documents/<project>/<name>.pages.txt` | The text of each PDF page of the same document, one page after each form feed, read from the PDF's text layer |
| `placeholder/` | Five plan rows that ticket 01 typed in. Ticket 08 replaces them with rows read from the recorded plans |

Every recorded file starts with its source and its license line, which is CC BY 4.0. Notices keep their contact names, emails and phone numbers on purpose, because the lakehouse must strip them at ingestion (CLAUDE.md rule 8).

The pages file exists because the published text does not always mark pages. The text of the newest plans has no form feeds at all, and the P130164 PAD's text has none either. The pages file gives every document the PDF page numbers that citations need.

## Refresh it

Run the recording command. It needs the network, so it is never a gate step.

    uv run python -m strata.fixture.record

It fetches every source again and prints a diff against the recorded files. It writes nothing until you run it again with `--write`. A file whose content did not change keeps its Recorded date. The command ignores the `as_of_date` that Finances One stamps on each row every day. To refresh a few sources, pass `--only` with part of their file names, for example `--only P156634`.

After a refresh, run the gate. The tests in `tests/test_ground_truth_values.py` check every value in `tests/ground_truth/values.toml` against the recorded files, so a source that changed shows up as a failing value. Update that value only when the source really changed, and say so in the commit.

## Add a source

Add a `[[source]]` entry to `sources.toml`, then record it with `--only` and `--write`. The size limits in `sources.toml` keep the gate well under two minutes, and a test checks them.
