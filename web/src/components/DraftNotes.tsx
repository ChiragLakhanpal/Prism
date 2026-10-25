// The notes of a review notes draft (the 35 brief, sections 3.5 and 3.6): two columns, Activity and Review
// note, as in the Word file. A table when the document column is at least 560 px wide, cards below that,
// by a container query on the column itself, since two columns fit far more narrowly than the plan
// check's six. The Activity cell is the row header: the mark's badge on its own line, the STEP reference
// as a link to its row in the plan check, then the Description. Rows keep the plan check's order.
//
// NoteSentences draws one note's sentences with their citation markers, which open the evidence drawer at
// the plan row each cites. Numbers the verifier matched explain themselves, as in an answer.
import { createContext, Fragment, useContext, type ReactNode } from "react";
import type { DraftNote } from "../lib/drafts";
import type { EvidenceEvent, SentenceEvent } from "../lib/answer";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { cx } from "../lib/cx";
import { DRAWER_ID, markerSource, sentenceText } from "./AnswerPanel";
import { CitationMarker } from "./CitationMarker";
import { EvidenceCard } from "./EvidenceCard";
import { Lang } from "./Lang";
import { StatusBadge } from "./StatusBadge";
import { TextLink } from "./TextLink";

const BADGE = { needs_a_look: "needs-a-look", watch: "watch" } as const;

export type NoteRow = {
  key: string;
  mark: DraftNote["mark"];
  description: string | null;
  // The address of the activity's row in the plan check.
  href: string;
  note: ReactNode;
};

// The open drawer's source, and the sentence whose marker opened it, for the active marker's look.
export type OpenSource = { id: string | null; sentence: number | null };

// The language the writer wrote a draft in (ticket 42), which the draft page provides: every writer sentence carries
// it, and a citation marker inside it stays in the copy file's English.
export const WrittenIn = createContext("en");

export function NoteSentences({
  sentences,
  evidence,
  numbers,
  opened,
  open,
  textSize = "small",
}: {
  sentences: SentenceEvent[];
  evidence: Record<string, EvidenceEvent>;
  // Each source's number, in order of first appearance across the whole draft.
  numbers: Map<string, number>;
  // The sources this viewer opened since the draft was saved: their markers take the visited look.
  opened: ReadonlySet<string>;
  open: OpenSource;
  // A draft's notes are small; a lesson review's summary is body text, like the states around it.
  textSize?: "small" | "body";
}) {
  const show = (id: string, sentence: number, marker: HTMLElement | null) =>
    openEvidence(id, { serial: null, sentence, marker, runId: null });
  const writtenIn = useContext(WrittenIn);
  return (
    <Lang as="p" code={writtenIn} className={cx("max-w-[72ch] text-ink", textSize === "body" ? "text-body" : "text-small")} data-note>
      {sentences.map((sentence, index) => {
        const active = open.id !== null && open.sentence === sentence.index && sentence.evidence_ids.includes(open.id);
        return (
          <Fragment key={sentence.index}>
            {index > 0 && " "}
            <span data-sentence-text={sentence.index} className={active ? "bg-tint [box-decoration-break:clone]" : undefined}>
              {sentenceText(sentence, evidence, (id) => show(id, sentence.index, null))}
              <Lang code="en">
              {sentence.evidence_ids.map((id) => {
                const n = numbers.get(id)!;
                return (
                  <CitationMarker
                    key={id}
                    n={n}
                    evidenceId={id}
                    sentence={sentence.index}
                    source={markerSource(evidence[id], id)}
                    href={evidenceHref(id)}
                    drawerId={DRAWER_ID}
                    active={open.id === id && active}
                    opened={opened.has(id)}
                    preview={evidence[id] ? <EvidenceCard evidence={evidence[id]} n={n} sentence={null} visited={opened.has(id)} /> : undefined}
                    onOpen={(marker) => show(id, sentence.index, marker)}
                  />
                );
              })}
              </Lang>
            </span>
          </Fragment>
        );
      })}
    </Lang>
  );
}

function Activity({ row, card = false }: { row: NoteRow; card?: boolean }) {
  return (
    <>
      <StatusBadge kind={BADGE[row.mark]} />
      <TextLink href={row.href} data-activity-ref className={cx("max-w-full font-mono font-medium wrap-anywhere", card ? "mt-1" : "mt-0.5")}>
        {row.key}
      </TextLink>
    </>
  );
}

export function DraftNotes({ rows, columns, caption, cardsLabelId }: {
  rows: NoteRow[];
  // The two column headings, from the kind's layout (config/drafts.toml) in the kind's words.
  columns: string[];
  // The table's caption, for screen readers.
  caption: string;
  // The lede's id, which names the list of cards.
  cardsLabelId: string;
}) {
  const [activity, note] = columns;
  return (
    <div data-draft-notes>
      <div data-view="table" className="hidden overflow-hidden rounded-md border border-line bg-surface @min-[35rem]/doc:block">
        <table className="w-full table-fixed border-collapse text-small">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-surface-2">
            <tr>
              <th scope="col" className="w-60 p-3 text-left font-semibold text-ink-heading">
                {activity}
              </th>
              <th scope="col" className="p-3 text-left font-semibold text-ink-heading">
                {note}
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} id={`note-${row.key}`} className="border-t border-line align-top">
                <th scope="row" className="p-3 text-left font-normal">
                  <div className="flex flex-col items-start">
                    <Activity row={row} />
                    {row.description && <span className="mt-1 block text-small text-ink">{row.description}</span>}
                  </div>
                </th>
                <td className="p-3">{row.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul data-view="cards" aria-labelledby={cardsLabelId} className="flex flex-col gap-3 @min-[35rem]/doc:hidden">
        {rows.map((row) => (
          <li key={row.key} className="rounded-md border border-line bg-surface p-4">
            <article>
              <h3 className="flex flex-col items-start text-small">
                <Activity row={row} card />
              </h3>
              {row.description && <p className="mt-1 text-small text-ink">{row.description}</p>}
              <div className="mt-3 border-t border-line pt-3">{row.note}</div>
            </article>
          </li>
        ))}
      </ul>
    </div>
  );
}
