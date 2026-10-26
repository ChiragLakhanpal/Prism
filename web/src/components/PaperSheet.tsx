// The procurement summary for the Project Paper (ticket 36; the 36 brief, section 3.7; DESIGN.md section 4): the
// draft's exportable text on a surface sheet, so it reads as the page that becomes the Word file. Three parts, one
// per input, each an h3: the Procurement Plan, the implementing agency's track record and the PPSD's risks. A part
// with nothing to draw on says why in the first person, and the Word file leaves it out. The PPSD part names each
// draft it drew on, by its title, as a link to it. Under a part that cites a lesson a lead has since changed or retired,
// its version notice (ticket 39), and after the parts, any part its author removed.
import type { ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { Draft, DraftNote } from "../lib/drafts";
import { draftHref } from "../lib/drafts";
import { formatDate } from "../lib/format";
import { NoteSentences, type OpenSource } from "./DraftNotes";
import { Fill } from "./Fill";
import { TextLink } from "./TextLink";

const words = copy.paper;
const kind = copy.draft.kinds.project_paper;

function PartBody({ note, draft, evidence, numbers, opened, open }: {
  note: DraftNote;
  draft: Draft;
  evidence: Record<string, EvidenceEvent>;
  numbers: Map<string, number>;
  opened: ReadonlySet<string>;
  open: OpenSource;
}) {
  if (note.sentences.length > 0) {
    return <NoteSentences sentences={note.sentences} evidence={evidence} numbers={numbers} opened={opened} open={open} textSize="body" />;
  }
  const line =
    note.reason === "no_ppsd_rows" ? words.ppsdNone
      : note.reason === "no_track_record" ? words.recordNone(draft.subject.implementing_agency)
        : note.state === "refused" ? (kind.refused[note.refusal ?? ""] ?? kind.refusedOther)
          : words.abstain;
  return (
    <p className="max-w-[72ch] text-small text-ink-muted" data-part-empty={note.reason ?? note.state}>
      {line}
    </p>
  );
}

export function PaperSheet({ draft, numbers, opened, open, under, after }: {
  draft: Draft;
  numbers: Map<string, number>;
  opened: ReadonlySet<string>;
  open: OpenSource;
  under?: (key: string) => ReactNode;
  after?: ReactNode;
}) {
  return (
    <article aria-label={words.sheetLabel} className="rounded-md border border-line bg-surface p-4 md:p-6 lg:p-8" data-paper-sheet>
      <div className="flex flex-col gap-8">
        {draft.notes.map((note) => (
          <section key={note.key} aria-labelledby={`part-${note.key}`} data-paper-part={note.key}>
            <h3 id={`part-${note.key}`} className="text-title text-ink-heading">
              {words.parts[note.key]}
            </h3>
            {note.key === "ppsd" && (note.drafts ?? []).length > 0 && (
              <p className="mt-1 text-caption text-ink-muted" data-ppsd-source>
                {(note.drafts ?? []).map((source) => (
                  <span key={source.draft_id} className="block">
                    <Fill
                      template={words.ppsdSource}
                      slots={{
                        title: (
                          <TextLink href={draftHref(source.draft_id)}>
                            {copy.draft.kinds.ppsd_rows.rowTitle(source.package_title ?? "", "")}
                          </TextLink>
                        ),
                        checker: source.checked_by ?? "",
                        date: source.checked_at ? formatDate(source.checked_at.slice(0, 10)) : "",
                      }}
                    />
                  </span>
                ))}
              </p>
            )}
            <div className="mt-2">
              <PartBody note={note} draft={draft} evidence={draft.evidence} numbers={numbers} opened={opened} open={open} />
            </div>
            {under?.(note.key)}
          </section>
        ))}
        {after}
      </div>
    </article>
  );
}
