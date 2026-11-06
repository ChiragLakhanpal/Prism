# Formal complaints in deep research

By Surya Yadav, November 6, 2026

Deep research checks whether people affected by a project have asked the World Bank's Inspection Panel for a case. The design comes from my ProcIntel work. Prism's reader is `src/strata/research/sources/inspection_panel.py`, and its entry in the registry is `[sources.inspection_panel]` in `config/research.toml`.

## What it reads

The Inspection Panel is the World Bank's independent body that hears complaints from people who say a Bank-financed project harmed them. Its public case register is at https://www.inspectionpanel.org/panel-cases/data.

The reader makes one call to that page with Prism's named client, `prism-research/0.1`. The page holds its cases in its Drupal settings, under `drupalSettings.extractCases`. That is a list of each case's node id and its title. A case's title names the projects it is about by their project IDs, such as P153836. The reader waits at least two seconds between two calls and reuses an answer for 24 hours.

## How a case is matched to a project

The reader finds every project ID in each case title, written as P followed by six digits. A case is kept when one of those IDs is the project's own ID.

- Each kept case is one item. Its text is the case title, and its link opens the case's own page, `https://www.inspectionpanel.org/node/<node id>`.
- The register prints no date for a case, so the item is marked undated.
- No case for the project gives no item, and the source still counts as reached.

The reader matches on the project ID only. It does not match a case by the project's country.

On November 5, 2026 the register listed 197 cases, and none named P156634. For P153836 it found one case, node 1086, whose title begins "High Priority Roads Reopening and Maintenance".

## When the register does not answer

When the page answers 403, 429 or a bot check page, or holds no list of cases, the source is not reached. The note says why in one sentence, and Prism keeps no item from it. Prism never pretends to be a browser to get past a refusal.

## What the brief says when no case names the project

The reader's note gives the count, such as "The Inspection Panel's register lists 197 cases, 0 of them naming P156634." The brief writer is told to say, in the section on what the run could not see, that no case in the register names the project, and to cite the source's coverage record (`src/strata/agent/instructions/research_brief_writer.md`).

The writer is also told to name the cases the note lists for the project's country, if the note names any. Today the note names none, because the reader does not match by country. Listing the country's cases is the next step for this reader.

## What it cannot show

The registry lists this limit: the register lists the cases the Panel registered, so a complaint made only to the project's own grievance mechanism is not in it.

Procurement complaints are a different record. A bidder's complaint about a tender, and how it was handled, is restricted and stays in STEP, the World Bank's system for recording a project's procurement. Prism cannot see it today.

## Where the complaints log would come from

If the World Bank gave Prism access, the complaints log would come from STEP, read as the signed-in viewer so each person sees only what STEP lets them see. It would be one more source in `config/research.toml` with its own reader, like the Inspection Panel. Until then, Prism refuses to comment on procurement complaints, and the brief says only what the Panel's public register shows.
