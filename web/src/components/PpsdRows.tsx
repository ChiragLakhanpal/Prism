// Suggested risk rows for the borrower's PPSD (ticket 36; the 36 brief, sections 3.3 to 3.5 and 4.4; DESIGN.md section
// 5, PPSD risk table). The columns are the template registry's, word for word, in the form the person chose.
//
// - The Short Form is the template's own three-column table from a 600 px document column: Risk Description (the row
//   header), Description of mitigation and Risk Owner, with a fill-in chip in each empty owner cell.
// - The Long Form, and the Short Form below 600 px, are row blocks: the risk's name as an h3, Strata's two cells, then
//   a band on the page fill with the fields people fill, in the template's order. The band is the line between what
//   Strata wrote and what you commit to. Word always gets the template's table.
//
// One layout is in the page at a time, chosen from the document column's width, so each chip has one id the bar's
// hold line can link to. Each of Strata's sentences has one citation marker, which may carry several sources and
// becomes one Word footnote; the Sources list shows each footnote's Word text.
import { useContext } from "react";
import { Lang } from "./Lang";
import { WrittenIn } from "./DraftNotes";
import { Fragment, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent, SentenceEvent } from "../lib/answer";
import { cx } from "../lib/cx";
import type { Draft, DraftNote, Footnote, PpsdColumn, PpsdRow } from "../lib/drafts";
import { valueOf } from "../lib/drafts";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { formatAmountText, formatNumber } from "../lib/format";
import { DRAWER_ID, sentenceText } from "./AnswerPanel";
import { CitationMarker } from "./CitationMarker";
import { FillChip } from "./FillChip";
import { Fill } from "./Fill";
import { fillText } from "./LessonParts";
import type { OpenSource } from "./DraftNotes";
import { SegmentedControl } from "./SegmentedControl";
import { DraftRowNotice, RowChoice } from "./VersionNotice";
import { draftTitle } from "../lib/lessonsPage";

const words = copy.ppsd;
const kind = copy.draft.kinds.ppsd_rows;
const whole = (value: number) => formatNumber(value, { compact: false });
// The table holds from a document column of 600 px (37.5rem): the owner column then holds the "Set the owner" chip.
const TABLE_FROM = 600;
// Strata's two cells sit side by side in a block whose content is at least 560 px wide.
const SIDE_BY_SIDE_FROM = 560;

