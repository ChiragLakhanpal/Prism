// Baseline line (DESIGN.md section 5; the 21 brief, section 5.2): a Task zone row after Check a plan's activities, "Baseline
// for delay" (ticket 100; it sat under the method sentence before), that saves one version of an agency's plans as the baseline, the
// plan agreed at negotiations. The baseline is shared: every World Bank staff viewer who checks that
// agency's plans sees the same one, and who saved it. Later checks then also measure delay from its dates;
// the marks still come from the first published planned date.
//
// Its consequence is written before its button (feedforward). Saving and removing can be undone, so they
// ask nothing; replacing a baseline someone else saved asks in place, naming whose plan it replaces and for
// whom. Status messages replace the text in the same panel, in a role="status" element that takes focus,
// so each is read once and nothing below moves. Undo stays until you leave or act again.
//
// The server refuses a save outside the World Bank staff view, and this panel offers none there: the
// implementing agency view reads the baseline without its saver, the public view never shows the panel,
// and a past date shows the baseline only if it was saved by then, with no controls.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import { ApiError, deleteJson, putJson, type Baseline, type CheckPlanResult } from "../lib/api";
import { formatDate } from "../lib/format";
import { useStore } from "../lib/store";
import { allows, appliedView } from "../lib/view";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { TaskZone, ZoneBlock } from "./TaskZone";
import { TextLink } from "./TextLink";

const words = copy.baseline;
const short = (iso: string) => formatDate(iso, { style: "table" });

// How the baseline shows in the view the server applied, from the roles file's [views] (ticket 40): not at all without
// the baseline capability (the public view), read-only without the saver's name where the view lacks the saver or
// saving (the implementing agency view and its preview), and in full with its controls for World Bank staff.
export function useBaselineView(): "staff" | "piu" | "public" {
  const shown = useStore(appliedView);
  if (!allows("baseline", shown)) return "public";
  return allows("baseline_saver", shown) && allows("save_baseline", shown) ? "staff" : "piu";
}

type Action = "save" | "remove" | "replace" | "undo";
type Mode =
  | { kind: "idle" }
  | { kind: "confirm" }
  | { kind: "busy"; action: Action }
  | { kind: "done"; message: ReactNode; undo: () => Promise<void> }
  | { kind: "undone"; message: ReactNode }
  | { kind: "failed"; again: () => void }
  | { kind: "permission" };

