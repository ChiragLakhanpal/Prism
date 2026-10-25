// The lesson review's own parts (DESIGN.md section 5; the 29 brief, sections 3.2, 5.4, 5.9, 5.12 and 5.13):
//
// - QueueRow: one item waiting for review, modelled on the Following row. Status first, the statement as an
//   h3 link, the source sentence with the P-code as a ProjectId link, badges only for the evidence and an
//   exception, the clock with its day as a Num whose tooltip says how it was counted, then who acts next or
//   why you can't.
// - statusOf, clockOf and sourceOf: the same status, clock and source lines on the review page.
// - HistoryList: a dated ol in the past tense, reasons in straight quotes, Was and Now lines under a change.
// - OutcomePanel: an Alert with a lead sentence in 600, one more sentence and up to two links, which takes
//   the decision form's place after a save and shows a decided item's result on its record.
import { forwardRef, Fragment, useId, type ReactNode } from "react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { itemHref, type Clock, type HistoryEvent, type Item, type QueueRow as Row } from "../lib/lessons";
import { Fill } from "./Fill";
import { EvidenceBadge, fillText } from "./LessonParts";
import { ProjectId } from "./ProjectId";
import { Num } from "./Num";
import { STATES, type State } from "./state";
import { StatusBadge } from "./StatusBadge";
import { TextLink } from "./TextLink";

const words = copy.lessons;

// "New lesson · needs your decision", or "· needs a decision" when someone else acts next.
export function statusOf(row: Pick<Row, "kind" | "stage" | "group">): string {
  const kind = words.kinds[row.kind];
  if (row.stage === "decided") return fillText(words.row.statusDecided, { kind });
  const forms = row.group === "you" ? words.row.statusYou : words.row.statusOthers;
  return fillText(forms[row.stage], { kind });
}

export function ClockLine({ clock }: { clock: Clock }) {
  const r = words.row;
  const due = <Num date={clock.due_on} />;
  if (clock.overdue_days > 0) {
    return clock.overdue_days === 1 ? (
      <Fill template={r.clockOverdueOne} slots={{ due }} />
    ) : (
      <Fill template={r.clockOverdue} slots={{ due, days: <Num value={clock.overdue_days} options={{ compact: false }} /> }} />
    );
  }
  if (clock.day === null || clock.limit_days === null) return <Fill template={r.clockCrossCheck} slots={{ due }} />;
  const tooltip = <Fill template={r.clockTooltip} slots={{ start: <Num date={clock.start_on} /> }} />;
  if (clock.last_day) return <Fill template={r.clockLastDay} slots={{ limit: <Num value={clock.limit_days} check={{ tooltip }} /> }} />;
  return (
    <Fill
      template={r.clock}
      slots={{ day: <Num value={clock.day} check={{ tooltip }} />, limit: <Num value={clock.limit_days} />, due }}
    />
  );
}

// "From the ICR for Rajasthan Road Sector Modernization Project (P130164), paragraph 54, page 23. South Asia."
export function SourceSentence({ row }: { row: Row }) {
  const r = words.row;
  if (row.kind === "cross_check" && row.decided) {
    return <Fill template={r.sourceCrossCheck} slots={{ region: row.decided.region, date: row.decided.on ? <Num date={row.decided.on} /> : "" }} />;
  }
  const source = row.source;
  if (!source) return null;
  const template = source.doc_short === "ICR Review" ? r.sourceIcrReview : source.doc_short === "PPAR" ? r.sourcePpar : r.sourceIcr;
  return (
    <Fill
      template={template}
      slots={{
        name: row.project.name ?? source.project_name ?? "",
        pid: <ProjectId pid={row.project.pid} />,
        para: source.locator.text,
        section: source.locator.text,
        page: String(source.page),
        region: row.region,
      }}
    />
  );
}

