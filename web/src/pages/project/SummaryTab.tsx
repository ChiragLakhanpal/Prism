// A project's Summary tab (the 21 brief, section 3): what the project is and where it stands, from
// precomputed records, before any model call. One request, GET /api/projects/{pid}/summary, gives every
// value with its source and each source as the evidence drawer shows it, so a citation marker opens at
// once. The lead sentence is a template filled with the route's values, and a caption says no model wrote
// it. Four fact tables follow (Dates, with the closing date history under it; Money; Ratings; Sectors and
// implementing agencies), each value with its source cell and citation marker. Markers are numbered in
// reading order, and a source cited again keeps its number, like a footnote.
//
// The page counts and sums nothing: the number of closing-date moves and each amount are the route's. It
// takes up columns 1 to 7 from a page area of 1200 px, so the evidence drawer opens into the space beside
// it and the column never moves.
//
// States: loading (the group titles and table heads are real, with skeleton rows as many as P130164's),
// populated, a value missing from its record, a source not loaded for this project (the closing date
// history), no ratings yet, a project before the Environmental and Social Framework, pipeline or
// dropped, a service that didn't answer, and an account that can't read Strata's tables.
import { useEffect, type ReactNode } from "react";
import { CitationMarker } from "../../components/CitationMarker";
import { EvidenceCard } from "../../components/EvidenceCard";
import { FactTable, type FactRow } from "../../components/FactTable";
import { Fill } from "../../components/Fill";
import { LoadError } from "../../components/LoadError";
import { Num } from "../../components/Num";
import { SkeletonLine } from "../../components/Skeleton";
import { Table, type Column, type Row } from "../../components/Table";
import { copy } from "../../copy";
import type { EvidenceEvent } from "../../lib/answer";
import type { Fact, FactSource, Summary } from "../../lib/api";
import { evidenceHref, openEvidence, remember } from "../../lib/evidence";
import { formatDate } from "../../lib/format";
import { useLoad } from "../../lib/load";
import { fill } from "../../routes";

const words = copy.summary;
const table = (iso: string) => formatDate(iso, { style: "table" });

// The month a loan history row reports: "Dec 2018".
function month(iso: string): string {
  return formatDate(iso, { style: "table" }).replace(/ \d+,/, "");
}

const missing = <span className="text-ink-muted">{words.notInRecord}</span>;

// Each source's number, in the order the page reads them, so a source cited again keeps its number.
function numberSources(summary: Summary): Map<string, number> {
  const numbers = new Map<string, number>();
  const cite = (source: FactSource) => {
    if (source.evidence_id && !numbers.has(source.evidence_id)) numbers.set(source.evidence_id, numbers.size + 1);
  };
  summary.dates.forEach((fact) => cite(fact.source));
  summary.history.rows.forEach((row) => cite(row.source));
  summary.money.forEach((fact) => cite(fact.source));
  summary.ratings.forEach((fact) => cite(fact.source));
  summary.who.forEach((fact) => cite(fact.source));
  return numbers;
}

// The words of a source cell, and the name its marker reads: "Projects API, Aug 1, 2023".
function sourceWords(source: FactSource): { cell: string; name: string } {
  const date = source.date ?? "";
  const sequence = source.sequence != null ? String(source.sequence) : null;
  const kind = source.kind === "isr" && !sequence ? "isrUnnumbered" : source.kind;
  const shortDate = source.kind === "loan_history" ? month(date) : table(date);
  return {
    cell: fill(words.source[kind], { date: date ? shortDate : "", sequence: sequence ?? "" }),
    name: fill(words.markerSource[kind], { date: date ? formatDate(date) : "", sequence: sequence ?? "" }),
  };
}

function SourceCell({ source, numbers, events }: { source: FactSource; numbers: Map<string, number>; events: Record<string, EvidenceEvent> }) {
  const { cell, name } = sourceWords(source);
  const id = source.evidence_id;
  const n = id ? numbers.get(id) : undefined;
  const event = id ? events[id] : undefined;
  return (
    <span>
      {cell}
      {id && n !== undefined && (
        <CitationMarker
          n={n}
          source={name}
          href={evidenceHref(id)}
          evidenceId={id}
          preview={event ? <EvidenceCard evidence={event} n={n} sentence={null} /> : undefined}
          onOpen={(marker) => openEvidence(id, { serial: null, sentence: null, marker, runId: null })}
        />
      )}
    </span>
  );
}

