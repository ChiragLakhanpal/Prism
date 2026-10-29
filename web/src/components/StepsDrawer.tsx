// The evidence drawer's two lists for section 2 (ticket 27; the 27 brief, section 7.6), in brief 14's frame: the
// comparable packages behind one step's planned date, and the packages behind "ran longest". Each entry is a
// 44 px button with its STEP reference in mono that opens the package's records (brief 15's comparable view, with
// "Back to the {n} packages" above its title). Both middle and cautious figures show, whichever choice is selected,
// so the list reads the same from either column. The section holds the lists, so opening one records nothing.
import { useEffect, useRef, type ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { cx } from "../lib/cx";
import type { DotEntry } from "../lib/packages";
import type { LongestListRow, StepComparable, StepListRow } from "../lib/steps";
import { familyStep, stepFamily } from "../steps";
import { Fill, Joined } from "./Fill";
import { Num } from "./Num";
import { Source } from "./Source";

const words = copy.stepDates.drawer;
const number = (value: number) => <Num value={value} options={{ compact: false }} />;
// About how many in 10 ran later, as the tool counted them; five in 10 is "about half", as the section says it.
const about = (in10: number | null) =>
  in10 === 5 ? copy.stepDates.aboutHalf : <Fill template={copy.stepDates.aboutIn10} slots={{ in10: number(in10 ?? 0) }} />;

// One comparable's days at the step: on the delay basis against its own first planned date (late, on it, or early;
// a still-open one whose date had not come yet is not due), on the duration basis since the step before.
function entryDays(entry: StepComparable, basis: "delay" | "duration"): ReactNode {
  const { days } = entry;
  if (entry.still_open) return days < 0 ? words.entryNotDue : <Fill template={words.entryOpen} slots={{ days: number(days) }} />;
  if (days < 0) return <Fill template={days === -1 ? words.entryBeforeOne : words.entryBefore} slots={{ days: number(-days) }} />;
  if (basis === "duration") return <Fill template={days === 1 ? words.entryDay : words.entryDays} slots={{ days: number(days) }} />;
  if (days === 0) return words.entryOnPlan;
  return <Fill template={days === 1 ? words.entryLateOne : words.entryLate} slots={{ days: number(days) }} />;
}

// The drawer's heading for a list.
export function stepListTitle(evidence: EvidenceEvent): string {
  if (evidence.kind === "steps-longest") return words.longestTitle;
  const row = evidence.row as StepListRow;
  const step = familyStep(stepFamily(row.family), row.step.step_key);
  return words.title(step?.phrase ?? row.step.step_key);
}

// The comparable view an entry opens is find_comparables' package record, as a quantile dot's entries open it.
const asEntry = (reference: string, evidenceId: string): DotEntry => ({ step_reference: reference, evidence_id: evidenceId, months: 0, still_open: false });

function Entry({ reference, evidenceId, focus, onOpen, children }: { reference: string; evidenceId: string; focus: boolean; onOpen?: (entry: DotEntry) => void; children: ReactNode }) {
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    if (focus) ref.current?.focus();
  }, [focus]);
  return (
    <li>
      <button
        ref={ref}
        type="button"
        data-step-entry={reference}
        // The list lands on the package you came back from, marked with tint (ticket 105).
        data-landed={focus ? "" : undefined}
        onClick={() => onOpen?.(asEntry(reference, evidenceId))}
        className={cx(
          "flex min-h-11 w-full cursor-pointer flex-wrap items-baseline justify-between gap-x-4 px-2 py-2 text-left",
          focus ? "bg-tint" : "hover:bg-tint-hover",
        )}
      >
        {/* Its name says what it opens, then its words on screen, so the name holds them (WCAG 2.5.3). */}
        <span className="min-w-0 font-mono text-small wrap-anywhere text-primary underline decoration-1 underline-offset-3">
          <span className="sr-only">{words.entryOpens} </span>
          {reference}
        </span>
        {/* ml-auto keeps the days on the right edge when a long reference pushes them onto a line of their own. */}
        <span className="ml-auto text-small text-ink-muted tabular-nums">{children}</span>
      </button>
    </li>
  );
}