// Who acts next, or why the viewer can't: one line, or two for a re-check waiting for a decision.
export function NextLines({ row }: { row: Row }) {
  const r = words.row;
  const lines: ReactNode[] = [];
  const values = { name: row.project.name ?? "", pid: <ProjectId pid={row.project.pid} />, region: row.can.values.region ?? row.can.values.decided_region ?? row.region };
  if (row.origin && row.kind === "recheck") {
    const origin = row.origin;
    const date = <Num date={origin.on} />;
    lines.push(
      origin.kind === "cross_check" ? (
        <Fill template={r.nextCrossCheck} slots={{ name: origin.name ?? "", region: origin.region ?? "", date }} />
      ) : origin.kind === "edition" ? (
        <Fill template={r.nextEdition} slots={{ date, edition: origin.reason ?? "" }} />
      ) : (
        <Fill template={r.nextAsked} slots={{ name: origin.name ?? "", date }} />
      ),
    );
  }
  if (row.stage === "decision" && row.recommendation) {
    const phrase = r.phrases[row.recommendation.phrase] ?? row.recommendation.phrase;
    lines.push(<Fill template={r.nextDecide} slots={{ name: row.recommendation.name, phrase, date: <Num date={row.recommendation.on} /> }} />);
  } else if (row.stage === "recommendation" && row.group === "others" && !row.can.reason_code) {
    lines.push(r.nextRecommend);
  }
  const code = row.can.reason_code;
  if (row.group === "others" && code && code in r.whyNot) lines.push(<Fill template={r.whyNot[code]} slots={values} />);
  return (
    <>
      {lines.map((line, index) => (
        <p key={index} className="text-small text-ink">
          {line}
        </p>
      ))}
    </>
  );
}

export function QueueRow({ row }: { row: Row }) {
  const overdue = (row.clock?.overdue_days ?? 0) > 0;
  return (
    <li data-queue-row={row.item_id} className="flex flex-col gap-1 border-t-2 border-line py-4">
      <p className="text-small font-semibold text-ink-heading">{statusOf(row)}</p>
      <h3 className="text-title text-balance">
        <TextLink href={itemHref(row.item_id)}>{row.statement}</TextLink>
      </h3>
      <p className="text-caption text-ink-muted">
        <SourceSentence row={row} />
      </p>
      {(row.kind !== "cross_check" || overdue || row.may_repeat) && (
        <div className="flex flex-wrap gap-2 py-1">
          <EvidenceBadge status={row.ieg_status} />
          {row.may_repeat && <StatusBadge kind="may-repeat" />}
          {overdue && <StatusBadge kind="overdue" />}
        </div>
      )}
      {row.clock && (
        <p className="text-small text-ink">
          <ClockLine clock={row.clock} />
        </p>
      )}
      <NextLines row={row} />
    </li>
  );
}

// ── History ──────────────────────────────────────────────────────────────

const ROLE: Record<string, string> = {
  "accredited procurement specialist": words.review.roles.accredited,
  "lead procurement specialist": words.review.roles.lead,
};

function valueText(field: string, value: unknown, lists: { risk_factors: Item[]; stages: Item[]; kinds: Item[] }): string {
  const label = (items: Item[], key: unknown) => items.find((item) => item.key === key)?.label ?? String(key ?? "");
  if (field === "statement") return fillText(words.card.quote, { quote: String(value ?? "") });
  if (field === "risk_factors") return (Array.isArray(value) ? value : []).map((key) => label(lists.risk_factors, key)).join(copy.list.comma);
  if (field === "stage") return label(lists.stages, value);
  if (field === "kind") return label(lists.kinds, value);
  return String(value ?? "");
}

function Changes({ event, lists }: { event: HistoryEvent; lists: { risk_factors: Item[]; stages: Item[]; kinds: Item[] } }) {
  const changes = event.changes ?? [];
  const h = words.review.history;
  if (changes.length === 0) return null;
  // A merge's was and now count the quotes and reports the lesson rests on.
  const merge = changes.every((change) => change.field === "quotes" || change.field === "reports");
  if (merge) {
    const get = (key: "was" | "now", field: string) => Number(changes.find((change) => change.field === field)?.[key] ?? 0);
    // "one quote from one report", "two quotes from two reports": each count with its own noun's form.
    const counted = (key: "was" | "now") => ({
      quotes: <Fill template={get(key, "quotes") === 1 ? h.quotes.one : h.quotes.many} slots={{ count: <Num count={get(key, "quotes")} /> }} />,
      reports: <Fill template={get(key, "reports") === 1 ? h.reports.one : h.reports.many} slots={{ count: <Num count={get(key, "reports")} /> }} />,
    });
    return (
      <>
        <p className="text-caption text-ink-muted">
          <Fill template={h.was} slots={{ value: <Fill template={h.merged} slots={counted("was")} /> }} />
        </p>
        <p className="text-caption text-ink-muted">
          <Fill template={h.now} slots={{ value: <Fill template={h.mergedNow} slots={counted("now")} /> }} />
        </p>
      </>
    );
  }
  return (
    <>
      {changes.map((change) => (
        <Fragment key={change.field}>
          <p className="text-caption text-ink-muted">{fillText(h.was, { value: valueText(change.field, change.was, lists) })}</p>
          <p className="text-caption text-ink-muted">{fillText(h.now, { value: valueText(change.field, change.now, lists) })}</p>
        </Fragment>
      ))}
    </>
  );
}

