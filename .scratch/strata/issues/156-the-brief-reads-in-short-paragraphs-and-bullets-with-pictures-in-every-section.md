# 156: The brief reads in short paragraphs and bullets, with pictures in every section, and prints with room to breathe

**What to build:** The user's feedback on the brief's PDF, November 5, 2026 at about 22:00 PST, applied to the Deep research tab (ticket 149) and its print, which is what "Download as PDF" produces:

1. **Readable.** The writer's instruction (`src/strata/agent/instructions/research_brief_writer.md`) asks for short paragraphs of at most two sentences in "the picture", and for one sentence per bullet in developments, by site and the questions; voices stay as quotes with their attribution line. The tab renders developments, by-site items and questions as bulleted or numbered lists, each bullet one sentence with its markers, and the picture as short paragraphs. Re-record the writer's answer for the seeded P156634 run in that shape (ops/agent/record.py --research, or by hand following the sample's facts), keep the verifier at 70 kept, and re-record the API fixtures.
2. **Pictures in every section, for the demo.** Satellite: the Sentinel-2 grids for two or three sites per project, side by side, already in the seeds. Field photos: a demo set of sample photos per project, seeded as field photos of the demo's staff team (the viewer the demo signs in as; see how ticket 150 keys the team), taken from the openly licensed photos already recorded near the sites (the Wikimedia Commons recordings under `.notes/prism-sample/sample/` and `.notes/prism-sample/news/` in the main checkout: Wajir, Isiolo, Mombasa, Marsabit; fetch two or three more per project with the named client from Commons geosearch within 10 km of each site if the recordings lack them), each with a caption that says what it is ("Sample photo standing in for a staff photo: Wikimedia Commons, by <author as the file page prints>, CC BY-SA 4.0, taken <date>") so nothing claims a World Bank staff member took it; the photo files go in the seed's fixture folder and, on the workspace, into the `strata.ops.field_photos` volume through the photo route's own store (`ops/research/seed.py --photos`, a new flag, or a sibling script). The brief's field-photo lines cite the caption and the date, never the pixels (ticket 150's rule). Complaints: the section lists the register's cases for the project's country when none names the project ("none names this project; two name other Kenya projects: ..."), with their links. Social: the posts the run holds, with a line saying when none is about the works.
3. **Layout.** On screen and in print: a visible band or rule that opens each main section (the sample's navy rule under the section title, or a light band), a page break before each main heading in print, the footer reduced to the page number only (no repeated disclaimer; the one-line disclaimer stays once, on the last page), the Prism mark drawn no taller than the World Bank logo beside it (the logo is 24 px in the bar and 28 px on the cover; the mark matches, and the wordmark sits at the logo's cap height), and the two cover sentences removed: "Read on November 5, 2026 · 16 public sources outside the World Bank's records, set against the Bank's last two status reports · for World Bank staff" and "Sample document · Prism is an independent demo built on World Bank open data; it is not a World Bank product." The cover keeps the project line and the closing date. The tab's print test (ticket 149) is updated to the new sheets.

Then print the seeded P156634 brief to a PDF with Playwright and save it as `.notes/prism-sample/prism-deep-research-P156634-v6.pdf` in the main checkout, so the user can see the format in the morning. Keep the gate under 180 seconds.

Build this in the ticket's worktree on a branch from `build/strata`'s HEAD (caa3287e or later). Essentials only, no review rounds. Commit with plain-English messages and no trailers. Do not change ticket files, docs/STATUS.md or anything under .scratch. Report within 75 minutes: branch and worktree, each change with its evidence, the photo seed's counts per project, the PDF's path, the gate's time, and the workspace steps (the photo files into the volume, a redeploy, the five briefs written again).

**Blocked by:** None (can start immediately)

**Status:** in-progress
**Area:** app
**Phase:** P5
**Design review:** no

- [ ] The brief's sections read as short paragraphs and one-sentence bullets, on screen and in print, with the P156634 replay still at 70 kept (tests).
- [ ] Every section carries content for the five seeded projects: satellite grids, sample field photos with honest captions, complaints and social lines (the seed's counts, and the printed P156634 PDF).
- [ ] The print has a rule or band per section, a page break per main heading, a page-number-only footer, the Prism mark at the logo's size, and no cover sentences about the run or the sample (the print test and the PDF).
- [ ] The gate passes under 180 seconds on the worktree.

## Comments

- November 5, 2026, orchestrator: opened at about 22:00 PST from the user's feedback on the sample PDF; the format ships in the third deploy of the night.
