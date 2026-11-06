// A project's Summary tab (the 21 brief, section 3): what the project is and where it stands, from
// precomputed records, before any model call. One request, GET /api/projects/{pid}/summary, gives every
// value with its source and each source as the evidence drawer shows it, so a citation marker opens at
// once. The lead sentence is a template filled with the route's values and is the page's finding (ticket 99): it
// opens the Summary in the finding style, and a caption says no model wrote it. Four
// fact tables follow (Dates, with the closing date history under it; Money; Ratings; Sectors and implementing
// agencies), each value with its source cell and citation marker. Markers are numbered in reading order, and a source
// cited again keeps its number, like a footnote.
//
// The page counts and sums nothing: the number of closing-date moves and each amount are the route's. The Summary
// takes the page's 12 columns, and its tables sit two side by side where it is at least 75rem wide and in one column
// below; the evidence drawer narrows the page, so it puts them in one column and never moves the page's left edge.
//
// States: loading (the group titles and table heads are real, with skeleton rows as many as P130164's),
// populated, a value missing from its record, a source not loaded for this project (the closing date
// history), no ratings yet, a project before the Environmental and Social Framework, pipeline or
// dropped, a service that didn't answer, and an account that can't read Prism's tables.
import { useEffect, type ReactNode } from "react";
import { CitationMarker } from "../../components/CitationMarker";
import { EightColumns } from "../../components/EightColumns";
import { EvidenceCard } from "../../components/EvidenceCard";
import { FactTable, type FactRow } from "../../components/FactTable";
import { Fill } from "../../components/Fill";
import { LoadError } from "../../components/LoadError";
import { InfoWindow, MadeBy } from "../../components/MadeBy";
import { Num } from "../../components/Num";
import { SkeletonLine, SkeletonText } from "../../components/Skeleton";
import { Source } from "../../components/Source";
import { Table, type Column, type Row } from "../../components/Table";
import { DefinitionWindow } from "../../components/Term";
import { copy } from "../../copy";
import type { EvidenceEvent } from "../../lib/answer";
import type { Fact, FactSource, Summary } from "../../lib/api";
import { evidenceHref, openEvidence, remember } from "../../lib/evidence";
import { formatDate } from "../../lib/format";
import { useLoad } from "../../lib/load";
import { address } from "../../lib/router";
import { useStore } from "../../lib/store";
import { withReadParams } from "../../lib/view";
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
  if (summary.history.source) cite(summary.history.source);
  // An amount summed over several loans or credits cites each one, in the order the route lists them.
  summary.money.forEach((fact) => (fact.loan_ids && fact.loan_ids.length > 1 ? fact.loan_ids.forEach((id) => cite({ ...fact.source, evidence_id: id })) : cite(fact.source)));
  summary.ratings.forEach((fact) => cite(fact.source));
  summary.who.forEach((fact) => cite(fact.source));
  return numbers;
}

// The words of a source cell, and the name its marker reads: "Projects API, Aug 1, 2023".
// The cell's date is one unbroken run, "Sep 30, 2026" or "Nov 2022", so it never splits across two lines (ticket 59).
function sourceWords(source: FactSource): { cell: ReactNode; name: string } {
  const date = source.date ?? "";
  const sequence = source.sequence != null ? String(source.sequence) : null;
  const kind = source.kind === "isr" && !sequence ? "isrUnnumbered" : source.kind;
  const shortDate = source.kind === "loan_history" ? month(date) : table(date);
  return {
    cell: <Fill template={words.source[kind]} slots={{ date: date ? <span className="whitespace-nowrap">{shortDate}</span> : "", sequence: sequence ?? "" }} />,
    name: fill(words.markerSource[kind], { date: date ? formatDate(date) : "", sequence: sequence ?? "" }),
  };
}

// A source cell: its words, then one marker for each record it cites. An amount summed over several loans
// or credits cites each one, so a reader can open the credit that holds most of it too (the 21 critique,
// round 3), and each marker's name says which credit it opens.
function SourceCell({ source, numbers, events, loans = [] }: { source: FactSource; numbers: Map<string, number>; events: Record<string, EvidenceEvent>; loans?: { id: string; loan: string }[] }) {
  const { cell, name } = sourceWords(source);
  const cited =
    loans.length > 1
      ? loans.map(({ id, loan }) => ({ id, name: fill(words.markerSource.loan, { loan, date: source.date ? formatDate(source.date) : "" }) }))
      : source.evidence_id
        ? [{ id: source.evidence_id, name }]
        : [];
  return (
    <span>
      {cell}
      {cited.map(({ id, name: markerName }) => {
        const n = numbers.get(id);
        const event = events[id];
        return (
          n !== undefined && (
            <CitationMarker
              key={id}
              n={n}
              source={markerName}
              href={evidenceHref(id)}
              evidenceId={id}
              preview={event ? <EvidenceCard evidence={event} n={n} sentence={null} /> : undefined}
              onOpen={(marker) => openEvidence(id, { serial: null, sentence: null, marker, runId: null })}
            />
          )
        );
      })}
    </span>
  );
}