function eventSentence(event: HistoryEvent): ReactNode {
  const h = words.review.history;
  const name = event.name ?? "";
  const role = ROLE[event.role ?? ""] ?? event.role ?? "";
  switch (event.event) {
    case "proposed":
      return (
        <Fill
          template={h.proposed}
          slots={{ doc: event.doc_short ?? "", name: event.project_name ?? "", pid: <ProjectId pid={event.pid ?? ""} />, date: event.published_on ? <Num date={event.published_on} /> : "" }}
        />
      );
    case "restatement":
      return <Fill template={h.restatement} slots={{ date: event.review_date ? <Num date={event.review_date} /> : "" }} />;
    case "recheck_asked":
      return fillText(h.asked, { name });
    case "recheck_edition":
      return fillText(h.edition, { edition: event.reason ?? "" });
    case "recheck_cross_check":
      return fillText(h.crossCheckStarted, { name });
    case "recommended":
      return event.outcome === "change"
        ? fillText(h.recommendedChange, { name, role })
        : fillText(h.recommended, { name, role, phrase: words.row.phrases[event.outcome ?? ""] ?? "" });
    case "decided": {
      const phrase = h.decisions[event.outcome ?? ""] ?? "";
      return (
        <Fill
          template={h.decided}
          slots={{ name, phrase: <Fill template={phrase} slots={{ target: event.target ?? "", version: event.version ? <Num value={event.version} /> : "" }} /> }}
        />
      );
    }
    case "cross_checked":
      return fillText(event.outcome === "agree" ? h.agreed : h.disagreed, { name, region: event.region ?? "" });
    default:
      return null;
  }
}

export function HistoryList({ events, lists, headingId }: { events: HistoryEvent[]; lists: { risk_factors: Item[]; stages: Item[]; kinds: Item[] }; headingId: string }) {
  const h = words.review.history;
  return (
    <ol aria-labelledby={headingId} data-history className="flex flex-col gap-3">
      {events.map((event, index) => {
        const withReason = event.reason && !["recheck_edition"].includes(event.event);
        const wordingChanged = event.event === "decided" && event.outcome === "add" && (event.changes ?? []).length > 0;
        return (
          <li key={index} className="flex flex-col gap-1 text-small text-ink @md/page:flex-row @md/page:gap-4">
            <time dateTime={event.on ?? undefined} className="shrink-0 font-semibold tabular-nums @md/page:w-30">
              {event.on ? <Num date={event.on} style="table" /> : null}
            </time>
            <div className="min-w-0 flex-1">
              <p>
                {eventSentence(event)}
                {withReason && (
                  <>
                    {" "}
                    {fillText(h.reason, { reason: event.reason ?? "" })}
                  </>
                )}
              </p>
              {wordingChanged && <p className="mt-1">{fillText(h.wordingChanged, { name: event.name ?? "" })}</p>}
              <Changes event={event} lists={lists} />
            </div>
          </li>
        );
      })}
    </ol>
  );
}

// ── The outcome panel ────────────────────────────────────────────────────

export const OutcomePanel = forwardRef<HTMLDivElement, { state: State; lead: ReactNode; body: ReactNode; links?: { href: string; text: ReactNode }[] }>(
  function OutcomePanel({ state, lead, body, links = [] }, ref) {
    const look = STATES[state];
    const id = useId();
    return (
      <div
        ref={ref}
        tabIndex={-1}
        role="region"
        aria-labelledby={id}
        data-outcome-panel={state}
        className={cx("flex animate-fade-in gap-3 rounded-r-md border-l-4 px-4 py-4 outline-none motion-reduce:animate-none", look.box, look.border)}
      >
        <look.Icon aria-hidden="true" className={cx("mt-0.5 size-5 shrink-0", look.icon)} />
        <div className="min-w-0 flex-1">
          <p id={id} className={cx("text-body font-semibold", look.text)}>
            {lead}
          </p>
          <p className={cx("mt-1 text-body", look.text)}>{body}</p>
          {links.length > 0 && (
            <p className="mt-3 flex flex-wrap gap-x-6 gap-y-2 text-body">
              {links.map((link) => (
                <TextLink key={link.href} href={link.href}>
                  {link.text}
                </TextLink>
              ))}
            </p>
          )}
        </div>
      </div>
    );
  },
);