// A money value: the route's amount, and when the project has several loans or credits, a tooltip that
// lists each one and the total the route summed.
function Money({ fact }: { fact: Fact }) {
  if (fact.value === null) return missing;
  if (!fact.loans || fact.loans.length < 2) return <span className="tabular-nums">{fact.value}</span>;
  return (
    <Num
      written={fact.value}
      check={{
        tooltip: (
          <ul className="flex flex-col gap-1" data-numbers>
            {fact.loans.map((loan) => (
              <li key={loan.loan_number}>
                <Fill template={words.loanLine} slots={{ loan: <span className="font-mono">{loan.loan_number}</span>, amount: loan.value }} />
              </li>
            ))}
            <li className="font-semibold">
              <Fill template={words.loanTotal} slots={{ amount: fact.value }} />
            </li>
          </ul>
        ),
      }}
    />
  );
}

function Lead({ summary }: { summary: Summary }) {
  const lead = summary.lead;
  const closing = lead.closing_date ? <Num date={lead.closing_date} /> : missing;
  const moves =
    lead.moves === null ? null : lead.moves === 0 ? (
      words.closingMoves.none
    ) : lead.moves === 1 ? (
      words.closingMoves.one
    ) : (
      <Fill
        template={words.closingMoves.many}
        slots={{ n: <Num count={lead.moves} check={{ tooltip: words.movesExplain }} /> }}
      />
    );
  const slots: Record<string, ReactNode> = {
    closing_date: closing,
    closing_moves: moves ?? "",
    commitment: lead.commitment ?? "",
    disbursed: lead.disbursed ?? "",
    canceled: lead.canceled ?? "",
    disbursed_as_of: lead.disbursed_as_of ? <Num date={lead.disbursed_as_of} /> : "",
  };
  const money = lead.commitment !== null && lead.disbursed !== null;
  const canceled = lead.canceled !== null && Number(lead.canceled) > 0;
  let text: ReactNode;
  if (lead.kind === "pipeline") text = words.lead.pipeline;
  else if (lead.kind === "dropped") text = words.lead.dropped;
  else if (lead.kind === "closed") {
    text = <Fill template={!money ? words.lead.closedNoMoney : canceled ? words.lead.closed : words.lead.closedNoCancel} slots={slots} />;
  } else {
    text = (
      <>
        <Fill template={money ? words.lead.active : words.lead.activeNoMoney} slots={slots} />
        {money && canceled && (
          <>
            {" "}
            <Fill template={words.lead.activeCancel} slots={slots} />
          </>
        )}
      </>
    );
  }
  return (
    <p className="max-w-[65ch] text-h3 text-ink-heading" data-summary-lead>
      {text}
    </p>
  );
}

const LABELS = words.label;

function factRows(facts: Fact[], numbers: Map<string, number>, events: Record<string, EvidenceEvent>, value: (fact: Fact) => ReactNode, note?: (fact: Fact) => ReactNode): FactRow[] {
  return facts.map((fact) => ({
    key: fact.key,
    label: LABELS[fact.key] ?? fact.key,
    value: value(fact),
    note: note?.(fact),
    source: <SourceCell source={fact.source} numbers={numbers} events={events} />,
  }));
}

// A list of values, one per line, such as the sectors with their shares.
function Lines({ values }: { values: string[] }) {
  if (values.length === 0) return missing;
  return (
    <ul className="flex flex-col">
      {values.map((line) => (
        <li key={line}>{line}</li>
      ))}
    </ul>
  );
}

const historyColumns: Column[] = [
  { key: "first", header: words.history.col.first, short: true },
  { key: "before", header: words.history.col.before, short: true },
  { key: "after", header: words.history.col.after, short: true },
  { key: "source", header: words.history.col.source, short: true },
];

function History({ summary, numbers, events }: { summary: Summary; numbers: Map<string, number>; events: Record<string, EvidenceEvent> }) {
  const title = <h4 className="text-small font-bold text-ink-heading">{words.history.title}</h4>;
  if (!summary.history.known) {
    return (
      <div className="mt-4" data-closing-history="unknown">
        {title}
        <p className="mt-1 max-w-prose text-caption text-ink-muted">{words.history.unknown}</p>
      </div>
    );
  }
  if (summary.history.rows.length === 0) {
    return (
      <div className="mt-4" data-closing-history="none">
        {title}
        <p className="mt-1 max-w-prose text-body text-ink">{words.history.none}</p>
      </div>
    );
  }
  const rows: Row[] = summary.history.rows.map((row) => ({
    id: row.first_recorded,
    cells: {
      first: month(row.first_recorded),
      before: <Num date={row.before} style="table" />,
      after: <Num date={row.after} style="table" />,
      source: <SourceCell source={row.source} numbers={numbers} events={events} />,
    },
  }));
  return (
    <div className="mt-4" data-closing-history="rows">
      <Table title={words.history.title} level={4} columns={historyColumns} rowHeader="first" state={{ status: "ready", rows }} />
    </div>
  );
}

// The skeleton's rows: as many as a populated P130164 summary has in each table.
const LOADING_ROWS = { dates: 3, money: 3, ratings: 4, who: 3 };

const head = (key: keyof typeof words.col) => words.col[key];

