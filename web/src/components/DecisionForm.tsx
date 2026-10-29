// The decision form and its parts (DESIGN.md section 5; the 29 brief, sections 3.2, 4.5 and 5.10 to 5.12).
//
// - ReasonField: brief 23's labelled textarea, 3 rows and at most 500 characters, with a helper linked by
//   aria-describedby, a counter "{n} characters left." from 400 characters that a screen reader hears only at
//   100, 50 and 0 left, and an error line under it.
// - LessonEditor: a lead's change to the statement (at most 80 characters, the counter from 60), the risk
//   factors, the stage and the kind, from the closed lists. Quotes and pages are never editable.
// - DecisionForm: a card holding a form named by its h2. An outcome fieldset when the kind needs one, the
//   editor when opened, the reason field, buttons named for what they do, and a caption that says what the
//   button will do. The server decides who may act; the form only asks for what the act needs, checks it in
//   the browser first, and sends the stage the viewer saw, so an act on an item that moved on is refused as
//   stale and nothing typed is lost.
import { useEffect, useId, useRef, useState, type ReactNode, type Ref } from "react";
import { ChevronDown } from "lucide-react";
import { copy } from "../copy";
import { ApiError, postJson } from "../lib/api";
import { cx } from "../lib/cx";
import type { Item, Refusal, ReviewItem, Saved } from "../lib/lessons";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { InfoWindow } from "./MadeBy";
import { fillText } from "./LessonParts";
import { Num } from "./Num";

const words = copy.lessons.form;
const COUNTER_FROM = 100; // characters left when the counter shows: 400 of 500, 60 of 80
const SPOKEN = new Set([100, 50, 0]);

// ── The reason field ─────────────────────────────────────────────────────

export function ReasonField({
  ref,
  label,
  helper,
  value,
  onChange,
  max,
  error,
  disabled = false,
  rows = 3,
  countFrom = COUNTER_FROM,
  readOnly = false,
}: {
  ref?: Ref<HTMLTextAreaElement>;
  label: ReactNode;
  helper?: ReactNode;
  value: string;
  onChange?: (value: string) => void;
  max: number;
  error?: string | null;
  disabled?: boolean;
  rows?: number;
  // How many characters left when the counter starts to show.
  countFrom?: number;
  readOnly?: boolean;
}) {
  const id = useId();
  const left = max - value.length;
  const [spoken, setSpoken] = useState("");
  useEffect(() => {
    if (SPOKEN.has(left) && left <= countFrom) setSpoken(left === 1 ? words.counterOne : fillText(words.counter, { count: left }));
  }, [left, countFrom]);
  const described = [helper && `${id}-helper`, error && `${id}-error`].filter(Boolean).join(" ") || undefined;
  return (
    <div className="flex flex-col gap-1" data-reason-field>
      <label htmlFor={id} className="text-small font-bold text-ink-heading">
        {label}
      </label>
      {helper && (
        <p id={`${id}-helper`} className="max-w-prose text-caption text-ink-muted">
          {helper}
        </p>
      )}
      <textarea
        ref={ref}
        id={id}
        rows={rows}
        maxLength={max}
        value={value}
        readOnly={readOnly}
        disabled={disabled}
        aria-invalid={error ? true : undefined}
        aria-describedby={described}
        onChange={(event) => onChange?.(event.target.value)}
        className={cx(
          "mt-1 w-full rounded-sm border bg-surface px-3 py-2 text-body text-ink",
          error ? "border-error-icon" : "border-line-strong",
          disabled && "cursor-not-allowed bg-surface-2 text-ink-muted",
          readOnly && "bg-surface-2",
        )}
      />
      {left <= countFrom && !readOnly && (
        <p aria-hidden="true" className="text-caption text-ink-muted tabular-nums">
          {left === 1 ? words.counterOne : <Fill template={words.counter} slots={{ count: <Num value={left} options={{ compact: false }} /> }} />}
        </p>
      )}
      <p role="status" className="clip-visually">
        {spoken}
      </p>
      {error && (
        <p id={`${id}-error`} className="text-small text-error">
          {error}
        </p>
      )}
    </div>
  );
}

// ── Radio and checkbox rows ──────────────────────────────────────────────