function useWidth<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [width, setWidth] = useState(0);
  useLayoutEffect(() => {
    const element = ref.current;
    if (!element) return;
    const update = () => setWidth(element.getBoundingClientRect().width);
    update();
    const observer = new ResizeObserver(update);
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  return [ref, width];
}

// A US dollar amount as a sentence writes it (DESIGN.md section 7, rule 11): "1.2 million", "50 million".
function dollars(amount: string | null): string {
  return amount === null ? "" : formatAmountText(Number(amount));
}

// The marker's name lists every source it carries (the 36 brief, 4.6): "Source 2: ICR P130164 paragraph 54, page
// 23, and ICR Review paragraph 10.b".
export function footnoteSources(footnote: Footnote, row: PpsdRow): string {
  const named = footnote.evidence_ids.map((id) => {
    if (id === row.counts_evidence_id) return words.markerCount;
    if (id === row.lesson.evidence_id) return words.markerLesson;
    const source = row.sources.find((one) => one.evidence_id === id);
    if (!source) return id;
    return source.locator.kind === "paragraph"
      ? fillText(words.markerParagraph, { doc: source.doc_short, pcode: source.pcode, para: source.locator.text, page: source.page ?? "" })
      : fillText(words.markerSection, { doc: source.doc_short, section: source.locator.text });
  });
  return named.join(words.markerJoin);
}

function CellSentences({
  note,
  row,
  footnotes,
  evidence,
  opened,
  open,
}: {
  note: DraftNote | undefined;
  row: PpsdRow;
  footnotes: Footnote[];
  evidence: Record<string, EvidenceEvent>;
  opened: ReadonlySet<string>;
  open: OpenSource;
}) {
  const writtenIn = useContext(WrittenIn);
  if (!note || note.sentences.length === 0) {
    return <p className="text-small text-ink-muted" data-cell-abstain>{kind.abstain}</p>;
  }
  return (
    <Lang as="p" code={writtenIn} className="max-w-[65ch] text-small text-ink" data-cell-text>
      {note.sentences.map((sentence: SentenceEvent, index) => {
        const footnote = footnotes.find((one) => one.row_key === row.row_key && one.cell === note.cell && one.position === index);
        const ids = footnote?.evidence_ids ?? sentence.evidence_ids;
        const first = ids[0];
        const seen = ids.every((id) => opened.has(id));
        const active = open.id !== null && open.sentence === sentence.index && ids.includes(open.id);
        return (
          <Fragment key={sentence.index}>
            {index > 0 && " "}
            <span data-sentence-text={sentence.index} className={active ? "bg-tint [box-decoration-break:clone]" : undefined}>
              {sentenceText(sentence, evidence, undefined)}
              {footnote && (
                <CitationMarker
                  n={footnote.number}
                  evidenceId={first}
                  sentence={sentence.index}
                  source={footnoteSources(footnote, row)}
                  href={evidenceHref(first)}
                  drawerId={DRAWER_ID}
                  active={active}
                  opened={seen}
                  onOpen={(marker) => openEvidence(first, { serial: null, sentence: sentence.index, marker, runId: null })}
                />
              )}
            </span>
          </Fragment>
        );
      })}
    </Lang>
  );
}

export type PpsdRowsProps = {
  draft: Draft;
  // The author, in Draft or Checked by you, in the staff view: the fields and the form can change.
  editable: boolean;
  opened: ReadonlySet<string>;
  open: OpenSource;
  // The lede's id, which names the blocks' list.
  ledeId: string;
  onSave: (rowKey: string, field: string, value: string | null) => Promise<boolean>;
  onForm: (form: "short" | "long") => void;
  // Ticket 39: the draft as the server answers after its author chose for a row whose lesson changed.
  onLesson?: (next: Draft) => void;
};

export function PpsdRows({ draft, editable, opened, open, ledeId, onSave, onForm, onLesson }: PpsdRowsProps) {
  const ppsd = draft.ppsd!;
  const [frame, width] = useWidth<HTMLDivElement>();
  const form = ppsd.forms[ppsd.form];
  const notes = new Map(draft.notes.map((note) => [note.key, note]));
  const footnotes = draft.footnotes ?? [];
  const rows = ppsd.rows.filter((row) => !row.removed);
  const table = ppsd.form === "short" && width >= TABLE_FROM;
  const people = form.columns.filter((column) => column.filled_by === "people");
  const strata = form.columns.filter((column) => column.filled_by === "strata");
  const tableI = ppsd.table_i;
  const category = words.categories[tableI.category ?? ""] ?? tableI.category ?? "";
  const captionId = useId();
  const cell = (row: PpsdRow, column: PpsdColumn) => (
    <CellSentences
      note={notes.get(row.cells[column.key as "risk_description" | "mitigation"])}
      row={row}
      footnotes={footnotes}
      evidence={draft.evidence}
      opened={opened}
      open={open}
    />
  );
  const chip = (row: PpsdRow, column: PpsdColumn) => (
    <FillChip
      id={`fill-${row.row_key}-${column.key}`}
      column={column}
      ppsd={ppsd}
      riskLabel={row.risk_label}
      value={valueOf(draft, row.row_key, column.key)}
      editable={editable}
      onSave={(value) => onSave(row.row_key, column.key, value)}
    />
  );

  const formCaption: ReactNode = tableI.amount === null ? words.formNoAmount : (
    <Fill
      template={tableI.applies ? words.formAvailable : words.formBelow}
      slots={{ amount: dollars(tableI.amount), threshold: dollars(tableI.threshold), category }}
    />
  );
  const counts = ppsd.counts;
  const long = ppsd.form === "long";
  // Ticket 39: under a row, its version notice, or what its author chose for it (the 39 brief, section 2.4).
  const title = draftTitle(draft.kind, draft.subject as unknown as Record<string, string | null>);
  const canAct = Boolean(draft.lesson_can_act);
  const done = (answer: { draft: Draft }) => onLesson?.(answer.draft);
  const under = (row: PpsdRow): ReactNode => {
    const notice = (draft.lesson_notices ?? []).find((one) => one.row_key === row.row_key);
    if (notice) {
      return (
        <DraftRowNotice<Draft> notice={notice} draftId={draft.draft_id} draftState={draft.state} title={title} canAct={canAct && notice.can_act} author={draft.author.name} onDone={done} />
      );
    }
    const updated = (draft.lesson_updated ?? []).filter((one) => one.row_key === row.row_key).at(-1);
    if (updated) {
      const earlier = (updated.earlier ?? []).find((note) => note.key === row.cells.mitigation);
      return (
        <RowChoice<Draft>
          record={updated}
          kind="updated"
          draftId={draft.draft_id}
          canAct={canAct}
          onDone={done}
          earlierText={earlier ? earlier.sentences.map((sentence) => sentence.text).join(" ") : undefined}
        />
      );
    }
    const kept = (draft.lesson_kept ?? []).find((one) => one.row_key === row.row_key);
    return kept ? <RowChoice<Draft> record={kept} kind="kept" draftId={draft.draft_id} canAct={canAct} onDone={done} /> : null;
  };
  const removed = draft.lesson_removed ?? [];
  return (
    <div ref={frame} data-ppsd-rows={ppsd.form} data-layout={table ? "table" : "blocks"}>
      {tableI.applies ? (
        <div className="flex flex-col gap-2" data-form-control>
          {editable ? (
            <SegmentedControl
              legend={<span className="font-bold text-ink">{words.formLegend}</span>}
              options={(["short", "long"] as const).map((key) => ({ value: key, label: ppsd.forms[key].name }))}
              value={ppsd.form}
              onChange={onForm}
              describedBy={captionId}
            />
          ) : (
            <p className="text-small font-bold text-ink">{words.formLegend}</p>
          )}
          <p id={captionId} className="max-w-[72ch] text-caption text-ink-muted" data-form-caption>
            {formCaption}
          </p>
        </div>
      ) : (
        <p className="max-w-[72ch] text-caption text-ink-muted" data-form-caption>
          {formCaption}
        </p>
      )}
      <p className="mt-4 max-w-[72ch] text-small text-ink" data-progress>
        <span className="font-bold" data-numbers>
          {words.progressCount(whole(counts.owners_set), whole(counts.total))}
          {long && <> {words.progressRated(whole(counts.rated), whole(counts.total))}</>}
        </span>{" "}
        {long ? words.progressLong : words.progressShort}
      </p>
      <p className="mt-2 text-caption text-ink-muted" data-count-line data-numbers>
        {kind.countLine(counts.total, whole(counts.total))}
      </p>
      <div className="mt-2">
        {table ? (
          <div className="overflow-hidden rounded-md border border-line bg-surface" data-ppsd-table>
            <table className="w-full table-fixed border-collapse text-small">
              <caption className="sr-only">{kind.tableCaption(form.name, "")}</caption>
              <colgroup>
                <col className="w-[36%]" />
                <col className="w-[36%]" />
                <col className="w-[28%]" />
              </colgroup>
              <thead className="bg-surface-2">
                <tr>
                  {form.columns.map((column) => (
                    <th key={column.key} scope="col" className="p-3 text-left align-top font-bold text-ink-heading" data-column={column.key}>
                      {column.header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const below = under(row);
                  return (
                    <Fragment key={row.row_key}>
                      <tr id={`row-${row.row_key}`} className="border-t border-line align-top" data-ppsd-row={row.row_key}>
                        {form.columns.map((column, index) =>
                          index === 0 ? (
                            <th key={column.key} scope="row" className="p-3 text-left font-normal">
                              {cell(row, column)}
                            </th>
                          ) : (
                            <td key={column.key} className="p-3">
                              {column.filled_by === "strata" ? cell(row, column) : chip(row, column)}
                            </td>
                          ),
                        )}
                      </tr>
                      {below && (
                        <tr data-notice-row={row.row_key}>
                          <td colSpan={form.columns.length} className="px-3">
                            {below}
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <ol aria-labelledby={ledeId} className="flex flex-col gap-3" data-ppsd-blocks>
            {rows.map((row) => (
              <li key={row.row_key} id={`row-${row.row_key}`} data-ppsd-row={row.row_key}>
                <article aria-labelledby={`${ledeId}-${row.row_key}`} className="overflow-hidden rounded-md border border-line bg-surface">
                  <div className="p-4 md:p-6">
                    <h3 id={`${ledeId}-${row.row_key}`} className="text-small font-semibold text-ink-heading">
                      {row.risk_label}
                    </h3>
                    <div className={cx("mt-3 grid gap-3", width - 48 >= SIDE_BY_SIDE_FROM && "grid-cols-2 gap-6")}>
                      {strata.map((column) => (
                        <div key={column.key} className="min-w-0">
                          <p className="text-caption font-semibold text-ink-muted">{column.header}</p>
                          <div className="mt-1">{cell(row, column)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div role="group" aria-label={words.bandLabel(row.risk_label)} className="border-t border-line bg-page p-4" data-band>
                    <div className="flex flex-wrap gap-x-4 gap-y-3">
                      {people.map((column) => (
                        <div
                          key={column.key}
                          className={cx(
                            "flex min-w-0 flex-col gap-1",
                            column.key === "risk_owner" ? "min-w-[200px]" : column.control === "stage" ? "min-w-[160px]" : "min-w-[96px]",
                          )}
                        >
                          <span className="text-caption font-semibold text-ink-muted">{column.header}</span>
                          {chip(row, column)}
                        </div>
                      ))}
                    </div>
                  </div>
                  {under(row) && <div className="border-t border-line px-4" data-notice-row={row.row_key}>{under(row)}</div>}
                </article>
              </li>
            ))}
          </ol>
        )}
      </div>
      {removed.length > 0 && (
        <div className="mt-3 rounded-md border border-line bg-surface" data-removed-rows>
          {removed.map((record) => (
            <RowChoice<Draft> key={record.row_key} record={record} kind="removed" draftId={draft.draft_id} canAct={canAct} onDone={done} />
          ))}
        </div>
      )}
    </div>
  );
}