// While the summary loads: two bars for the lead and one for the caption, then the four groups' real titles
// and table heads over skeleton rows as many as P130164's, so nothing moves when the facts arrive.
export function SummarySkeleton() {
  const group = (key: keyof typeof LOADING_ROWS, value: keyof typeof words.col, numeric = false) => (
    <FactTable
      title={words.group[key]}
      caption={words.group[key]}
      labelHeader={head("label")}
      valueHeader={head(value)}
      sourceHeader={head("source")}
      rows={[]}
      numeric={numeric}
      loadingRows={LOADING_ROWS[key]}
    />
  );
  return (
    <>
      <div aria-hidden="true">
        <SkeletonLine className="text-h3" width="w-[65ch] max-w-full" />
        <SkeletonLine className="text-h3" width="w-[45ch] max-w-[70%]" />
        <SkeletonLine className="mt-2 text-caption" width="w-1/2" />
      </div>
      <p role="status" className="sr-only">
        {words.loading}
      </p>
      <div className="mt-8 flex flex-col gap-12">
        {group("dates", "date")}
        {group("money", "money", true)}
        {group("ratings", "rating")}
        {group("who", "detail")}
      </div>
    </>
  );
}

// The populated summary: the lead, its caption and the four fact tables.
export function SummaryFacts({ summary }: { summary: Summary }) {
  const data = summary;
  const name = data.project.display_name ?? data.project.project_name;
  const numbers = numberSources(data);
  const events = Object.fromEntries(data.sources.map((event) => [event.id, event]));
  const date = (fact: Fact) => (fact.value ? <Num date={fact.value} style="table" /> : missing);
  const text = (fact: Fact) => fact.value ?? missing;
  const who = data.who.flatMap((fact) => {
    if (fact.key === "sectors") {
      return [
        { ...fact, key: "sector" },
        { ...fact, key: "sectors", value: null, values: fact.values ?? [] },
      ];
    }
    if (fact.key === "agencies") return [{ ...fact, key: (fact.values ?? []).length > 1 ? "agencies" : "agency" }];
    return [fact];
  });
  const whoValue = (fact: Fact) => (fact.key === "sectors" || fact.key === "agencies" || fact.key === "agency" ? <Lines values={fact.values ?? []} /> : text(fact));
  return (
    <>
      <Lead summary={data} />
      <p className="mt-2 text-caption text-ink-muted" data-made-by>
        <Fill template={words.madeBy} slots={{ as_of_date: <Num date={data.as_of} /> }} />
      </p>
      <div className="mt-8 flex flex-col gap-12">
        <div>
          <FactTable
            title={words.group.dates}
            caption={words.caption.dates(name)}
            labelHeader={head("label")}
            valueHeader={head("date")}
            sourceHeader={head("source")}
            rows={factRows(data.dates, numbers, events, date)}
          />
          <History summary={data} numbers={numbers} events={events} />
        </div>
        {data.money.length > 0 && (
          <FactTable
            title={words.group.money}
            caption={words.caption.money(name)}
            labelHeader={head("label")}
            valueHeader={head("money")}
            sourceHeader={head("source")}
            numeric
            rows={factRows(data.money, numbers, events, (fact) => <Money fact={fact} />)}
          />
        )}
        {data.ratings.length > 0 ? (
          <FactTable
            title={words.group.ratings}
            caption={words.caption.ratings(name)}
            labelHeader={head("label")}
            valueHeader={head("rating")}
            sourceHeader={head("source")}
            rows={factRows(data.ratings, numbers, events, text, (fact) => (fact.key === "ea_category" ? words.eaNote : null))}
          />
        ) : (
          <section>
            <h3 className="text-title text-ink-heading">{words.group.ratings}</h3>
            <p className="mt-2 max-w-prose text-body text-ink">{words.noRatings}</p>
          </section>
        )}
        <FactTable
          title={words.group.who}
          caption={words.caption.who(name)}
          labelHeader={head("label")}
          valueHeader={head("detail")}
          sourceHeader={head("source")}
          rows={factRows(who, numbers, events, whoValue)}
        />
      </div>
    </>
  );
}

export function SummaryTab({ pid }: { pid: string }) {
  const [load, retry] = useLoad<Summary>(`/api/projects/${encodeURIComponent(pid)}/summary`);
  const data = load.status === "ready" ? load.data : null;

  // Each source the summary cites is known to the evidence drawer at once, so a marker opens it with no request.
  useEffect(() => {
    if (data) for (const event of data.sources) remember(event);
  }, [data]);

  return (
    <div className="layout-grid" data-summary={load.status}>
      <div className="col-span-12 @xl/page:col-span-7">
        <h2 className="sr-only">{words.heading}</h2>
        {load.status === "error" ? (
          <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        ) : data ? (
          <SummaryFacts summary={data} />
        ) : (
          <SummarySkeleton />
        )}
      </div>
    </div>
  );
}
