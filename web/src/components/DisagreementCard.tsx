// Disagreement card (DESIGN.md section 5; the 24 brief, section 4.4, and the 23 brief, section 5): two sources
// that disagree, side by side in the order they were written, with equal weight: the same box, type and spacing on
// both sides, and the role of each named only by a quiet source tag, "Strata leans on this" or "You kept this". A
// heading names what they disagree about; one sentence states the evidence ladder's rule, a line says what you
// would treat as true if you kept the other, and a keep line says where you can keep it.
//
// Warning state with "Two reports disagree" when keeping the other side would change a sentence in the answer or
// draft; otherwise the info state with "Sources differ". Never red: a disagreement is not an error. The card is a
// surface box with a 4px left border in its state's icon colour.
//
// The card is a size container: its sides sit side by side when the card itself is 560 px (35rem) wide or more, and
// stack, the earlier on top, below that, so it reads the same in the answer, in the drawer and on a project page.
// While they sit side by side, each side keeps a 24 px tag row, so both claims start on one line.
//
// Ticket 24 placed the card in an answer; ticket 23 gives it this look and the keep action (KeepChoice): a person
// keeps the other report with a required reason, stored with their name and the answer or draft for the evidence
// pack, and can go back to Strata's choice. Neither rewrites the answer.
import { createElement, useEffect, useId, useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import { ApiError, getJson, postJson } from "../lib/api";
import type { SideData } from "../lib/disagreement";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { Button } from "./Button";
import { ReasonField } from "./DecisionForm";
import { Source } from "./Source";
import { SourceTag } from "./SourceTag";
import { StatusBadge } from "./StatusBadge";

const words = copy.disagreement.card;
// The reason a person gives for keeping the other report: at most 500 characters, as the server takes it.
const REASON_LIMIT = 500;

export type CardSide = {
  // The side's name: "ISR 7" on the timeline, or spelled out in an answer.
  title: ReactNode;
  // The same as text, which names its list item.
  titleText: string;
  // "{date}. {written when}."
  meta: string;
  // The side Strata leans on carries the tag.
  leaned: boolean;
  // What the source said: a rating under the report's own field name, or a quote.
  said: ReactNode;
  // When get_disagreements gives it: how long after the moment the side was made.
  context?: ReactNode;
  source?: ReactNode;
  // A citation marker, in an answer, for a side whose source has a number there.
  marker?: ReactNode;
  // "Open ISR 7": a side's tab in the drawer, or the drawer at that source from an answer.
  open?: { label: string; href: string; onOpen: (element: HTMLElement) => void };
  assertionId?: string;
};

// What keeping the other report is stored with: the answer's run or the draft (POST /api/disagreements/{id}/choices).
export type KeepTarget = { disagreementId: string; runId: string | null; draftId: string | null; preview: boolean };

export type Keep = {
  // The other report's short name: "ISR 7".
  other: string;
  otherAssertionId: string;
  leanAssertionId: string;
  // Null on the timeline and in a document view, where no answer or draft rests on the two reports.
  target: KeepTarget | null;
};

export function DisagreementCard({
  warning,
  name,
  subject,
  level = 3,
  sides,
  rule,
  whatChanges,
  changes,
  keep,
  leanTag = copy.disagreement.lean,
  initialKept = null,
  initialReason = "",
  initialBackFailed = false,
  sample = false,
}: {
  warning: boolean;
  // The group's accessible name: the badge's words and the two sources.
  name: string;
  subject?: ReactNode;
  // The heading's level: 3 in the drawer, 4 in an answer.
  level?: 3 | 4;
  sides: [CardSide, CardSide];
  rule: string;
  whatChanges?: string;
  // "That changes one sentence in this answer."
  changes?: string;
  keep?: Keep;
  leanTag?: string;
  // A design gallery sample's starting state of the keep action.
  initialKept?: KeepState | null;
  initialReason?: string;
  initialBackFailed?: boolean;
  sample?: boolean;
}) {
  const [kept, setKept] = useState<string | null>(initialKept?.phase === "kept" ? (keep?.otherAssertionId ?? null) : null);
  return (
    <div
      role="group"
      aria-label={name}
      data-disagreement={warning ? "warning" : "info"}
      className={cx("@container/disagreement rounded-r-md border border-l-4 border-line bg-surface p-4", warning ? "border-l-warning-icon" : "border-l-info-icon")}
    >
      <StatusBadge kind={warning ? "two-reports-disagree" : "sources-differ"} />
      {subject && createElement(`h${level}`, { className: "mt-2 text-title text-ink-heading", "data-card-subject": "" }, subject)}
      <ul aria-label={words.sides} data-disagreement-sides className="mt-4 grid grid-cols-1 gap-3 @min-[35rem]/disagreement:grid-cols-2">
        {sides.map((side, index) => {
          const keptThis = Boolean(kept && side.assertionId === kept);
          const tags = side.leaned || keptThis;
          return (
            <li key={index} data-side={side.leaned ? "leaned" : "other"} aria-label={side.titleText} className="flex min-w-0 flex-col rounded-md border border-line bg-surface p-4">
              <div className="flex items-start justify-between gap-2">
                <p className="text-small font-bold text-ink-heading [overflow-wrap:anywhere]">{side.title}</p>
                {side.marker && <span className="shrink-0">{side.marker}</span>}
              </div>
              <p className="mt-1 text-caption text-ink-muted">{side.meta}</p>
              <div data-tag-row className={cx("mt-2 min-h-6 flex-wrap gap-2", tags ? "flex" : "hidden @min-[35rem]/disagreement:flex")}>
                {side.leaned && <SourceTag>{leanTag}</SourceTag>}
                {keptThis && <SourceTag className="animate-fade-in">{words.kept}</SourceTag>}
              </div>
              <div className="mt-2">{side.said}</div>
              {side.context && <p className="mt-2 text-caption text-ink-muted">{side.context}</p>}
              {side.source && <Source className="mt-3">{side.source}</Source>}
              {side.open && (
                <p className="mt-2">
                  <a
                    href={side.open.href}
                    data-open-side
                    onClick={(event) => {
                      if (event.metaKey || event.ctrlKey || event.shiftKey || event.button !== 0) return;
                      event.preventDefault();
                      side.open!.onOpen(event.currentTarget);
                    }}
                    className="inline-flex min-h-6 items-center py-1 text-small text-primary underline underline-offset-3 hover:text-link-hover"
                  >
                    {side.open.label}
                  </a>
                </p>
              )}
            </li>
          );
        })}
      </ul>
      <p className="mt-4 text-small text-ink">{rule}</p>
      {whatChanges && (
        <p className="mt-2 text-small text-ink">
          {whatChanges}
          {changes && <> {changes}</>}
        </p>
      )}
      {keep && <KeepChoice keep={keep} onKept={setKept} initial={initialKept} initialReason={initialReason} initialBackFailed={initialBackFailed} sample={sample} />}
    </div>
  );
}

// What a side said: a rating under the report's own field name, or its words in straight quotes.
export function SideSaid({ side }: { side: SideData }) {
  if (side.quote) {
    return (
      <p lang="en" className="text-small text-ink">
        {copy.removed.quoted(side.sentence ?? side.quote)}
      </p>
    );
  }
  return (
    <>
      <p className="text-caption text-ink-muted">{side.field_name}</p>
      <p className="text-small font-semibold text-ink">{side.value}</p>
    </>
  );
}

// The keep action's state: the button, the form open, saving, a failed save, or a kept choice with its date and
// reason.
export type KeepState =
  | { phase: "idle" }
  | { phase: "open"; error?: boolean }
  | { phase: "saving" }
  | { phase: "failed" }
  | { phase: "kept"; madeAt: string; reason: string };

// The text a person typed stays for the session, so reopening the form after Cancel restores it.
const drafts = new Map<string, string>();

type Choice = { kept_assertion_id: string; leaned_assertion_id: string; reason: string | null; made_at: string; kept_other: boolean };

function KeepChoice({
  keep,
  onKept,
  initial,
  initialReason,
  initialBackFailed,
  sample,
}: {
  keep: Keep;
  onKept: (assertionId: string | null) => void;
  initial: KeepState | null;
  initialReason: string;
  initialBackFailed: boolean;
  sample: boolean;
}) {
  const target = keep.target;
  const key = target ? `${target.disagreementId}|${target.runId ?? ""}|${target.draftId ?? ""}` : "";
  const [state, setState] = useState<KeepState>(initial ?? { phase: "idle" });
  const [reason, setReason] = useState(() => drafts.get(key) ?? initialReason);
  const [said, setSaid] = useState("");
  // Going back to Strata's choice failed: the kept choice stays, with a line that says so.
  const [backFailed, setBackFailed] = useState(initialBackFailed);
  const button = useRef<HTMLButtonElement>(null);
  const field = useRef<HTMLTextAreaElement>(null);
  const keptLine = useRef<HTMLParagraphElement>(null);
  const formId = useId();
  const fill = (template: string) => template.replace("{other}", keep.other);
  const query = target ? (target.runId ? `run_id=${encodeURIComponent(target.runId)}` : `draft_id=${encodeURIComponent(target.draftId ?? "")}`) : "";
  const path = target ? `/api/disagreements/${encodeURIComponent(target.disagreementId)}/choices` : "";

  // A card shown again after Back takes the latest choice this person made for this answer or draft.
  useEffect(() => {
    if (!target || target.preview || sample || initial) return;
    let live = true;
    getJson<{ choice: Choice | null }>(`${path}?${query}`).then(
      ({ choice }) => {
        if (!live || !choice || !choice.kept_other) return;
        setState({ phase: "kept", madeAt: choice.made_at, reason: choice.reason ?? "" });
        onKept(choice.kept_assertion_id);
      },
      () => undefined,
    );
    return () => {
      live = false;
    };
  }, [path, query]);

  if (!target) {
    return <p className="mt-2 text-small text-ink-muted">{fill(words.keep.lineNoTarget)}</p>;
  }
  if (target.preview) {
    return <p className="mt-2 text-small text-ink-muted">{words.keep.preview}</p>;
  }

  const save = async (kept: string, text: string) => {
    const body = { kept_assertion_id: kept, reason: text, ...(target.runId ? { run_id: target.runId } : { draft_id: target.draftId }) };
    return postJson<{ recorded: boolean; choice?: Choice }>(path, body);
  };

  const submit = async () => {
    const text = reason.trim();
    if (!text) {
      setState({ phase: "open", error: true });
      field.current?.focus();
      return;
    }
    setState({ phase: "saving" });
    try {
      const answer = await save(keep.otherAssertionId, text);
      if (!answer.recorded || !answer.choice) throw new ApiError(503, path);
      drafts.delete(key);
      setState({ phase: "kept", madeAt: answer.choice.made_at, reason: answer.choice.reason ?? text });
      onKept(keep.otherAssertionId);
      setSaid(fill(words.keep.saved));
      requestAnimationFrame(() => keptLine.current?.focus());
    } catch {
      setState({ phase: "failed" });
    }
  };

  const goBack = async () => {
    setBackFailed(false);
    try {
      const answer = await save(keep.leanAssertionId, "");
      if (!answer.recorded) throw new ApiError(503, path);
      setState({ phase: "idle" });
      onKept(null);
      setSaid(words.keep.wentBack);
      requestAnimationFrame(() => button.current?.focus());
    } catch {
      setBackFailed(true);
    }
  };

  const close = () => {
    setState({ phase: "idle" });
    requestAnimationFrame(() => button.current?.focus());
  };

  const open = state.phase === "open" || state.phase === "saving" || state.phase === "failed";
  return (
    <div data-keep={state.phase} className="mt-2">
      {state.phase === "kept" ? (
        <>
          <p ref={keptLine} tabIndex={-1} data-kept-line className="text-small text-ink-muted focus:outline-none">
            {words.keep.kept.replace("{other}", keep.other).replace("{date}", formatDate(state.madeAt.slice(0, 10))).replace("{reason}", state.reason)}
          </p>
          <Button variant="ghost" className="mt-3" flush onClick={goBack}>
            {words.keep.undo}
          </Button>
          {backFailed && <p className="mt-1 text-caption text-error">{fill(words.keep.backFailed)}</p>}
        </>
      ) : (
        <>
          <p className="text-small text-ink-muted">{fill(words.keep.line)}</p>
          {!open && (
            <Button
              ref={button}
              variant="secondary"
              className="mt-3"
              aria-expanded={false}
              aria-controls={formId}
              onClick={() => {
                setState({ phase: "open" });
                requestAnimationFrame(() => field.current?.focus());
              }}
            >
              {fill(words.keep.button)}
            </Button>
          )}
        </>
      )}
      {open && (
        <form
          id={formId}
          aria-busy={state.phase === "saving" || undefined}
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
          onKeyDown={(event) => {
            if (event.key !== "Escape") return;
            event.preventDefault();
            event.stopPropagation();
            close();
          }}
          className="mt-3 flex flex-col gap-3"
        >
          <ReasonField
            ref={field}
            max={REASON_LIMIT}
            label={fill(words.keep.label)}
            helper={target.runId ? words.keep.helperAnswer : words.keep.helperDraft}
            value={reason}
            onChange={(value) => {
              setReason(value);
              drafts.set(key, value);
              if (state.phase === "open" && state.error && value.trim()) setState({ phase: "open" });
            }}
            error={state.phase === "open" && state.error ? fill(words.keep.empty) : null}
          />
          {state.phase === "failed" && <p className="text-caption text-error">{words.keep.failed}</p>}
          <div className="flex flex-wrap gap-2">
            <Button type="submit" variant="secondary" loading={state.phase === "saving"} busyLabel={words.keep.saving}>
              {state.phase === "failed" ? words.keep.retry : fill(words.keep.submit)}
            </Button>
            <Button variant="ghost" onClick={close}>
              {words.keep.cancel}
            </Button>
          </div>
        </form>
      )}
      <p aria-live="polite" className="sr-only">
        {said}
      </p>
    </div>
  );
}
