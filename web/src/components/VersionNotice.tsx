// The version notice (ticket 39; the 39 brief, sections 3.4 and 5.3; DESIGN.md section 5, Version notice): a lesson
// that changed after the version a draft row cites. A work row, not a card: the change badge first, the statement at
// the cited version, "Was" and "Now" with the changed words marked, the lead's reason by role, a link to both versions,
// then one use block per draft row with its two choices and what each will do. Under a draft row the same notice
// drops the title and "Used in" and leads with a sentence about the row.
//
// The server decides everything: the tier, which choices a row offers, who may act and every count. Each choice is a
// POST to the row's lesson route; nothing in a draft changes until its author chooses.
import { createElement, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import { ApiError, postJson } from "../lib/api";
import { draftHref, type Draft } from "../lib/drafts";
import { evidenceHref, openEvidence } from "../lib/evidence";
import type { Change, ChoiceAnswer, DraftUse, NoticeBody, Tier, VersionBlock, VersionsView as VersionsViewData } from "../lib/lessonsPage";
import { choiceUrl, draftTitle, rowLabel, versionsId } from "../lib/lessonsPage";
import { Alert } from "./Alert";
import { RemovedBox, removedFrom, type Removed } from "./Checks";
import { Button } from "./Button";
import { ReasonField } from "./DecisionForm";
import { Fill } from "./Fill";
import { fillText, SourceChip, Tag } from "./LessonParts";
import { Num } from "./Num";
import { StatusBadge, type BadgeKind } from "./StatusBadge";
import { TextLink } from "./TextLink";

const n = copy.notice;
const BADGE: Record<Tier, BadgeKind> = { narrowed: "changed", retired_wrong: "retired-wrong", retired_outdated: "retired-outdated" };
const retired = (tier: Tier) => tier !== "narrowed";

// The words the server marked as changed, in the highlight fill, with hidden words around each run.
export function ChangeMarks({ text, ranges }: { text: string; ranges: [number, number][] }) {
  const parts: ReactNode[] = [];
  let at = 0;
  ranges.forEach(([start, end], index) => {
    if (start > at) parts.push(text.slice(at, start));
    parts.push(
      <mark key={index} data-change-mark className="bg-highlight text-ink [box-decoration-break:clone]">
        <span className="clip-visually">{n.changedStart}</span>
        {text.slice(start, end)}
        <span className="clip-visually">{n.changedEnd}</span>
      </mark>,
    );
    at = end;
  });
  if (at < text.length) parts.push(text.slice(at));
  return <>{parts}</>;
}

function fieldLine(change: Change, side: "was" | "now"): ReactNode {
  const value = change[side] || n.fieldNone;
  const ranges = change[side] ? change[side === "was" ? "was_ranges" : "now_ranges"] : [];
  const template = n.fields[change.field] ?? n.fields.statement;
  return <Fill template={template} slots={{ value: <ChangeMarks text={value} ranges={ranges} /> }} />;
}

// "Was" and "Now", one above the other on the same left edge.
export function WasNow({ notice, onRow }: { notice: NoticeBody; onRow: boolean }) {
  const cited = <Fill template={onRow ? n.citesRow : n.citesYours} slots={{ a: <Num value={notice.a} /> }} />;
  const rows: { term: string; lines: ReactNode[]; caption: ReactNode }[] = retired(notice.tier)
    ? [
        { term: n.was, lines: [notice.statement_a], caption: cited },
        { term: n.now, lines: [<Fill key="now" template={n.retiredNow[notice.tier]} slots={{ date: <Num date={notice.retired_on ?? notice.decided_on} /> }} />], caption: null },
      ]
    : [
        { term: n.was, lines: notice.changes.map((change) => fieldLine(change, "was")), caption: cited },
        {
          term: n.now,
          lines: notice.changes.map((change) => fieldLine(change, "now")),
          caption: <Fill template={n.decidedNow} slots={{ b: <Num value={notice.b} />, date: <Num date={notice.decided_on} /> }} />,
        },
      ];
  return (
    <dl className="grid gap-x-4 gap-y-3 text-small @min-[30rem]/page:grid-cols-[4rem_1fr]" data-was-now>
      {rows.map((row) => (
        <div key={row.term} className="contents">
          <dt className="font-semibold text-ink-heading">{row.term}</dt>
          <dd className="flex min-w-0 flex-col gap-0.5 text-ink">
            {row.lines.map((line, index) => (
              <span key={index}>{line}</span>
            ))}
            {row.caption && <span className="text-caption text-ink-muted">{row.caption}</span>}
          </dd>
        </div>
      ))}
    </dl>
  );
}

// The decided line, with the lead's reason as written, by role.
function Decided({ notice }: { notice: NoticeBody }) {
  return (
    <p className="max-w-prose text-small text-ink-muted" data-decided-line>
      {fillText(n.decided[notice.tier], { reason: notice.reason })}
    </p>
  );
}

function VersionsLink({ notice }: { notice: NoticeBody }) {
  const id = versionsId(notice.lesson_id, notice.a, notice.b);
  return (
    <TextLink
      href={evidenceHref(id)}
      data-versions-link
      className="inline-flex min-h-6 items-center text-small"
      onClick={(event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        openEvidence(id, { serial: null, sentence: null, marker: event.currentTarget, runId: null });
      }}
    >
      {retired(notice.tier) ? n.readRetired : n.seeBoth}
    </TextLink>
  );
}

type Busy = "update" | "keep" | "remove" | null;

export type ChoiceProps<D> = {
  notice: NoticeBody;
  draftId: string;
  rowKey: string;
  draftState: string | undefined;
  title: string;
  actions: ("update" | "remove" | "keep")[];
  // Keeping the choice's words with the draft: the server's answer, and the choice made.
  onDone: (answer: ChoiceAnswer<D>, action: "update" | "keep" | "remove") => void;
  holdSentence?: boolean;
  view?: string;
};

// A draft kind's own words for the verifier's reasons, from the draft an answer carries.
function kindReasons(draft: unknown): Record<string, { item: string; joined: string }> {
  const kind = (draft as { kind?: string } | null)?.kind ?? "";
  const kinds = copy.draft.kinds as Record<string, { removedReasons?: Record<string, { item: string; joined: string }> }>;
  return kinds[kind]?.removedReasons ?? {};
}

// The two choices of one use, the keep form, and what each choice will do (feedforward).
export function Choices<D>({ notice, draftId, rowKey, draftState, title, actions, onDone, holdSentence = false, view }: ChoiceProps<D>) {
  const [busy, setBusy] = useState<Busy>(null);
  const [form, setForm] = useState<{ open: boolean; error: string | null }>({ open: false, error: null });
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<ReactNode>(null);
  // When none of the rewrite's sentences passed, what the verifier removed (CLAUDE.md rule 2: removed and shown).
  const [removedNow, setRemovedNow] = useState<Removed[]>([]);
  const keepButton = useRef<HTMLButtonElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const feedforwardId = useId();
  const holdId = useId();
  const formId = useId();
  const isRetired = retired(notice.tier);
  useEffect(() => {
    if (form.open) field.current?.focus();
  }, [form.open]);

  const choose = async (action: "update" | "keep" | "remove") => {
    if (action === "keep" && !reason.trim()) {
      setForm({ open: true, error: n.keepEmpty });
      field.current?.focus();
      return;
    }
    setBusy(action);
    setProblem(null);
    setRemovedNow([]);
    try {
      const answer = await postJson<ChoiceAnswer<D>>(choiceUrl(draftId, rowKey), {
        lesson_id: notice.lesson_id,
        action,
        expected_cited_version: notice.a,
        expected_current_version: notice.b,
        reason: action === "keep" ? reason : null,
        view: view ?? "staff",
      });
      if (answer.outcome === "nothing_passed") {
        setProblem(fillText(n.nothingPassed, { a: notice.a, b: notice.b }));
        setRemovedNow(removedFrom(answer.removed ?? [], kindReasons(answer.draft)));
      } else onDone(answer, action);
    } catch (error) {
      const code = error instanceof ApiError ? error.body.code : null;
      setProblem(
        code === "stale"
          ? n.stale
          : action === "update"
            ? fillText(n.updateFailed, { a: notice.a })
            : action === "remove"
              ? n.removeFailed
              : n.saveFailed,
      );
    } finally {
      setBusy(null);
    }
  };

  const primary = actions.includes("update") ? "update" : actions.includes("remove") ? "remove" : null;
  // What each choice will do is said only when there is a second choice to tell it from: a notice that offers only
  // Keep (a kind with no writer for one row) has nothing to compare, so it shows no feedforward.
  const describedBy = [primary !== null ? feedforwardId : null, holdSentence ? holdId : null].filter(Boolean).join(" ") || undefined;
  return (
    <div className="flex flex-col gap-3" data-choices>
      {problem && (
        <Alert state={typeof problem === "string" && problem === n.stale ? "info" : "error"} live="alert">
          {problem}
        </Alert>
      )}
      {removedNow.length > 0 && <RemovedBox removed={removedNow} all />}
      {holdSentence && (
        <p id={holdId} className="text-small text-ink" data-hold-sentence>
          {n.holdSentence}
        </p>
      )}
      <div className="flex flex-col gap-3 @min-[30rem]/page:flex-row @min-[30rem]/page:flex-wrap">
        {primary !== null && (
          <Button
            variant="secondary"
            loading={busy === primary}
            busyLabel={n.busy[primary]}
            disabled={busy !== null && busy !== primary}
            aria-describedby={describedBy}
            onClick={() => void choose(primary)}
            data-choice={primary}
          >
            {primary === "update" ? n.update : n.remove}
            <span className="clip-visually">{fillText(primary === "update" ? n.inDraft : n.fromDraft, { title })}</span>
          </Button>
        )}
        {actions.includes("keep") && !form.open && (
          <Button
            ref={keepButton}
            variant="ghost"
            aria-expanded={false}
            aria-controls={formId}
            aria-describedby={describedBy}
            disabled={busy !== null}
            onClick={() => setForm({ open: true, error: null })}
            data-choice="keep-open"
          >
            {isRetired ? n.keepRow : fillText(n.keepVersion, { a: notice.a })}
            <span className="clip-visually">{fillText(n.inDraft, { title })}</span>
          </Button>
        )}
      </div>
      {form.open && (
        <form
          id={formId}
          noValidate
          aria-busy={busy === "keep" || undefined}
          onSubmit={(event) => {
            event.preventDefault();
            void choose("keep");
          }}
          onKeyDown={(event) => {
            if (event.key === "Escape" && busy === null) {
              event.stopPropagation();
              setForm({ open: false, error: null });
              requestAnimationFrame(() => keepButton.current?.focus());
            }
          }}
          className="flex flex-col gap-3"
          data-keep-form
        >
          <ReasonField
            ref={field}
            label={isRetired ? n.keepLabelRow : fillText(n.keepLabelVersion, { a: notice.a })}
            helper={n.keepHelper}
            value={reason}
            onChange={setReason}
            max={notice.reason_max_chars}
            error={form.error}
            disabled={busy === "keep"}
          />
          <div className="flex flex-wrap gap-3">
            <Button type="submit" variant="secondary" loading={busy === "keep"} busyLabel={n.busy.keep}>
              {isRetired ? n.keepSubmitRow : fillText(n.keepSubmitVersion, { a: notice.a })}
            </Button>
            <Button
              type="button"
              variant="ghost"
              disabled={busy === "keep"}
              onClick={() => {
                setForm({ open: false, error: null });
                requestAnimationFrame(() => keepButton.current?.focus());
              }}
            >
              {n.cancel}
            </Button>
          </div>
        </form>
      )}
      {primary !== null && (
        <p id={feedforwardId} className="max-w-prose text-caption text-ink-muted" data-feedforward>
          {primary === "update" ? (
            <>
              {fillText(n.feedforwardUpdate, { b: notice.b })}
              {draftState === "checked" && <> {n.feedforwardChecked}</>}
            </>
          ) : (
            n.feedforwardRemove
          )}
        </p>
      )}
      {busy === "update" && (
        <p role="status" className="text-caption text-ink-muted">
          {fillText(n.updatingStatus, { b: notice.b })}
        </p>
      )}
    </div>
  );
}

// What a choice made on the Lessons tab leaves in place of its use block.
function Outcome({ action, answer, notice, draftId }: { action: "update" | "keep" | "remove"; answer: ChoiceAnswer<unknown>; notice: NoticeBody; draftId: string }) {
  const panel = useRef<HTMLDivElement>(null);
  useEffect(() => panel.current?.focus(), []);
  const o = n.outcomes;
  const isRetired = retired(notice.tier);
  const lead =
    action === "update" ? fillText(o.updated, { b: notice.b }) : action === "remove" ? o.removed : isRetired ? o.keptRow : fillText(o.kept, { a: notice.a });
  const body =
    action === "update"
      ? answer.back_to_draft
        ? o.updatedBodyChecked
        : o.updatedBody
      : action === "remove"
        ? o.removedBody
        : isRetired
          ? o.keptRowBody
          : o.keptBody;
  return (
    <div ref={panel} tabIndex={-1} className="outline-none" data-outcome={answer.outcome}>
      <Alert state={action === "update" ? "success" : action === "remove" ? "neutral" : "info"}>
        {lead} {body}
        {notice.holds_export && action !== "update" && <> {o.released}</>}{" "}
        <TextLink href={draftHref(draftId)}>{o.openDraft}</TextLink>
      </Alert>
    </div>
  );
}

// One draft row that cites the lesson, on the Lessons tab: "Used in", the row, and its choices.
function UseBlock({ notice, use, actions }: { notice: NoticeBody; use: DraftUse; actions: ("update" | "remove" | "keep")[] }) {
  const [done, setDone] = useState<{ action: "update" | "keep" | "remove"; answer: ChoiceAnswer<unknown> } | null>(null);
  const title = draftTitle(use.kind, use.subject);
  const label = rowLabel(use.kind, use.row_label);
  return (
    <div className="flex flex-col gap-3 border-t border-line pt-4" data-use={use.draft_id}>
      {done ? (
        <Outcome action={done.action} answer={done.answer} notice={notice} draftId={use.draft_id} />
      ) : (
        <>
          <div className="flex flex-col gap-1">
            <p className="text-small text-ink">
              <Fill template={n.usedIn} slots={{ title: <TextLink href={draftHref(use.draft_id)}>{title}</TextLink>, a: <Num value={use.cites} /> }} />
            </p>
            {label && <p className="text-caption text-ink-muted">{label}</p>}
          </div>
          {use.can_act && (
            <Choices
              notice={notice}
              draftId={use.draft_id}
              rowKey={use.row_key ?? ""}
              draftState={use.draft_state}
              title={title}
              actions={actions.filter((action) => action !== "update" || use.can_update)}
              holdSentence={use.holds_export}
              onDone={(answer, action) => setDone({ action, answer })}
            />
          )}
        </>
      )}
    </div>
  );
}

// The notice on the Lessons tab, in "Changed where you used it".
export function VersionNotice({ notice, level = 3 }: { notice: NoticeBody & { actions: string[]; uses: DraftUse[] }; level?: 3 | 4 }) {
  const headingId = useId();
  const actions = notice.actions.filter((action): action is "update" | "remove" | "keep" => action !== "versions");
  return (
    <li id={notice.anchor} className="border-t-2 border-line py-4" data-version-notice={notice.tier}>
      <article aria-labelledby={headingId} className="flex flex-col gap-3">
        <div>
          <StatusBadge kind={BADGE[notice.tier]} />
        </div>
        {createElement(`h${level}`, { id: headingId, className: "text-title text-balance text-ink-heading" }, notice.statement_a)}
        <WasNow notice={notice} onRow={false} />
        <Decided notice={notice} />
        <div>
          <VersionsLink notice={notice} />
        </div>
        {notice.uses.map((use) => (
          <UseBlock key={`${use.draft_id}-${use.row_key}`} notice={notice} use={use} actions={actions} />
        ))}
      </article>
    </li>
  );
}

// What an author's choice leaves on a draft row (the 39 brief, section 5.9): an updated row's caption with "Show the
// earlier text" and "Go back to version {a}", a kept version's caption, or a removed row's line with "Restore the row".
export function RowChoice<D>({
  record,
  kind,
  draftId,
  canAct,
  onDone,
  earlierText,
  partName,
}: {
  record: { row_key: string; lesson_id: string; action: string; cited_version: number; current_version: number; reason: string | null; at: string; row_label: { n: number; risk_label: string } | null };
  kind: "updated" | "kept" | "removed";
  draftId: string;
  canAct: boolean;
  onDone: (answer: ChoiceAnswer<D>) => void;
  earlierText?: ReactNode;
  // A part of a draft whose kind has no rows, by its heading, in place of the row label.
  partName?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState(false);
  const [earlier, setEarlier] = useState(false);
  const line = useRef<HTMLParagraphElement>(null);
  const act = async (action: "restore" | "revert") => {
    setBusy(true);
    setFailed(false);
    try {
      onDone(
        await postJson<ChoiceAnswer<D>>(choiceUrl(draftId, record.row_key), {
          lesson_id: record.lesson_id,
          action,
          // An updated row cites the version it was updated to; a removed row, the version it cited.
          expected_cited_version: action === "revert" ? record.current_version : record.cited_version,
          expected_current_version: record.current_version,
        }),
      );
    } catch {
      setFailed(true);
    } finally {
      setBusy(false);
    }
  };
  const date = <Num date={record.at.slice(0, 10)} />;
  return (
    <div className="flex flex-col gap-2 py-3 pl-6 text-small" data-row-choice={kind}>
      {failed && (
        <Alert state="error" live="alert">
          {n.saveFailed}
        </Alert>
      )}
      <p ref={line} tabIndex={-1} className="text-ink-muted outline-none">
        {kind === "updated" ? (
          <Fill template={n.updatedCaption} slots={{ b: <Num value={record.current_version} />, date }} />
        ) : kind === "kept" ? (
          <Fill template={n.keptCaption} slots={{ a: <Num value={record.cited_version} />, date, reason: record.reason ?? "" }} />
        ) : (
          record.row_label ? (
            <Fill template={n.removedCaption} slots={{ n: String(record.row_label.n), risk: record.row_label.risk_label, date }} />
          ) : (
            <Fill template={n.removedPartCaption} slots={{ part: partName ?? "", date }} />
          )
        )}
      </p>
      {kind === "updated" && earlierText && (
        <div>
          <Button variant="ghost" flush aria-expanded={earlier} onClick={() => setEarlier(!earlier)}>
            {earlier ? n.hideEarlier : n.showEarlier}
          </Button>
          {earlier && <div className="mt-2 border-l-2 border-line-strong pl-3 text-ink-muted" data-earlier-text>{earlierText}</div>}
        </div>
      )}
      {canAct && kind !== "kept" && (
        <div>
          <Button
            variant={kind === "removed" ? "secondary" : "ghost"}
            loading={busy}
            busyLabel={kind === "removed" ? n.busy.restore : n.busy.revert}
            onClick={() => void act(kind === "removed" ? "restore" : "revert")}
            data-choice={kind === "removed" ? "restore" : "revert"}
          >
            {kind === "removed" ? n.restore : fillText(n.goBack, { a: record.cited_version })}
          </Button>
        </div>
      )}
    </div>
  );
}

// The notice under a draft row (the 39 brief, section 2.4): a lead sentence in place of the title and "Used in".
// anchorId is the id the draft bar's hold link goes to: notice-{row_key} unless a part shows several notices.
export function DraftRowNotice<D>({
  notice,
  draftId,
  draftState,
  title,
  canAct,
  author,
  onDone,
  anchorId,
}: {
  notice: NoticeBody & { row_key: string; actions: ("update" | "remove" | "keep")[] };
  draftId: string;
  draftState: string;
  title: string;
  canAct: boolean;
  author: string | null;
  onDone: (answer: ChoiceAnswer<D>, action: "update" | "keep" | "remove") => void;
  anchorId?: string;
}) {
  const leadId = useId();
  return (
    <div role="group" aria-labelledby={leadId} id={anchorId ?? `notice-${notice.row_key}`} className="flex flex-col gap-3 py-4 pl-6" data-row-notice={notice.tier}>
      <div>
        <StatusBadge kind={BADGE[notice.tier]} />
      </div>
      <p id={leadId} tabIndex={-1} className="text-small font-semibold text-ink-heading outline-none">
        <Fill template={n.rowLead[notice.tier]} slots={{ a: <Num value={notice.a} /> }} />
      </p>
      <WasNow notice={notice} onRow />
      <Decided notice={notice} />
      <div>
        <VersionsLink notice={notice} />
      </div>
      {canAct ? (
        <Choices notice={notice} draftId={draftId} rowKey={notice.row_key} draftState={draftState} title={title} actions={notice.actions} holdSentence={notice.holds_export} onDone={onDone} />
      ) : draftState === "exported" ? (
        <p className="text-caption text-ink-muted">{n.exported}</p>
      ) : (
        <p className="text-caption text-ink-muted">{fillText(n.teammate, { name: author ?? "" })}</p>
      )}
    </div>
  );
}


// The evidence drawer's "Two versions of a lesson" (the 39 brief, section 5.7): two blocks, oldest first and with
// equal weight, each with its statement, its tags and the quotes it rests on as Source chips, and the later one with
// the lead's reason. A retired lesson's later block says when and why.
export function VersionsView({ view }: { view: VersionsViewData }) {
  const v = copy.versions;
  const statement = view.changes.find((change) => change.field === "statement");
  const block = (version: VersionBlock, later: boolean) => {
    const headingId = `version-${version.version}`;
    const ranges = statement ? (later ? statement.now_ranges : statement.was_ranges) : [];
    return (
      <section key={version.version} aria-labelledby={headingId} className="flex flex-col gap-2" data-version-block={version.version}>
        <h3 id={headingId} className="text-small font-semibold text-ink-heading">
          {later && view.retired_as ? v.retiredHeading : fillText(v.heading, { n: version.version })}
        </h3>
        <p className="text-caption text-ink-muted">
          <Fill template={v.decidedOn} slots={{ date: <Num date={version.decided_on} /> }} />
          {later && version.version === view.current && <> {v.thisCurrent}</>}
        </p>
        <p className="text-title text-ink-heading">
          <ChangeMarks text={version.statement} ranges={ranges} />
        </p>
        <ul className="flex flex-wrap gap-2">
          {[...(version.categories ?? []), ...(version.methods ?? []), ...version.risk_factors].map((tag) => (
            <li key={tag.key}>
              <Tag>{tag.label}</Tag>
            </li>
          ))}
        </ul>
        <ul className="flex flex-col gap-2">
          {version.evidence.map((evidence) => (
            <li key={evidence.evidence_id} className="flex flex-col items-start gap-1">
              <span className="text-body text-ink">{fillText(copy.lessons.card.quote, { quote: evidence.quote })}</span>
              <SourceChip evidence={evidence} />
            </li>
          ))}
        </ul>
        {later && <p className="max-w-prose text-small text-ink-muted">{fillText(n.decided[view.tier] ?? n.decided.narrowed, { reason: view.reason })}</p>}
      </section>
    );
  };
  return (
    <div className="flex flex-col gap-6 px-6 py-4" data-versions-view>
      <p className="text-caption text-ink-muted">{fillText(v.caption, { b: view.current })}</p>
      {block(view.versions[0], false)}
      {view.between.map((between) => (
        <p key={between.version} className="text-caption text-ink-muted">
          <Fill template={v.between} slots={{ n: <Num value={between.version} />, date: <Num date={between.decided_on} style="table" /> }} />
        </p>
      ))}
      {block(view.versions[1], true)}
    </div>
  );
}

// Under a part of a draft whose kind has no rows of its own, such as the Project Paper summary's PPSD part, which cites
// the lessons its checked rows cite (ticket 39): the part's version notice, or the choice its author kept. A removed
// part has left the notes, so the page lists it after them with RemovedParts.
// A part can cite several lessons, so it shows a notice for each, those that hold the export first, and only the first
// takes the part's anchor, which the draft bar's hold link goes to. Each choice its author kept follows, for a lesson
// with no newer notice.
export function NoteLesson({ draft, noteKey, onDone }: { draft: Draft; noteKey: string; onDone: (draft: Draft) => void }) {
  const canAct = Boolean(draft.lesson_can_act);
  const notices = (draft.lesson_notices ?? [])
    .filter((one) => one.row_key === noteKey)
    .sort((one, other) => Number(other.holds_export) - Number(one.holds_export));
  const kept = (draft.lesson_kept ?? []).filter((one) => one.row_key === noteKey && !notices.some((notice) => notice.lesson_id === one.lesson_id));
  if (notices.length === 0 && kept.length === 0) return null;
  const title = draftTitle(draft.kind, draft.subject as unknown as Record<string, string | null>);
  return (
    <>
      {notices.map((notice, index) => (
        <DraftRowNotice<Draft>
          key={`${notice.lesson_id}-v${notice.a}`}
          notice={notice}
          draftId={draft.draft_id}
          draftState={draft.state}
          title={title}
          canAct={canAct && notice.can_act}
          author={draft.author.name}
          onDone={(answer) => onDone(answer.draft)}
          anchorId={index === 0 ? `notice-${noteKey}` : `notice-${noteKey}-${notice.lesson_id}-v${notice.a}`}
        />
      ))}
      {kept.map((entry) => (
        <RowChoice<Draft> key={`kept-${entry.lesson_id}`} record={entry} kind="kept" draftId={draft.draft_id} canAct={canAct} onDone={(answer) => onDone(answer.draft)} />
      ))}
    </>
  );
}

export function RemovedParts({ draft, names, onDone }: { draft: Draft; names: Record<string, string>; onDone: (draft: Draft) => void }) {
  const removed = draft.lesson_removed ?? [];
  if (removed.length === 0) return null;
  return (
    <div className="flex flex-col" data-removed-parts>
      {removed.map((entry) => (
        <RowChoice<Draft> key={`${entry.row_key}-${entry.lesson_id}`} record={entry} kind="removed" draftId={draft.draft_id} canAct={Boolean(draft.lesson_can_act)} partName={names[entry.row_key]} onDone={(answer) => onDone(answer.draft)} />
      ))}
    </div>
  );
}