// A radio or checkbox row, at least 44 px tall with the whole label as its target; the control itself is 24 px,
// the smallest target WCAG 2.5.8 allows. The control sits on the first line of its label, so a label that wraps
// to three lines still reads as its own, rows sit at least 16 px apart, and the control's left edge meets the
// legend's (the row's hover fill reaches 8 px past it).
function Choice({ type, groupId, checked, onChange, children, disabled }: {
  type: "radio" | "checkbox";
  // The input group's name, which ties each group's radios together.
  groupId: string;
  checked: boolean;
  onChange: () => void;
  children: ReactNode;
  disabled?: boolean;
}) {
  return (
    <label className={cx("-mx-2 flex min-h-11 cursor-pointer items-start gap-3 rounded-sm px-2 py-2 hover:bg-tint-hover", disabled && "cursor-not-allowed")}>
      <input type={type} name={groupId} checked={checked} onChange={onChange} disabled={disabled} className="mt-0.5 size-6 shrink-0 accent-primary" />
      <span className="text-body text-ink">{children}</span>
    </label>
  );
}

function Fieldset({ legend, error, children, legendRef }: { legend: ReactNode; error?: string | null; children: ReactNode; legendRef?: Ref<HTMLFieldSetElement> }) {
  const id = useId();
  return (
    <fieldset ref={legendRef} tabIndex={-1} aria-invalid={error ? true : undefined} aria-describedby={error ? id : undefined} className="flex flex-col outline-none">
      <legend className="mb-1 text-small font-bold text-ink-heading">{legend}</legend>
      {children}
      {error && (
        <p id={id} className="mt-1 text-small text-error">
          {error}
        </p>
      )}
    </fieldset>
  );
}

// ── The lesson editor ────────────────────────────────────────────────────

// Ticket 39 adds procurement categories and selection methods, from the package form's closed lists; a lesson that
// names none applies to every category and method.
export type Change = { statement: string; risk_factors: string[]; stage: string; kind: string; categories?: string[]; methods?: string[] };
type ChangeErrors = Partial<Record<keyof Change, string>>;

export function validChange(change: Change, max: number): ChangeErrors {
  const errors: ChangeErrors = {};
  const statement = change.statement.trim();
  if (!statement) errors.statement = words.errors.statement;
  else if (statement.length > max) errors.statement = fillText(words.errors.statementLong, { count: max });
  if (change.risk_factors.length === 0) errors.risk_factors = words.errors.riskFactors;
  if (!change.stage) errors.stage = words.errors.stage;
  if (!change.kind) errors.kind = words.errors.kind;
  return errors;
}

export function LessonEditor({ value, onChange, lists, max, errors, disabled }: {
  value: Change;
  onChange: (value: Change) => void;
  lists: { risk_factors: Item[]; stages: Item[]; kinds: Item[]; categories?: Item[]; methods?: Item[] };
  max: number;
  errors: ChangeErrors;
  disabled?: boolean;
}) {
  const name = useId();
  const e = words.editor;
  const toggle = (key: string) =>
    onChange({ ...value, risk_factors: value.risk_factors.includes(key) ? value.risk_factors.filter((one) => one !== key) : [...value.risk_factors, key] });
  return (
    <div data-lesson-editor className="flex animate-open-in flex-col gap-4 rounded-sm border border-line bg-surface-2 p-4 motion-reduce:animate-none">
      <ReasonField
        label={e.statement}
        value={value.statement}
        onChange={(statement) => onChange({ ...value, statement })}
        max={max}
        rows={2}
        countFrom={20}
        error={errors.statement}
        disabled={disabled}
      />
      <Fieldset legend={e.riskFactors} error={errors.risk_factors}>
        <div className="grid gap-x-4 @md/page:grid-cols-2">
          {lists.risk_factors.map((item) => (
            <Choice key={item.key} type="checkbox" groupId={`${name}-risk`} checked={value.risk_factors.includes(item.key)} onChange={() => toggle(item.key)} disabled={disabled}>
              {item.label}
            </Choice>
          ))}
        </div>
      </Fieldset>
      <Fieldset legend={e.stage} error={errors.stage}>
        {lists.stages.map((item) => (
          <Choice key={item.key} type="radio" groupId={`${name}-stage`} checked={value.stage === item.key} onChange={() => onChange({ ...value, stage: item.key })} disabled={disabled}>
            {item.label}
          </Choice>
        ))}
      </Fieldset>
      <Fieldset legend={e.kind} error={errors.kind}>
        {lists.kinds.map((item) => (
          <Choice key={item.key} type="radio" groupId={`${name}-kind`} checked={value.kind === item.key} onChange={() => onChange({ ...value, kind: item.key })} disabled={disabled}>
            {item.label}
          </Choice>
        ))}
      </Fieldset>
      {(["categories", "methods"] as const).map((list) =>
        lists[list] ? (
          <Fieldset key={list} legend={e[list]}>
            <div className="grid gap-x-4 @md/page:grid-cols-2">
              {lists[list]!.map((item) => {
                const chosen = value[list] ?? [];
                return (
                  <Choice
                    key={item.key}
                    type="checkbox"
                    groupId={`${name}-${list}`}
                    checked={chosen.includes(item.key)}
                    onChange={() => onChange({ ...value, [list]: chosen.includes(item.key) ? chosen.filter((one) => one !== item.key) : [...chosen, item.key] })}
                    disabled={disabled}
                  >
                    {item.label}
                  </Choice>
                );
              })}
            </div>
          </Fieldset>
        ) : null,
      )}
      <p className="text-caption text-ink-muted">{e.fixed}</p>
    </div>
  );
}

