// The evidence drawer's feedback row (DESIGN.md section 5, Evidence drawer; the 32 brief, sections 2.2, 4.1 and
// 5.1): "Was this the right passage?" with "Wrong passage" and "Not useful" as ghost toggle buttons, at the end
// of the drawer's content, never sticky, so you judge a passage only after reading it.
//
// Choosing a kind presses its button and opens an optional reason field, already focused; "Send the report"
// writes one passage report and an Outcome panel says what happens next, with "Withdraw the report" until a
// reviewer decides. Reopening the same passage for the same answer shows the report's state, a reviewer's
// decision and reason included. The server decides whether the row shows (feedback.allowed); in a preview it
// shows with both buttons disabled and says why. Escape closes the open form before the drawer, and keeps its text.
import { useEffect, useId, useRef, useState, type KeyboardEvent, type ReactNode, type RefObject } from "react";
import { copy } from "../copy";
import { formatDate } from "../lib/format";
import { useStore } from "../lib/store";
import {
  loadReport,
  reportKey,
  reports as reportsStore,
  sendReport,
  withdrawReport,
  type Feedback,
  type MyReport,
  type ReportKind,
} from "../lib/retrieval";
import { ApiError } from "../lib/api";
import { Button } from "./Button";
import { ReasonField } from "./DecisionForm";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { fillText } from "./LessonParts";
import { OutcomePanel } from "./LessonReview";
import { ToggleButton } from "./ToggleButton";

const words = copy.feedback;
const KINDS: ReportKind[] = ["wrong_passage", "not_useful"];
const REASON_MAX = 500;

// What you typed, kept for the session when you cancel, by passage and answer.
const typed = new Map<string, { kind: ReportKind; text: string }>();

export type RowStart = {
  // A gallery sample's or a test's state: the form open with a kind and text, sending, failed, a report, or
  // withdrawing.
  chosen?: ReportKind;
  text?: string;
  sending?: boolean;
  failed?: boolean;
  report?: MyReport | null;
  fresh?: boolean;
  withdrawing?: boolean;
  withdrawFailed?: "failed" | "decided";
};

export function FeedbackRow({
  evidenceId,
  feedback,
  sentence,
  preview,
  start,
}: {
  evidenceId: string;
  feedback: Feedback;
  // The answer's sentence the drawer was opened from, if any.
  sentence: number | null;
  preview: boolean;
  start?: RowStart;
}) {
  const runId = feedback.run_id ?? "";
  const key = reportKey(evidenceId, runId);
  const held = useStore(reportsStore);
  const disabled = preview || !feedback.allowed;
  const headingId = useId();
  const formId = useId();
  const previewId = useId();
  const kept = typed.get(key);
  const [chosen, setChosen] = useState<ReportKind | null>(start?.chosen ?? null);
  const [text, setText] = useState(start?.text ?? kept?.text ?? "");
  const [sending, setSending] = useState(start?.sending ?? false);
  const [failed, setFailed] = useState(start?.failed ?? false);
  const [fresh, setFresh] = useState(start?.fresh ?? false);
  const [withdrawing, setWithdrawing] = useState(start?.withdrawing ?? false);
  const [withdrawFailed, setWithdrawFailed] = useState<"failed" | "decided" | null>(start?.withdrawFailed ?? null);
  const [announced, setAnnounced] = useState("");
  const buttons = useRef<Record<string, HTMLButtonElement | null>>({});
  const reason = useRef<HTMLTextAreaElement>(null);
  const panel = useRef<HTMLDivElement>(null);
  const report: MyReport | null = start && "report" in start ? (start.report ?? null) : (held[key] ?? feedback.my_report ?? null);

  // Reopening a passage you reported on for this answer reads your report again, so a reviewer's decision shows.
  // A fresh answer carries no report (the stream's feedback.my_report), so opening it asks for nothing.
  useEffect(() => {
    if (start || disabled || !runId || !reportsStore.get()[key]) return;
    void loadReport(evidenceId, runId);
  }, [key]);

  // Choosing a kind puts focus in the reason field (brief 23's rule).
  useEffect(() => {
    if (chosen && !start) reason.current?.focus();
  }, [chosen === null]);

  function choose(kind: ReportKind) {
    if (disabled) return;
    setChosen(kind);
    setFailed(false);
    typed.set(key, { kind, text });
  }

  function close() {
    const was = chosen;
    if (was) typed.set(key, { kind: was, text });
    setChosen(null);
    setFailed(false);
    requestAnimationFrame(() => was && buttons.current[was]?.focus());
  }

  async function send() {
    if (!chosen || sending) return;
    setSending(true);
    setFailed(false);
    try {
      await sendReport({ evidence_id: evidenceId, run_id: runId, sentence_id: sentence, kind: chosen, reason: text.trim() || null });
      typed.delete(key);
      setFresh(true);
      setChosen(null);
      setText("");
      requestAnimationFrame(() => panel.current?.focus());
    } catch {
      setFailed(true);
    } finally {
      setSending(false);
    }
  }

  async function withdraw() {
    if (!report || withdrawing) return;
    const kind = report.kind;
    setWithdrawing(true);
    setWithdrawFailed(null);
    try {
      await withdrawReport(evidenceId, runId, report.report_id);
      setFresh(false);
      setAnnounced(words.withdrawn);
      requestAnimationFrame(() => buttons.current[kind]?.focus());
    } catch (error) {
      setWithdrawFailed(error instanceof ApiError && error.status === 409 ? "decided" : "failed");
    } finally {
      setWithdrawing(false);
    }
  }

  // Escape closes the form and keeps its text, before the drawer's own Escape closes the drawer.
  const onFormKey = (event: KeyboardEvent) => {
    if (event.key !== "Escape") return;
    event.preventDefault();
    close();
  };

  return (
    <section aria-labelledby={headingId} data-feedback-row={report ? report.status : chosen ? "form" : "idle"} className="mt-2 border-t border-line pt-4">
      <h3 id={headingId} className="text-small font-bold text-ink-heading">
        {words.question}
      </h3>
      {report ? (
        <div className="mt-2">
          <Outcome
            report={report}
            fresh={fresh}
            mode={feedback.mode}
            panelRef={panel}
            withdrawing={withdrawing}
            withdrawFailed={withdrawFailed}
            onWithdraw={() => void withdraw()}
          />
        </div>
      ) : (
        <>
          <div className="mt-2 flex flex-wrap gap-2" onKeyDown={chosen ? onFormKey : undefined}>
            {/* The first label starts on the heading's edge, as a flush ghost button's does. */}
            {KINDS.map((kind, index) => (
              <ToggleButton
                key={kind}
                inText
                className={index === 0 ? "-ml-4" : undefined}
                ref={(element) => {
                  buttons.current[kind] = element;
                }}
                pressed={chosen === kind}
                disabled={disabled}
                aria-controls={chosen ? formId : undefined}
                aria-describedby={disabled ? previewId : undefined}
                onClick={() => choose(kind)}
                data-report-kind={kind}
              >
                {words.kind[kind]}
              </ToggleButton>
            ))}
          </div>
          {disabled && (
            <p id={previewId} className="mt-2 text-caption text-ink-muted">
              {words.preview}
            </p>
          )}
          {chosen && !disabled && (
            <form
              id={formId}
              noValidate
              aria-busy={sending || undefined}
              onSubmit={(event) => event.preventDefault()}
              onKeyDown={onFormKey}
              className="mt-3 flex flex-col gap-3"
              style={{ scrollPaddingBottom: "4rem" }}
            >
              <ReasonFieldNearest>
                <ReasonField
                  ref={reason}
                  label={words.formLabel[chosen]}
                  helper={words.formHelper}
                  value={text}
                  onChange={(value) => {
                    setText(value);
                    typed.set(key, { kind: chosen, text: value });
                  }}
                  max={REASON_MAX}
                  disabled={sending}
                />
              </ReasonFieldNearest>
              {failed && (
                <p role="alert" className="text-small text-error">
                  {words.failed}
                </p>
              )}
              <div className="flex flex-wrap gap-3">
                <Button variant="secondary" loading={sending} busyLabel={words.sending} onClick={() => void send()} data-send-report>
                  {failed ? words.tryAgain : words.send}
                </Button>
                <Button variant="ghost" onClick={close} disabled={sending}>
                  {words.cancel}
                </Button>
              </div>
            </form>
          )}
        </>
      )}
      <p role="status" className="clip-visually">
        {announced}
      </p>
    </section>
  );
}

