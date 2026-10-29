// Mission brief content (DESIGN.md section 5; the 37 brief, sections 7.2 and 7.3): the five parts in the ticket's
// order, Latest Procurement Plans, Awards since the last ISR, Rating history, Disbursement and Closing check, each an
// h3 with its cited sentences first and a table of the records they rest on second. Every value in a table is
// project_records' own (the draft keeps the records), so the browser counts and sums nothing; a total row is the
// tool's. A part with no records says why in one first-person sentence; a part whose sentences were all removed
// keeps its table, and so does a part the writer refused, which says so in its refusal's words. Ratings and awards
// run oldest first, and awards fold after 10 rows on screen.
//
// Inside the document column a table becomes a list of blocks below 640 px (40rem): each row's key as an h4, the
// other cells as a definition list. Both are in the page, and the container query shows one.
import { useState, type ReactNode } from "react";
import { copy } from "../copy";
import { Abbr } from "./Abbreviations";
import type { EvidenceEvent } from "../lib/answer";
import type { BriefRecord, DraftNote } from "../lib/drafts";
import { formatCount, formatDate, formatNumber } from "../lib/format";
import { cx } from "../lib/cx";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { IdText } from "./ProjectId";
import { NoteSentences, type OpenSource } from "./DraftNotes";
import { TextLink } from "./TextLink";

const words = copy.mission;
const kindWords = copy.draft.kinds.mission_brief;
const AWARDS_SHOWN = 10;

type Cell = { text: ReactNode; numeric?: boolean };
type Table = { head: string[]; rows: { key: string; cells: Cell[] }[]; foot?: Cell[] };

const field = (row: BriefRecord, key: string) => row.fields.find((one) => one.key === key)?.value;
const table = (iso: string | null | undefined) => (iso ? formatDate(iso, { style: "table" }) : "");
const usd = (value: unknown) => (value === undefined || value === null || value === "" ? "" : formatNumber(Number(value), { decimals: 2, compact: false }));
const muted = (text: string): Cell => ({ text: <span className="text-ink-muted">{text}</span> });

function tableOf(note: DraftNote): Table | null {
  const rows = note.table ?? [];
  const head = words.cols[note.key] ?? [];
  if (note.key === "plans") {
    if (!rows.length) return null;
    const read = rows.map((row) => ({
      key: row.evidence_id,
      cells: [
        { text: field(row, "implementing_agency") },
        {
          // The version's plan check (the 37 brief, section 7.3).
          text: (
            <TextLink href={`/projects/${row.source.project_id}/procurement/${field(row, "agency_id")}/${field(row, "plan_date")}`}>
              <Fill template={words.planVersion} slots={{ date: table(field(row, "plan_date")) }} />
            </TextLink>
          ),
        },
        { text: formatNumber(field(row, "activities")), numeric: true },
        { text: formatNumber(field(row, "needs_a_look")), numeric: true },
        { text: formatNumber(field(row, "watch")), numeric: true },
      ],
    }));
    const unread = (note.agencies_without_plans ?? []).map((name) => ({
      key: name,
      cells: [{ text: name }, muted(words.noPlan), muted(""), muted(""), muted("")],
    }));
    return { head, rows: [...read, ...unread] };
  }
  if (note.key === "awards") {
    if (!rows.length) return null;
    return {
      head,
      rows: rows.map((row) => ({
        key: row.evidence_id,
        cells: [
          {
            text: (
              <>
                <IdText id={String(field(row, "step_reference") ?? row.reference)} />
                {field(row, "contract_description") && <span className="block text-small text-ink">{field(row, "contract_description")}</span>}
              </>
            ),
          },
          { text: table(field(row, "signed_on")) },
          { text: field(row, "supplier") ?? (field(row, "individual_consultant") ? words.individual : "") },
          { text: usd(field(row, "signed_amount_usd")) || `${field(row, "currency") ?? ""} ${field(row, "signed_amount") ?? ""}`.trim(), numeric: true },
          { text: usd(field(row, "estimated_amount_usd")), numeric: true },
        ],
      })),
    };
  }
  if (note.key === "ratings") {
    if (!rows.length) return null;
    const isrs: { sequence: number; date: string; pdo?: string; implementation?: string; key: string }[] = [];
    for (const row of rows) {
      const sequence = Number(field(row, "sequence"));
      let isr = isrs.find((one) => one.sequence === sequence);
      if (!isr) {
        isr = { sequence, date: String(field(row, "isr_date")), key: row.evidence_id };
        isrs.push(isr);
      }
      isr[field(row, "rating_key") as "pdo" | "implementation"] = String(field(row, "current_rating") ?? "");
    }
    return {
      head,
      rows: isrs.map((isr) => ({
        key: isr.key,
        cells: [
          { text: <Fill template={words.isr} slots={{ n: String(isr.sequence) }} /> },
          { text: table(isr.date) },
          isr.pdo ? { text: isr.pdo } : muted(words.notRated),
          isr.implementation ? { text: isr.implementation } : muted(words.notRated),
        ],
      })),
    };
  }
  if (note.key === "disbursement") {
    if (!rows.length) return null;
    const totals = note.totals ?? {};
    return {
      head,
      rows: rows.map((row) => ({
        key: row.evidence_id,
        cells: [
          { text: <IdText id={String(field(row, "loan_number"))} /> },
          { text: field(row, "original_principal_millions"), numeric: true },
          { text: field(row, "disbursed_millions"), numeric: true },
          { text: field(row, "undisbursed_millions"), numeric: true },
          { text: field(row, "cancelled_millions"), numeric: true },
        ],
      })),
      foot: rows.length > 1
        ? [{ text: words.total }, { text: totals.commitment_millions, numeric: true }, { text: totals.disbursed_millions, numeric: true },
          { text: totals.undisbursed_millions, numeric: true }, { text: totals.canceled_millions, numeric: true }]
        : undefined,
    };
  }
  const after = rows.filter((row) => row.source.source_key === "plans");
  if (!after.length) return null;
  return {
    head,
    rows: after.map((row) => ({
      key: row.evidence_id,
      cells: [
        { text: <IdText id={String(field(row, "activity_reference_no"))} /> },
        { text: field(row, "implementing_agency") },
        { text: table(field(row, "planned_completion_on")) },
        { text: formatNumber(field(row, "days_after_closing")), numeric: true },
      ],
    })),
  };
}