export function StepComparablesView({ evidence, focusEntry = null, onOpen }: { evidence: EvidenceEvent; focusEntry?: string | null; onOpen?: (entry: DotEntry) => void }) {
  const row = evidence.row as StepListRow;
  const family = stepFamily(row.family);
  const step = familyStep(family, row.step.step_key);
  const previous = row.previous_key ? familyStep(family, row.previous_key) : null;
  const n = row.step.comparables_n ?? 0;
  const { middle, cautious } = row.step;
  const phrase = step?.phrase ?? "";
  // The date the row beside it names: the page's as-of date when there is one, else the records' own date.
  const date = row.as_of ?? row.records_through;
  let finding;
  if (row.step.abstain_reason === "not_reached" && date) {
    // Most comparable packages had not reached the step, so they never "recorded" it (ticket 58).
    const reached = row.step.reached_n ?? 0;
    finding = (
      <Fill
        template={reached === 0 ? words.findingNotReachedNone : words.findingNotReached}
        slots={{ reached: number(reached), n: number(n), step: phrase, date: <Num date={date} /> }}
      />
    );
  } else if (!row.abstain_all && middle?.days != null && cautious?.days != null && (cautious.longer ?? 0) === 0 && row.step.abstain_reason !== "few_comparables") {
    // None ran later than the cautious days, so no "0 of 25, about 0 in 10" (ticket 58).
    finding = (
      <>
        <Fill
          template={row.basis === "delay" ? words.findingNoneLaterDelay : words.findingNoneLater}
          slots={{ n: number(n), step: phrase, days_c: number(cautious.days), previous: previous?.phrase ?? "" }}
        />
        {(middle.longer ?? 0) > 0 && (
          <>
            {" "}
            <Fill
              template={row.basis === "delay" ? words.findingMiddleDelay : words.findingMiddle}
              slots={{ longer_m: number(middle.longer ?? 0), about_m: about(middle.in10), days_m: number(middle.days), n: number(n), previous: previous?.phrase ?? "" }}
            />
          </>
        )}
      </>
    );
  } else if (!row.abstain_all && middle?.days != null && cautious?.days != null && row.step.abstain_reason !== "few_comparables") {
    finding = (
      <Fill
        template={row.basis === "delay" ? words.findingDelay : words.findingDuration}
        slots={{
          longer_c: number(cautious.longer ?? 0), about_c: about(cautious.in10), days_c: number(cautious.days),
          longer_m: number(middle.longer ?? 0), about_m: about(middle.in10), days_m: number(middle.days),
          n: number(n), step: phrase, previous: previous?.phrase ?? "",
        }}
      />
    );
  } else if (n < row.min_comparables) {
    finding = n === 1 ? <Fill template={words.findingAbstainOne} slots={{ step: phrase }} /> : <Fill template={words.findingAbstain} slots={{ step: phrase, n: <Num count={n} /> }} />;
  } else {
    finding = <Fill template={words.findingCounts} slots={{ step: phrase, n: number(n) }} />;
  }
  return (
    <div data-step-list={row.step.step_key} className="flex flex-col gap-4">
      {step && <p className="text-caption text-ink-muted">{words.fullName(step.step_name)}</p>}
      <p className="text-body text-ink">{finding}</p>
      {date && (
        <p className="text-caption text-ink-muted">
          <Fill template={row.basis === "delay" ? words.noteDelay : words.note} slots={{ date: <Num date={date} /> }} />
        </p>
      )}
      <ul className="flex flex-col divide-y divide-line border-y border-line">
        {row.step.comparables.map((entry) => (
          <Entry key={entry.step_reference} reference={entry.step_reference} evidenceId={entry.evidence_id} focus={entry.step_reference === focusEntry} onOpen={onOpen}>
            {entryDays(entry, row.basis)}
          </Entry>
        ))}
      </ul>
      <ListSource names={row.sources} through={row.records_through} asOf={row.as_of} />
    </div>
  );
}

export function LongestView({ evidence, focusEntry = null, onOpen }: { evidence: EvidenceEvent; focusEntry?: string | null; onOpen?: (entry: DotEntry) => void }) {
  const row = evidence.row as LongestListRow;
  const family = stepFamily(row.family);
  const stage = familyStep(family, row.longest.step_key)?.stage ?? "";
  return (
    <div data-longest-list className="flex flex-col gap-4">
      <p className="text-body text-ink">
        <Fill template={words.longestFinding} slots={{ stage, n: number(row.longest.n), m: number(row.longest.m) }} />
      </p>
      <p className="text-caption text-ink-muted">{words.longestNote}</p>
      <ul className="flex flex-col divide-y divide-line border-y border-line">
        {row.longest.entries.map((entry) => (
          <Entry key={entry.step_reference} reference={entry.step_reference} evidenceId={entry.evidence_id} focus={entry.step_reference === focusEntry} onOpen={onOpen}>
            <Fill template={words.longestEntry} slots={{ stage: familyStep(family, entry.stage_step_key)?.stage ?? "", days: number(entry.days) }} />
          </Entry>
        ))}
      </ul>
      <ListSource names={row.sources} through={row.records_through} asOf={row.as_of} />
    </div>
  );
}

// On a page as of a date the line reads "Records as of {asOf}", as the section's line does; otherwise it gives the
// date the tool's records run through. It never calls the page's date the records' own (the 58 review, round 2, B1).
function ListSource({ names, through, asOf }: { names: string[]; through: string | null; asOf: string | null }) {
  const date = asOf ?? through;
  return (
    <Source>
      <Fill template={asOf ? copy.stepDates.sourceLineAsOf : copy.stepDates.sourceLine} slots={{ names: <Joined items={names} />, date: date ? <Num date={date} /> : "" }} />
    </Source>
  );
}