export function BaselinePanel({
  pid,
  agencyId,
  agency,
  planDate,
  baseline,
  view,
  readOnly = false,
  refresh,
}: {
  pid: string;
  agencyId: string;
  agency: string;
  planDate: string;
  baseline: Baseline | null;
  view: "staff" | "piu" | "public";
  // A check as of a past date shows the baseline it had then, with no controls.
  readOnly?: boolean;
  // Reads the plan check again after a write, so the reasons give the new delays in the same render as the
  // message that says what changed.
  refresh: () => Promise<CheckPlanResult>;
}) {
  const [mode, setMode] = useState<Mode>({ kind: "idle" });
  const status = useRef<HTMLParagraphElement>(null);
  const make = useRef<HTMLButtonElement>(null);
  const confirmText = useRef<HTMLParagraphElement>(null);
  const focusAfter = useRef<"status" | "make" | "confirm" | null>(null);

  useEffect(() => {
    const target = focusAfter.current;
    focusAfter.current = null;
    if (target === "status") status.current?.focus();
    if (target === "make") make.current?.focus();
    if (target === "confirm") confirmText.current?.focus();
  }, [mode]);

  if (view === "public") return null;
  if (readOnly && !baseline) return null;
  const address = `/api/projects/${encodeURIComponent(pid)}/procurement/${encodeURIComponent(agencyId)}/baseline`;
  const save = (date: string) => putJson<{ baseline: Baseline | null }>(address, { plan_date: date });
  const remove = () => deleteJson<{ baseline: null }>(address);

  // Runs one write, reads the check again, then shows the message. A failure says why, and the check is read
  // again anyway, so the panel's sentence says what the baseline is now (the server writes in an order that a
  // failure part way leaves safe).
  const run = (action: Action, write: () => Promise<unknown>, after: () => Mode) => {
    const attempt = async () => {
      setMode({ kind: "busy", action });
      try {
        await write();
        await refresh();
        focusAfter.current = "status";
        setMode(after());
      } catch (error) {
        await refresh().catch(() => undefined);
        focusAfter.current = "status";
        setMode(error instanceof ApiError && error.status === 403 ? { kind: "permission" } : { kind: "failed", again: attempt });
      }
    };
    void attempt();
  };
  const date = (iso: string) => <Num date={iso} />;
  const undone = (to: string | null): Mode => ({
    kind: "undone",
    message: to ? <Fill template={words.undone} slots={{ date: date(to) }} /> : words.undoneNone,
  });
  const undoTo = (to: string | null) => async () =>
    run("undo", () => (to ? save(to) : remove()), () => undone(to));

  const isThis = baseline?.plan_date === planDate;
  const savedOn = baseline ? date(baseline.saved_on) : null;

  // The panel's sentence for the baseline as it stands.
  let text: ReactNode;
  if (view === "piu") {
    text = baseline ? <Fill template={words.piuSet} slots={{ baseline_date: date(baseline.plan_date), saved_date: savedOn }} /> : words.piuNone;
  } else if (!baseline) {
    text = words.none;
  } else if (isThis) {
    text = <Fill template={words.thisPlan} slots={{ saved_by: baseline.saved_by ?? "", saved_date: savedOn }} />;
  } else {
    text = <Fill template={words.another} slots={{ baseline_date: date(baseline.plan_date), saved_by: baseline.saved_by ?? "", saved_date: savedOn }} />;
  }

  const busy = mode.kind === "busy" ? mode.action : null;
  let message: ReactNode = text;
  let controls: ReactNode = null;
  const staff = view === "staff" && !readOnly;
  if (mode.kind === "done") {
    message = mode.message;
    controls = (
      <Button variant="ghost" flush onClick={() => void mode.undo()}>
        {words.undo}
      </Button>
    );
  } else if (mode.kind === "confirm" && baseline) {
    message = text;
  } else if (mode.kind === "undone") {
    message = mode.message;
  }
  if (staff && (mode.kind === "idle" || mode.kind === "undone" || mode.kind === "busy" || mode.kind === "failed")) {
    if (!baseline) {
      controls = (
        <Button
          variant="secondary"
          loading={busy === "save" || busy === "undo"}
          busyLabel={words.saving}
          onClick={() => run("save", () => save(planDate), () => ({ kind: "done", message: <Fill template={words.justSaved} slots={{ plan_date: date(planDate) }} />, undo: undoTo(null) }))}
        >
          {words.save}
        </Button>
      );
    } else if (isThis) {
      controls = (
        <Button
          variant="ghost"
          flush
          loading={busy === "remove" || busy === "undo"}
          busyLabel={words.removing}
          onClick={() => run("remove", remove, () => ({ kind: "done", message: words.justRemoved, undo: undoTo(planDate) }))}
        >
          {words.remove}
        </Button>
      );
    } else {
      controls = (
        <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
          <TextLink href={`/projects/${pid}/procurement/${agencyId}/${baseline.plan_date}`} className="text-small">
            <Fill template={words.anotherLink} slots={{ date: short(baseline.plan_date) }} />
          </TextLink>
          <Button
            ref={make}
            variant="secondary"
            loading={busy === "replace" || busy === "undo"}
            busyLabel={words.replacing}
            onClick={() => {
              focusAfter.current = "confirm";
              setMode({ kind: "confirm" });
            }}
          >
            {words.make}
          </Button>
        </div>
      );
    }
  }

  return (
    <TaskZone name={words.label} sectionKey="baseline" marks={{ "data-baseline": mode.kind === "idle" ? (baseline ? (isThis ? "this" : "another") : "none") : mode.kind }}>
      <ZoneBlock>
      <p ref={status} role="status" tabIndex={-1} className="text-body text-ink focus:outline-none">
        {message}
      </p>
      {mode.kind === "failed" && (
        <div className="mt-3">
          <Alert
            state="error"
            live="alert"
            action={
              <Button variant="secondary" onClick={mode.again}>
                {words.tryAgain}
              </Button>
            }
          >
            {words.failed}
          </Alert>
        </div>
      )}
      {mode.kind === "permission" && (
        <div className="mt-3">
          <Alert state="error" live="alert">
            {words.permission}
          </Alert>
        </div>
      )}
      {mode.kind === "confirm" && baseline && (
        <div
          className="mt-3 flex flex-col gap-3"
          onKeyDown={(event) => {
            if (event.key !== "Escape") return;
            event.stopPropagation();
            focusAfter.current = "make";
            setMode({ kind: "idle" });
          }}
        >
          <p ref={confirmText} tabIndex={-1} className="text-body font-semibold text-ink focus:outline-none" data-baseline-confirm>
            <Fill template={words.confirm} slots={{ baseline_date: date(baseline.plan_date), agency }} />
          </p>
          {/* Below 768 px the two buttons stack and the ghost one sits flush, its label on the text's edge
              (DESIGN.md section 5, Buttons); side by side from 768 px it keeps its padding. */}
          <div className="flex flex-col items-start gap-3 @md/page:flex-row @md/page:flex-wrap @md/page:items-center">
            <Button
              variant="secondary"
              onClick={() => {
                const old = baseline.plan_date;
                run("replace", () => save(planDate), () => ({
                  kind: "done",
                  message: <Fill template={words.justReplaced} slots={{ plan_date: date(planDate), old_date: date(old) }} />,
                  undo: undoTo(old),
                }));
              }}
            >
              {words.replace}
            </Button>
            <Button
              variant="ghost"
              flush
              className="@md/page:ml-0 @md/page:border-x @md/page:px-6"
              onClick={() => {
                focusAfter.current = "make";
                setMode({ kind: "idle" });
              }}
            >
              <Fill template={words.keep} slots={{ date: short(baseline.plan_date) }} />
            </Button>
          </div>
        </div>
      )}
      {controls && mode.kind !== "confirm" && <div className="mt-3">{controls}</div>}
      </ZoneBlock>
    </TaskZone>
  );
}