// On a phone, the on-screen keyboard covers the bottom of the sheet: the field scrolls into view when it takes focus.
function ReasonFieldNearest({ children }: { children: ReactNode }) {
  return (
    <div onFocus={(event) => event.target instanceof HTMLTextAreaElement && event.target.scrollIntoView({ block: "nearest" })}>
      {children}
    </div>
  );
}

function Outcome({
  report,
  fresh,
  mode,
  panelRef,
  withdrawing,
  withdrawFailed,
  onWithdraw,
}: {
  report: MyReport;
  fresh: boolean;
  mode: "pilot" | "scale";
  panelRef: RefObject<HTMLDivElement | null>;
  withdrawing: boolean;
  withdrawFailed: "failed" | "decided" | null;
  onWithdraw: () => void;
}) {
  const kind = copy.retrieval.queryKinds[report.query_kind] ?? copy.retrieval.queryKinds.other;
  const reported = formatDate(report.reported_on);
  const decided = report.decided_on ? formatDate(report.decided_on) : "";
  const lead = fresh ? words.sent[report.kind] : fillText(words.later[report.kind], { reported });
  const reviewer = report.reviewer_reason ? <p className="mt-1 text-small">{fillText(words.reviewerReason, { reason: report.reviewer_reason })}</p> : null;
  if (report.status === "ranked_lower" || report.status === "ranked_lower_by_agreement") {
    const body =
      report.status === "ranked_lower"
        ? fillText(words.rankedLower, { decided, kind })
        : <Fill template={words.byAgreement} slots={{ decided, kind, agreeing: <Num count={report.agreeing_count ?? 0} /> }} />;
    return (
      <OutcomePanel ref={panelRef} state="success" lead={lead} body={body}>
        {reviewer}
      </OutcomePanel>
    );
  }
  if (report.status === "kept") {
    return (
      <OutcomePanel ref={panelRef} state="neutral" lead={lead} body={fillText(words.kept, { decided })}>
        {reviewer}
      </OutcomePanel>
    );
  }
  return (
    <OutcomePanel ref={panelRef} state="info" lead={lead} body={mode === "scale" ? words.nextScale : words.nextPilot}>
      {report.reason && <p className="mt-1 text-small">{fillText(words.yourReason, { reason: report.reason })}</p>}
      {withdrawFailed && (
        <p role="alert" className="mt-2 text-small text-error">
          {withdrawFailed === "decided" ? words.withdrawDecided : words.withdrawFailed}
        </p>
      )}
      {withdrawFailed !== "decided" && (
        <div className="mt-3">
          <Button variant="ghost" flush onPage loading={withdrawing} busyLabel={words.withdrawing} onClick={onWithdraw} data-withdraw-report>
            {withdrawFailed === "failed" ? words.tryAgain : words.withdraw}
          </Button>
        </div>
      )}
    </OutcomePanel>
  );
}