// ── The decision form ────────────────────────────────────────────────────

export type Verb = "recommend" | "decide" | "cross_check";
// What happened after a save: the act, the outcome chosen, and the server's answer.
export type Done = { verb: Verb; choice: string; saved: Saved };
// Why the form gave way: a refusal by reason code, or the item moved on while it was open.
export type GaveWay = { kind: "refused"; code: string; values: Record<string, string>; verb: Verb } | { kind: "stale"; reason: string; item: ReviewItem } | { kind: "lost" };

type Failure = null | "failed";

export function currentChange(item: ReviewItem): Change {
  return {
    statement: item.statement ?? "",
    risk_factors: (item.tags.risk_factors ?? []).map((factor) => factor.key),
    stage: item.tags.stage?.key ?? "",
    kind: item.tags.kind?.key ?? "",
    categories: (item.tags.categories ?? []).map((tag) => tag.key),
    methods: (item.tags.methods ?? []).map((tag) => tag.key),
  };
}

export function DecisionForm({ item, onDone, onGaveWay, initial }: {
  item: ReviewItem;
  onDone: (done: Done) => void;
  onGaveWay: (gaveWay: GaveWay) => void;
  // A gallery sample's or a test's starting state.
  // choiceKey and savingKey name an outcome, such as keep, or a button, such as add.
  initial?: { choiceKey?: string; reason?: string; editor?: boolean; errors?: boolean; failed?: boolean; savingKey?: string };
}) {
  const verb = item.can.act as Verb;
  const recheck = item.kind === "recheck";
  const crossCheck = item.kind === "cross_check";
  const repeats = item.repeats;
  const max = item.limits.reason_max_chars;
  const headingId = useId();
  const [choice, setChoice] = useState<string>(initial?.choiceKey ?? "");
  const [reason, setReason] = useState(initial?.reason ?? "");
  const recommended = item.recommendation?.change as Partial<Change> | null | undefined;
  const [change, setChange] = useState<Change>(() => ({ ...currentChange(item), ...(verb === "decide" && recommended ? recommended : {}) }));
  const [editor, setEditor] = useState(initial?.editor ?? false);
  const [showErrors, setShowErrors] = useState(initial?.errors ?? false);
  const [saving, setSaving] = useState<string | null>(initial?.savingKey ?? null);
  const [failure, setFailure] = useState<Failure>(initial?.failed ? "failed" : null);
  const fieldset = useRef<HTMLFieldSetElement>(null);
  const reasonRef = useRef<HTMLTextAreaElement>(null);
  const form = useRef<HTMLFormElement>(null);
  const lastOutcome = useRef<string>(recheck || crossCheck ? "one" : "add");

  // What the act needs, by kind: the outcome fieldset, the choices it offers, the reason's words.
  const needsChoice = recheck || crossCheck || repeats.length > 0;
  const editorShown = recheck ? choice === "change" : verb === "decide" && editor && (!needsChoice || choice === "add");
  const reasonOptional = crossCheck && choice === "agree";
  const region = item.decided?.region ?? item.region;
  const helper = crossCheck
    ? fillText(words.reasonHelperCrossCheck, { region })
    : verb === "recommend"
      ? words.reasonHelperRecommend
      : recheck
        ? words.reasonHelperRecheckDecide
        : words.reasonHelperDecide;
  const noReason = crossCheck ? fillText(words.errors.noReasonCrossCheck, { region }) : verb === "recommend" ? words.errors.noReasonRecommend : words.errors.noReasonDecide;
  const noChoice = crossCheck ? words.errors.noChoiceCrossCheck : recheck ? words.errors.noChoiceRecheck : words.errors.noChoiceNew;
  const changeErrors = editorShown ? validChange(change, item.limits.statement_max_chars) : {};

  // A new lesson's two buttons each carry their outcome; a re-check or cross-check has one button.
  const errorsFor = (outcome: string) => ({
    choice: needsChoice && !(outcome === "reject") && !choiceFor(outcome) ? noChoice : null,
    reason: !reason.trim() && !(crossCheck && choiceFor(outcome) === "agree") ? noReason : null,
  });
  function choiceFor(outcome: string): string {
    if (recheck || crossCheck) return choice;
    if (outcome === "reject") return "reject";
    return choice;
  }
  const shownErrors = showErrors ? errorsFor(saving ?? lastOutcome.current) : { choice: null, reason: null };

  async function send(outcome: string) {
    lastOutcome.current = outcome;
    const found = errorsFor(outcome);
    const editorErrors = Object.keys(changeErrors).length > 0;
    if (found.choice || found.reason || editorErrors) {
      setShowErrors(true);
      requestAnimationFrame(() => {
        if (found.choice) fieldset.current?.focus();
        else if (editorErrors) form.current?.querySelector<HTMLElement>("[data-lesson-editor] [aria-invalid=true], [data-lesson-editor] fieldset[aria-invalid=true] input")?.focus();
        else reasonRef.current?.focus();
      });
      return;
    }
    const chosen = choiceFor(outcome);
    const body: Record<string, unknown> = { expected_stage: item.stage, reason: reason.trim() || null };
    if (crossCheck) body.agree = chosen === "agree";
    else if (recheck) body.outcome = chosen;
    else if (chosen === "reject") body.outcome = "reject";
    else if (chosen && chosen !== "add") {
      body.outcome = "repeat";
      body.repeat_of = chosen;
    } else body.outcome = "add";
    if (editorShown) body.change = change;
    setSaving(outcome);
    setFailure(null);
    try {
      const saved = await postJson<Saved>(`/api/lessons/review/${encodeURIComponent(item.item_id)}/${verb === "cross_check" ? "cross-check" : verb}`, body);
      onDone({ verb, choice: crossCheck ? chosen : String(body.outcome), saved });
    } catch (error) {
      setSaving(null);
      const refusal = error instanceof ApiError ? (error.body as unknown as Refusal) : null;
      if (refusal?.code === "stale" && refusal.item) onGaveWay({ kind: "stale", reason, item: refusal.item });
      else if (refusal?.code === "not_a_reviewer") onGaveWay({ kind: "lost" });
      else if (refusal?.code && refusal.code in copy.lessons.review.cannot) onGaveWay({ kind: "refused", code: refusal.code, values: refusal.values ?? {}, verb });
      else setFailure("failed");
    }
  }

  const options: { value: string; label: ReactNode }[] = crossCheck
    ? [
        { value: "agree", label: words.agree },
        { value: "disagree", label: words.disagree },
      ]
    : recheck
      ? [
          { value: "keep", label: words.keep },
          { value: "change", label: words.change },
          { value: "retire_wrong", label: words.retireWrong },
          { value: "retire_outdated", label: words.retireOutdated },
        ]
      : [
          { value: "add", label: words.yesNew },
          ...repeats.map((repeat) => ({
            value: repeat.lesson_id,
            label: <Fill template={words.repeats} slots={{ statement: repeat.statement, version: <Num value={repeat.version} /> }} />,
          })),
        ];
  const repeat = repeats.find((one) => one.lesson_id === choice);
  const version = item.lesson.version ?? 0;
  const feedforward: ReactNode = crossCheck
    ? null
    : recheck
      ? verb === "recommend"
        ? words.feedforwardRecheckRecommend
        : choice === "keep"
          ? <Fill template={words.feedforwardKeep} slots={{ version: <Num value={version} /> }} />
          : choice === "change"
            ? <Fill template={words.feedforwardChange} slots={{ next: item.lesson.next_version ? <Num value={item.lesson.next_version} /> : "", version: <Num value={version} /> }} />
            : choice.startsWith("retire")
              ? words.feedforwardRetire
              : null
      : verb === "recommend"
        ? words.feedforwardRecommend
        : repeat
          ? <Fill template={words.feedforwardRepeat} slots={{ statement: repeat.statement, version: repeat.next_version ? <Num value={repeat.next_version} /> : "" }} />
          : words.feedforwardAdd;
  const title = crossCheck ? words.crossCheckTitle : verb === "recommend" ? words.recommendTitle : words.decideTitle;
  const legend = crossCheck ? words.agreeLegend : recheck ? words.whatShouldHappen : words.isNew;
  const busy = saving !== null;
  const buttons: { outcome: string; label: string; variant: "primary" | "secondary" }[] = crossCheck
    ? [{ outcome: "one", label: words.saveCrossCheck, variant: "primary" }]
    : recheck
      ? [{ outcome: "one", label: verb === "recommend" ? words.recommend : words.saveDecision, variant: "primary" }]
      : verb === "recommend"
        ? [
            { outcome: "add", label: words.recommendAdd, variant: "primary" },
            { outcome: "reject", label: words.recommendReject, variant: "secondary" },
          ]
        : [
            { outcome: "add", label: words.add, variant: "primary" },
            { outcome: "reject", label: words.reject, variant: "secondary" },
          ];

  return (
    // A div, so the form named by the h2 is the one landmark it gives a screen reader.
    <div data-decision-form={`${item.kind}-${verb}`} className="rounded-md border border-line bg-surface p-4 @md/page:p-6">
      <form
        ref={form}
        noValidate
        aria-labelledby={headingId}
        aria-busy={busy || undefined}
        onSubmit={(event) => event.preventDefault()}
        className="flex flex-col gap-4"
      >
        <h2 id={headingId} className="text-h2 text-ink-heading">
          {title}
        </h2>
        {failure && (
          <Alert
            state="error"
            live="alert"
            action={
              <Button variant="secondary" onClick={() => void send(lastOutcome.current)}>
                {words.tryAgain}
              </Button>
            }
          >
            {fillText(words.failed, { act: words.acts[verb] })}
          </Alert>
        )}
        {crossCheck && item.decided && (
          // How cross-checks work, which the reviewer reads once, is in the window after the sentence (ticket 126).
          <p className="max-w-prose text-body text-ink">
            <Fill template={words.crossCheckIntro} slots={{ region: item.decided.region, date: item.decided.on ? <Num date={item.decided.on} /> : "" }} />
            <InfoWindow name={words.crossCheckName} kind="note">
              <Fill template={words.crossCheckWhy} slots={{ percent: <Num value={item.limits.sample_percent} /> }} />
            </InfoWindow>
          </p>
        )}
        {needsChoice && (
          <Fieldset legend={legend} error={shownErrors.choice} legendRef={fieldset}>
            {options.map((option) => (
              <Choice key={option.value} type="radio" groupId={`${headingId}-choice`} checked={choice === option.value} onChange={() => setChoice(option.value)} disabled={busy}>
                {option.label}
              </Choice>
            ))}
            {!recheck && !crossCheck && verb === "recommend" && repeat && (
              <p className="mt-1 text-caption text-ink-muted">
                <Fill template={words.repeatFeedforward} slots={{ statement: repeat.statement }} />
              </p>
            )}
          </Fieldset>
        )}
        {!recheck && !crossCheck && verb === "decide" && (!needsChoice || choice === "add") && (
          <div>
            <Button variant="ghost" flush aria-expanded={editor} onClick={() => setEditor(!editor)} icon={ChevronDown}>
              {words.editorToggle}
            </Button>
          </div>
        )}
        {editorShown && (
          <LessonEditor
            value={change}
            onChange={setChange}
            lists={item.lists}
            max={item.limits.statement_max_chars}
            errors={showErrors ? changeErrors : {}}
            disabled={busy}
          />
        )}
        <ReasonField
          ref={reasonRef}
          label={words.reasonLabel}
          helper={helper}
          value={reason}
          onChange={setReason}
          max={max}
          error={reasonOptional ? null : shownErrors.reason}
          disabled={busy}
        />
        <div className="flex flex-col gap-3 @md/page:flex-row @md/page:flex-wrap">
          {buttons.map((button) => (
            <Button
              key={button.outcome}
              variant={button.variant}
              loading={saving === button.outcome}
              busyLabel={words.saving}
              disabled={busy && saving !== button.outcome}
              onClick={() => void send(button.outcome)}
              className="w-full @md/page:w-auto"
            >
              {button.label}
            </Button>
          ))}
        </div>
        {feedforward && <p className="max-w-prose text-caption text-ink-muted">{feedforward}</p>}
      </form>
    </div>
  );
}