function historyOf(note: DraftNote): Table | null {
  const moves = (note.table ?? []).filter((row) => row.source.source_key === "loan_history");
  if (!moves.length) return null;
  return {
    head: words.cols.history,
    rows: moves.map((row) => ({
      key: row.evidence_id,
      cells: [
        { text: formatDate(String(field(row, "reported_on")), { style: "month" }) },
        { text: table(field(row, "previous_closing_date")) },
        { text: table(field(row, "closing_date")) },
      ],
    })),
  };
}

type Abbreviated = { short: string; spelled: string };

// A column head with its abbreviation as a window, such as "Progress towards achievement of PDO".
function headWords(name: string, abbr?: Abbreviated): ReactNode {
  if (!abbr || !name.includes(abbr.short)) return name;
  const [before, ...after] = name.split(abbr.short);
  return (
    <>
      {before}
      <Abbr short={abbr.short} spelled={abbr.spelled} />
      {after.join(abbr.short)}
    </>
  );
}

function TableView({ title, data, folded, abbr }: { title: ReactNode; data: Table; folded: boolean; abbr?: Abbreviated }) {
  const rows = folded ? data.rows.slice(0, AWARDS_SHOWN) : data.rows;
  return (
    <>
      <div className="hidden overflow-hidden rounded-md border border-line bg-surface @min-[40rem]/doc:block" data-brief-view="table">
        <table className="w-full border-collapse text-left text-small">
          <caption className="sr-only">{title}</caption>
          <thead className="bg-surface-2">
            <tr>
              {data.head.map((name, index) => (
                <th key={name} scope="col" className={cx("px-3 py-3 align-bottom font-bold text-ink-heading", data.rows[0]?.cells[index]?.numeric && "text-right")}>
                  {headWords(name, abbr)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-line align-top">
                {row.cells.map((cell, index) =>
                  index === 0 ? (
                    <th key={index} scope="row" className="px-3 py-3 text-left font-normal text-ink">
                      {cell.text}
                    </th>
                  ) : (
                    <td key={index} className={cx("px-3 py-3 text-ink", cell.numeric && "text-right tabular-nums")}>
                      {cell.text}
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
          {data.foot && (
            <tfoot>
              <tr className="border-t-2 border-line align-top font-semibold">
                {data.foot.map((cell, index) =>
                  index === 0 ? (
                    <th key={index} scope="row" className="px-3 py-3 text-left text-ink">
                      {cell.text}
                    </th>
                  ) : (
                    <td key={index} className="px-3 py-3 text-right text-ink tabular-nums">
                      {cell.text}
                    </td>
                  ),
                )}
              </tr>
            </tfoot>
          )}
        </table>
      </div>
      <ul className="flex flex-col @min-[40rem]/doc:hidden" data-brief-view="blocks">
        {[...rows, ...(data.foot ? [{ key: "total", cells: data.foot }] : [])].map((row) => (
          <li key={row.key} className="border-t border-line py-3">
            <h4 className="text-small font-bold text-ink-heading">{row.cells[0].text}</h4>
            {/* Two equal columns, so a long value (a supplier's name) can never squeeze its label to nothing. */}
            <dl className="mt-1 grid grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-x-4 gap-y-1 text-small">
              {row.cells.slice(1).map((cell, index) => (
                <div key={index} className="contents">
                  <dt className="min-w-0 text-caption text-ink-muted [overflow-wrap:anywhere]">{headWords(data.head[index + 1], abbr)}</dt>
                  <dd className={cx("min-w-0 text-ink [overflow-wrap:anywhere]", cell.numeric && "text-right tabular-nums")}>{cell.text}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}

// abbr: an abbreviation in the column heads, such as PDO, written short with the window that spells it out (ticket 126,
// pattern 4), where a caption under the title spelled it out until then.
function PartTable({ title, data, abbr, foldable = false }: { title: ReactNode; data: Table; abbr?: Abbreviated; foldable?: boolean }) {
  const [all, setAll] = useState(false);
  const folds = foldable && data.rows.length > AWARDS_SHOWN;
  return (
    <div className="mt-4">
      <p className="text-small font-bold text-ink-heading">{title}</p>
      <div className="mt-2">
        <TableView title={title} data={data} folded={folds && !all} abbr={abbr} />
      </div>
      {folds && (
        <Button className="mt-2" variant="ghost" flush onPage aria-expanded={all} onClick={() => setAll(!all)}>
          {all ? words.lessAwards : words.moreAwards(formatNumber(data.rows.length))}
        </Button>
      )}
    </div>
  );
}

function abstention(note: DraftNote, subject: { isr_date?: string | null; closing_date?: string | null }): string | null {
  if (!note.reason) return null;
  const template = note.key === "ratings" && note.reason === "no_isr" ? words.ratingsNone : words.none[note.reason] ?? null;
  return template?.replace("{date}", formatDate(note.reason === "no_awards" ? subject.isr_date ?? "" : subject.closing_date ?? "")) ?? null;
}

export function MissionBriefParts({ notes, evidence, numbers, opened, open, subject }: {
  notes: DraftNote[];
  evidence: Record<string, EvidenceEvent>;
  numbers: Map<string, number>;
  opened: ReadonlySet<string>;
  open: OpenSource;
  subject: { isr_date?: string | null; closing_date?: string | null; as_of?: string };
}) {
  return (
    <div className="flex flex-col gap-12" data-brief-parts="draft">
      {notes.map((note) => {
        const data = tableOf(note);
        const said = abstention(note, subject);
        const history = note.key === "closing" ? historyOf(note) : null;
        // Awards since the ISR's date; the loans as of their snapshot's month end.
        const titleDate = note.key === "awards" ? subject.isr_date : note.key === "disbursement" ? note.totals?.as_of_date : subject.as_of;
        const tableTitle = (words.tables[note.key] ?? "").replace("{date}", titleDate ? formatDate(titleDate) : "");
        return (
          <section key={note.key} aria-labelledby={`part-${note.key}`} data-brief-part={note.key}>
            <h3 id={`part-${note.key}`} tabIndex={-1} className="text-h2 text-ink-heading focus:outline-none">
              {words.parts[note.key]}
            </h3>
            <div className="mt-2">
              {note.sentences.length > 0 ? (
                <NoteSentences sentences={note.sentences} evidence={evidence} numbers={numbers} opened={opened} open={open} textSize="body" />
              ) : note.state === "refused" ? (
                // The writer declined the part, so I removed nothing: say so, in the words its refusal code has.
                <p className="max-w-[72ch] text-body text-ink" data-refused>
                  {kindWords.refused[note.refusal ?? ""] ?? kindWords.refusedOther}
                </p>
              ) : said ? (
                <p className="max-w-[72ch] text-body text-ink">{said}</p>
              ) : (
                <p className="max-w-[72ch] text-body text-ink-muted">{words.allRemoved}</p>
              )}
            </div>
            {data && <PartTable title={tableTitle} data={data} abbr={note.key === "ratings" ? { short: words.pdoShort, spelled: words.pdo } : undefined} foldable={note.key === "awards"} />}
            {/* The tool's flag, worded as the Summary's Money table words it: the browser compares no amounts. */}
            {data && note.key === "disbursement" && note.totals?.amounts_exceed_commitment && (
              <p className="mt-2 max-w-[72ch] text-caption text-ink-muted" data-exceeds>
                {copy.summary.money.exceeds}
              </p>
            )}
            {note.key === "closing" && !data && !note.reason && <p className="mt-4 max-w-[72ch] text-small text-ink-muted">{words.noneAfter}</p>}
            {history && <PartTable title={words.tables.history} data={history} />}
          </section>
        );
      })}
    </div>
  );
}

// "Cited in Latest Procurement Plans and Rating history."
export function citedInParts(keys: string[]): ReactNode {
  const names = keys.map((key) => words.parts[key] ?? key);
  const joined = names.length <= 1 ? names.join("") : names.slice(0, -1).join(copy.following.partsJoin) + copy.following.partsTwo + names.at(-1);
  return words.citedIn.replace("{parts}", joined);
}

export const partCount = (count: number) => formatCount(count);
