# 120: A project record's grants, trust funds and suffixed loans are kept as financing numbers

**What to build:** On October 28, 2026 the live check of ticket 63's step 4 compared every `loan_transactions[].financier_loan` a project record names in `strata.bronze.current_pages` (source projects) with `strata.silver.project_loans`: of 14,686 distinct project-and-number pairs, 3,989 have no row, none of them a four-digit loan (ticket 63's own criterion holds). The missing numbers are the forms `clean.loan_number` does not read: IDA grants with an H (954 pairs, IDA-H0010 to IDA-H9990), trust funds and co-financing with letters or five digits (TF-D2212, COFN-00280 to COFN-04660, 140 five-digit pairs), and loans with a suffix letter (IBRD-2075S; 2,895 pairs in all under "other"). A project financed by an IDA grant, which is most of the slice's poorer countries, therefore has no financing row at all, so a notice or plan that names its grant number cannot be tied to its project the way a loan number is. Keep every number the projects API names: `src/strata/lakehouse/silver/projects.py` keeps a financing number as its lender and digits when `clean.loan_number` reads it, and otherwise as the lender prefix and the rest of the number as written (upper case, one hyphen), in the same table and columns (`loan_number`, `loan_number_as_written`), with the lender in a new column `financier` (IBRD, IDA, TF, COFN and the others the records name) so a reader can tell a grant from a loan; `strata.gold.project_loan` carries the column; the fixture's measures and the ground-truth SQL that count loans state whether grants are in (the glossary entry for loan number says what counts). The ticket holds the one place the rule lives (`clean.loan_number` and the keep rule in projects.py), its tests on the fixture's project records (an IDA-H grant, a TF number, a COFN number, a suffixed loan, each kept with its lender), and the live check below. Touch no notice or plan reader: how a notice names a grant is ticket 07's and stays.

Read first: `src/strata/lakehouse/silver/projects.py` (the loans block), `src/strata/lakehouse/clean.py` (`loan_number`, its five forms), `src/strata/lakehouse/tables/silver/project_loans.sql`, `src/strata/lakehouse/gold/project_loan.sql`, `GLOSSARY.md` (loan number), the catch-up file's block "Ticket 63, step 4 of 5 ran" of October 28.

**Blocked by:** None (can start immediately)

**Status:** ready
**Area:** data
**Phase:** P4
**Design review:** no

- [ ] Every `financier_loan` a project record names on the fixture is a row of `strata.silver.project_loans` with its `financier`, proven by a test that walks the fixture's project records the way the live check did; a four-digit loan is still kept as before.
- [ ] `strata.gold.project_loan` carries `financier`; the table definitions add the column with an `ALTER TABLE ... ADD COLUMNS` line for a workspace whose table is older, written in the ticket's catch-up block; the measures and ground-truth queries that count loans say whether grants count, and `GLOSSARY.md` says what a loan number covers.
- [ ] After the merge, the bundle deploy and a `bronze_to_gold` run that reads every projects page again (the projects transform's VERSION bumped), the live comparison of the catch-up block "Ticket 63, step 4 of 5 ran" finds 0 missing pairs on the paid workspace (recorded in the catch-up file under this ticket).

## Comments

- October 28, 2026, orchestrator: opened at 03:40 PDT on the orchestrator's judgment from ticket 63's step 4 live check; it builds in wave 4u.