// The loans and credits an amount sums, each with the record that cites it, in the route's order.
function citedLoans(fact: Fact): { id: string; loan: string }[] {
  const ids = fact.loan_ids ?? [];
  return (fact.loans ?? []).flatMap((loan, index) => (ids[index] ? [{ id: ids[index], loan: loan.loan_number }] : []));
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
  const canceled = lead.any_canceled;
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
  // The page's finding (DESIGN.md section 1, principle 7; ticket 99), in the finding style, about 45 characters a line in
  // balanced lines. It is built from the records alone, with no model, so it carries no byline (ticket 111 kept the
  // project page's records free of one). How I built it, with its as-of date, is in the made-by window at its end
  // (ticket 126), no longer a caption under it.
  return (
    <p className="max-w-[22.5em] text-finding text-balance text-ink-heading" data-summary-lead data-finding>
      {text}
      <MadeBy name={words.madeByName}>
        <Fill template={words.madeBy} slots={{ as_of_date: <Num date={summary.as_of} /> }} />
      </MadeBy>
    </p>
  );
}

const LABELS = words.label;

// note: a sentence about a row, such as why a category stands in for a risk rating, which its label's window holds
// (ticket 126): the label already says what the row shows.
function factRows(facts: Fact[], numbers: Map<string, number>, events: Record<string, EvidenceEvent>, value: (fact: Fact) => ReactNode, note?: (fact: Fact) => ReactNode): FactRow[] {
  return facts.map((fact) => {
    const label = LABELS[fact.key] ?? fact.key;
    const said = note?.(fact);
    return {
      key: fact.key,
      label: said ? (
        <DefinitionWindow openOnHover label={label} title={label} inText={false}>
          {said}
        </DefinitionWindow>
      ) : (
        label
      ),
      value: value(fact),
      source: <SourceCell source={fact.source} numbers={numbers} events={events} loans={citedLoans(fact)} />,
    };
  });
}

// A list of values, one per line with 4 px between them, such as the sectors with their shares, so a name
// that wraps stays apart from the next.
function Lines({ values }: { values: string[] }) {
  if (values.length === 0) return missing;
  return (
    <ul className="flex flex-col gap-1">
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
  // The Source spans both of a card's columns, so its date keeps to one line in a 390 px card (ticket 59).
  { key: "source", header: words.history.col.source },
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
        {summary.history.source && (
          <Source className="mt-1">
            <SourceCell source={summary.history.source} numbers={numbers} events={events} />
          </Source>
        )}
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

// The skeleton's rows: as many as a populated P130164 summary has in each table (approval and closing dates;
// commitment, disbursed and canceled; seven ratings; region, sector, sectors and agency).
const LOADING_ROWS = { dates: 2, money: 3, ratings: 7, who: 4 };

const head = (key: keyof typeof words.col) => words.col[key];

// The fact tables (ticket 99): one column, and two side by side where the Summary is at least 75rem wide (Dates beside
// Money, Ratings beside Sectors and implementing agencies), with the layout grid's 32 px gutter between them. The
// Summary is a size container of its own, so the evidence drawer, which narrows it, puts them back in one column.
const TABLES = "mt-8 grid grid-cols-1 gap-12 @xl/summary:grid-cols-2 @xl/summary:gap-x-8";

// While the summary loads: four bars for the finding and one for the caption, then the four groups' real
// titles and table heads over skeleton rows as many as P130164's, so nothing moves when the facts arrive.
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
      <div aria-hidden="true" className="max-w-[22.5em] text-finding">
        <SkeletonText className="text-finding" widths={["w-full", "w-full", "w-full", "w-2/5"]} />
      </div>
      <p role="status" className="sr-only">
        {words.loading}
      </p>
      <div className={TABLES}>
        <div>
          {group("dates", "date")}
          {/* The closing date history's title and its one sentence with its source, as P130164 has. */}
          <div className="mt-4" aria-hidden="true">
            <h4 className="text-small font-bold text-ink-heading">{words.history.title}</h4>
            <SkeletonLine className="mt-1 text-body" width="w-3/5" />
            <SkeletonLine className="mt-1 text-caption" width="w-2/5" />
          </div>
        </div>
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
      <div className={TABLES}>
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
          <div>
            <FactTable
              // The route says when the loans data reports more disbursed and canceled than committed. Only a reader
              // who adds the three amounts asks why, so the answer is in an info window on the title (ticket 126).
              title={
                data.lead.amounts_exceed_commitment ? (
                  <>
                    {words.group.money}
                    <InfoWindow name={words.money.exceedsName} kind="money-note">
                      {words.money.exceeds}
                    </InfoWindow>
                  </>
                ) : (
                  words.group.money
                )
              }
              caption={words.caption.money(name)}
              labelHeader={head("label")}
              valueHeader={head("money")}
              sourceHeader={head("source")}
              numeric
              rows={factRows(data.money, numbers, events, (fact) => <Money fact={fact} />)}
            />
          </div>
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
            <h3 className="text-h2 text-ink-heading">{words.group.ratings}</h3>
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
  const search = useStore(address).search;
  const [load, retry] = useLoad<Summary>(withReadParams(`/api/projects/${encodeURIComponent(pid)}/summary`, search));
  const data = load.status === "ready" ? load.data : null;

  // Each source the summary cites is known to the evidence drawer at once, so a marker opens it with no request.
  useEffect(() => {
    if (data) for (const event of data.sources) remember(event);
  }, [data]);

  return (
    // The Summary takes the page's 12 columns (the wide layout) and is a size container of its own, by which its fact
    // tables lay out (TABLES above).
    <div className="@container/summary" data-summary={load.status}>
      <h2 className="sr-only">{words.heading}</h2>
      {load.status === "error" ? (
        <EightColumns>
          <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
        </EightColumns>
      ) : data ? (
        <SummaryFacts summary={data} />
      ) : (
        <SummarySkeleton />
      )}
    </div>
  );
}
