# The full rehearsal

Ticket 49's last part runs on the deployed App with a person signed in, so it waits for the workspace. Run it in this order, from the main checkout, after the change drill (`docs/change-drill.md`), and write the results into the tables below. Each step that fails gets a follow-up ticket or a "Designed, not built" line, which is an entry in `config/designed_not_built.toml` and the label at its route, added in the same change.

## 1. The demo-ready command

Run it first, from the main checkout, with the person who will walk the path signed in to the App in the browser the wizard saved:

    uv run --with databricks-sdk==0.156.0 python ops/demo/ready.py --env-file .env

It passed when its last line is `Strata is ready for the demo.` and it exits 0. Run it a second time: its step 6 then prints `No changes.`

| Run | Started | Minutes | Last line | Steps that failed |
|---|---|---:|---|---|
| First | | | | |
| Second | | | | |

## 2. A specialist's path, on the deployed App

Walk the blueprint's "A specialist's path" in the World Bank staff view, signed in as the reviewing panel's test account (`config/examples.toml` names its group). Never walk it in a preview, which can't check or export. Time each step from opening its page to seeing what the "Should show" column names. Compare what the App shows with `tests/ground_truth/values.toml` by the ids given, not with the blueprint's text, which was written for October 22, 2026.

| Step | Where | Should show (values.toml ids) | Started | Seconds | Worked | Follow-up |
|---|---|---|---|---:|---|---|
| 1. Home | `/` | The briefing's first line on KE-NWWDA-229129-CW-RFB, worth watching: signed at US$1,245,092.76 against an estimate of US$300,000 (plan-229129-actual, plan-229129-estimated). | | | | |
| 2. Check a plan | `/projects/P156634/procurement/northern-water-works-development-agency/2026-10-09` | No activity needs a look; KE-NWWDA-229129-CW-RFB is worth watching; KE-NWWDA-541055-CW-RFB and KE-NWWDA-541062-CW-RFQ are moved on since the plan, because the contract awards say each was signed (award-541055-signed, award-541062-signed). P156634 closes October 31, 2026 (closing-date-p156634), so the days left depend on the day of the walk. | | | | |
| 3. Package workspace | Packages, then a new package from a sentence about a rural roads package in Kenya | The past range as dots, the plan as a line through them, and a planned date for each STEP step. | | | | |
| 4. Evidence drawer | An answer about rebidding on P130164, then its citation | ICR paragraph 54 of P130164 on PDF page 23 (icr-para-54), and IEG's review saying it again (icr-review-2023-restates-para-54). | | | | |
| 5. Project timeline | `/projects/P130164/timeline` | ISR 7 of August 26, 2016 rating progress towards the PDO Satisfactory (isr-7-date, isr-7-rating), next to the ICR's paragraph 78 (icr-para-78), with the rule Strata applied. | | | | |
| 6. Drafts | `/drafts` | Risk owners set, the suggested PPSD rows and the review notes marked as checked, and a Word file and a STEP row exported. Nothing is sent. | | | | |
| 7. Projects you follow | `/projects/following` | The mission brief lists lapsed dates, an amount far above its estimate (plan-229129-actual) and a late direct-selection activity, KE-CWSB-567630-CW-DIR. | | | | |
| 8. Lessons | `/lessons` | A lesson's row with what it was and what it is now, and "Update this row". | | | | |

Before the demo, the awards dataset already disagreed with the plan of October 9, 2026 (`data/fixture/README.md`, "Before demo day"). It shows KE-NWWDA-541055-CW-RFB signed on June 22, 2026 (award-541055-signed, contract 1903781) and KE-NWWDA-541062-CW-RFQ signed on May 11, 2026 (award-541062-signed). So steps 1 and 2 may show something other than the blueprint on live data. Write down what they show as a finding for the demo's story, not as a failure: which story the demo tells is the user's choice (`docs/STATUS.md`, decisions 4 and 7).

Steps 6 and 8 write rows to `strata.ops` on the shared workspace, as the test account. They stay with that account. If they must go, a row leaves only through a `DELETE` with a `WHERE` that names that account (CLAUDE.md rule 5).
