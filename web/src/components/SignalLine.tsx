// Signal line (DESIGN.md section 5; the 37 brief, section 4.3): one copy-file sentence per check, filled with
// project_signals' values, in small ink. STEP references are plain mono text, not links. Num marks only derived
// values (a ratio, a count of moves or activities, a percentage, months left) and a rounded amount, whose popover
// shows the record's exact Estimated Amount. One citation marker ends the line and opens the record behind it in
// the evidence drawer; a strong signal then carries the Tag "Strong signal". A check that fired on several
// activities is one line with a count.
import type { ReactNode } from "react";
import { copy } from "../copy";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { formatDate, formatNumber } from "../lib/format";
import type { Signal } from "../lib/following";
import { CitationMarker } from "./CitationMarker";
import { EvidenceCard } from "./EvidenceCard";
import { Fill } from "./Fill";
import { Tag } from "./LessonParts";
import { Num } from "./Num";
import { IdText } from "./ProjectId";
import type { EvidenceEvent } from "../lib/answer";

const words = copy.signals;
const ref = (id: string) => <IdText id={id} />;
const day = (iso: string) => formatDate(iso);
const money = (value: string) => formatNumber(Number(value), { decimals: 2, compact: false });

function lines(items: ReactNode[]): ReactNode {
  return (
    <ul className="mt-1">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

function tooltip(lead: string, items: ReactNode[]): ReactNode {
  return (
    <div>
      <p className="font-semibold">{lead}</p>
      {lines(items)}
    </div>
  );
}

// The sentence of one signal, without its marker.
function sentence(signal: Signal): ReactNode {
  const items = signal.items;
  const first = items[0] ?? {};
  const many = signal.count > 1;
  const count = (lead: string, listed: ReactNode[]) => <Num count={signal.count} check={{ tooltip: tooltip(lead, listed) }} />;
  switch (signal.check) {
    case "completion_passed":
      return many ? (
        <Fill template={words.line.completion_passed.many} slots={{
          n: count(words.num.activities, items.map((item) => words.num.activity(item.activity_reference_no, day(item.planned_completion_on)))),
        }} />
      ) : (
        <Fill template={words.line.completion_passed.one} slots={{ ref: ref(first.activity_reference_no), date: day(first.planned_completion_on) }} />
      );
    case "above_estimate":
      return many ? (
        <Fill template={words.line.above_estimate.many} slots={{
          n: count(words.num.contracts, items.map((item) => words.num.contract(item.activity_reference_no, item.ratio_exact))),
          min: String(signal.values.ratio_min),
          max: String(signal.values.ratio_max),
        }} />
      ) : (
        <Fill template={words.line.above_estimate.one} slots={{
          ref: ref(first.activity_reference_no),
          ratio: <Num written={String(first.ratio)} check={{ tooltip: words.num.ratio(money(first.actual_amount_usd), money(first.estimated_amount_usd), first.ratio_exact) }} />,
        }} />
      );
    case "late_direct":
      return many ? (
        <Fill template={words.line.late_direct.many} slots={{
          n: count(words.num.direct, items.map((item) => words.num.directItem(item.activity_reference_no, money(item.estimated_amount_usd), day(item.first_plan_date)))),
          amount: String(signal.values.total_millions),
        }} />
      ) : (
        <Fill template={words.line.late_direct.one} slots={{
          ref: ref(first.activity_reference_no),
          amount: <Num written={first.amount_millions} check={{ tooltip: words.num.amount(money(first.estimated_amount_usd)) }} />,
          category: words.category[first.section] ?? words.categoryOther,
          date: day(first.first_plan_date),
        }} />
      );
    case "closing_moves": {
      const moves = items.map((item) => words.num.move(formatDate(item.reported_on, { style: "month" }), day(item.previous_closing_date), day(item.closing_date)));
      const n = <Num count={signal.count} check={{ tooltip: tooltip(words.num.moves, moves) }} />;
      return <Fill template={many ? words.line.closing_moves.many : words.line.closing_moves.one} slots={{ n, year: String(signal.values.since_year) }} />;
    }
    case "restructured": {
      const listed = items.map((item) => words.num.restructuring(String(item.level), day(item.restructured_on)));
      return many ? (
        <Fill template={words.line.restructured.many} slots={{
          n: count(words.num.restructurings, listed), year: String(signal.values.since_year), date: day(signal.values.latest_on),
        }} />
      ) : (
        <Fill template={words.line.restructured.one} slots={{ date: day(first.restructured_on) }} />
      );
    }
    case "isr_lowered":
      return (
        <>
          {items.map((item, index) => (
            <span key={item.evidence_id}>
              {index > 0 && " "}
              <Fill template={item.rating_key === "pdo" ? words.line.isr_lowered.pdo : words.line.isr_lowered.implementation} slots={{
                date: day(item.isr_date), to: item.current_rating, from: item.previous_rating,
              }} />
            </span>
          ))}
        </>
      );
    case "disbursement": {
      const values = signal.values;
      return (
        <Fill template={words.line.disbursement.one} slots={{
          date: day(values.as_of_date),
          pct: <Num written={String(values.percent)} check={{ tooltip: words.num.percent(values.disbursed_millions, values.available_millions, values.percent_exact) }} />,
          months: <Num count={values.months_left} />,
        }} />
      );
    }
  }
}

// The marker's name: the record it opens and its date.
export function signalSourceName(signal: Signal): string {
  const template = words.source[signal.source.source_key] ?? words.source.plans;
  return template.replace("{date}", signal.source.date ? formatDate(signal.source.date) : "");
}

export function SignalLine({ signal, n, event, opened }: { signal: Signal; n: number | undefined; event?: EvidenceEvent; opened: boolean }) {
  const id = signal.items[0]?.evidence_id;
  return (
    <li data-signal={signal.check} className="max-w-[72ch] text-small text-ink">
      {sentence(signal)}
      {id && n !== undefined && (
        <CitationMarker
          n={n}
          source={signalSourceName(signal)}
          href={evidenceHref(id)}
          evidenceId={id}
          opened={opened}
          preview={event ? <EvidenceCard evidence={event} n={n} sentence={null} /> : undefined}
          onOpen={(marker) => openEvidence(id, { serial: null, sentence: null, marker, runId: null })}
        />
      )}
      {signal.strong && (
        <span className="ml-2 inline-block">
          <Tag>{copy.following.strongTag}</Tag>
        </span>
      )}
    </li>
  );
}
