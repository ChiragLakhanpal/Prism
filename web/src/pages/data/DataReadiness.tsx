// Data readiness (the 16 design brief, sections 3 to 6): a headline sentence built from the measures,
// then "What you can ask", then one row per source, then the fixes ranked by what they would
// unlock. Every number comes from data_readiness_for (GET /api/data/readiness) and is shown as the
// tool returned it. Opened from a coverage line (?sources=&from=), it shows only the sources behind
// that answer, with "Show all sources".
//
// States: loading (static skeletons at once, and after three seconds one polite line), ready,
// filtered, empty (no measures yet), abstention (a source with no measures, or a date before the
// first measure) and error (a timeout, no access, or anything else). In an error the tables are
// hidden, so old numbers never pass for current ones.
import { useEffect, useRef, useState, type ReactNode, type RefObject } from "react";
import { Alert } from "../../components/Alert";
import { Button } from "../../components/Button";
import { DefinitionWindow } from "../../components/Term";
import { Num } from "../../components/Num";
import { ReadinessTable, type ReadinessColumn, type ReadinessRow } from "../../components/ReadinessTable";
import { SkeletonText } from "../../components/Skeleton";
import { StatusBadge } from "../../components/StatusBadge";
import { Template } from "../../components/Template";
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import {
  COLUMNS,
  readReadiness,
  readRegistry,
  registry,
  type Cell,
  type Column,
  type Fix,
  type Kind,
  type Readiness,
  type ReadinessState,
  type SourceRow,
} from "../../lib/dataPages";
import { useStore } from "../../lib/store";
import { DATA_HREF } from "../../routes";
import { MeasureValue, Sentence, type Measures } from "./measures";

const words = copy.dataReadiness;
const SLOW_MS = 3000;
// Until the registry answers, the skeleton holds this many rows in each table.
const ROWS_BEFORE_REGISTRY = 3;

const plain = (count: number) => <Num count={count} />;
const day = (iso: string, today: string, style: "sentence" | "table" = "sentence") => <Num date={iso} style={style} today={today} />;

// ── Cells ────────────────────────────────────────────────────────────────

function Stack({ children }: { children: ReactNode }) {
  return <div className="flex flex-col items-start gap-1">{children}</div>;
}

function Qualifier({ children }: { children: ReactNode }) {
  return <span className="text-caption text-ink-muted">{children}</span>;
}

function Badge({ status }: { status?: "partial" | "gap" | null }) {
  return status ? <StatusBadge kind={status} /> : null;
}

function measureCell(cell: Cell, column: Column, measures: Measures): ReactNode {
  if (cell.published_as_table) return <span className="text-ink-muted">{words.sources.publishedAsTable}</span>;
  if (cell.row === null || cell.row === undefined) return <span className="text-ink-muted">{words.sources.notMeasured}</span>;
  const row = measures.rows[cell.row];
  const noun = cell.noun ?? null;
  if (column === "fresh") {
    const schedule = words.server.schedules[cell.schedule as keyof typeof words.server.schedules] ?? cell.schedule ?? "";
    const style = cell.schedule === "frozen" ? "month" : "short";
    return (
      <Stack>
        <span className="font-semibold">
          <Template
            text={words.sources.fresh}
            values={{
              date: row.as_of ? (
                <MeasureValue measures={measures} index={cell.row} value={{ date: row.as_of, style, today: measures.asOf }} noun={noun} shown="day" column="fresh" />
              ) : (
                words.sources.notMeasured
              ),
              schedule,
            }}
          />
        </span>
        {cell.late_days ? (
          <Qualifier>
            <Template
              text={cell.late_days === 1 ? words.sources.lateOne : words.sources.late}
              values={{ days: <MeasureValue measures={measures} index={cell.row} value={{ count: cell.late_days }} noun={noun} shown="day" column="fresh" /> }}
            />
          </Qualifier>
        ) : null}
        <Badge status={cell.status} />
      </Stack>
    );
  }
  const years = cell.years_row !== null && cell.years_row !== undefined ? measures.rows[cell.years_row] : null;
  return (
    <Stack>
      <span className="font-semibold">
        {column === "coverage" || row.denominator === null ? (
          <MeasureValue measures={measures} index={cell.row} value={{ value: row.count ?? 0, options: { compact: false } }} noun={noun} shown="ratio" column={column} />
        ) : (
          <MeasureValue measures={measures} index={cell.row} value={{ part: row.count ?? 0, whole: row.denominator, style: "table" }} noun={noun} shown="ratio" column={column} />
        )}
      </span>
      <Qualifier>{cell.note ?? cell.counts}</Qualifier>
      {years && years.count !== null && years.denominator !== null && cell.years_row !== null && cell.years_row !== undefined && (
        <Qualifier>
          <Template
            text={years.count !== years.denominator ? words.sources.yearsOf : years.count === 1 ? words.sources.yearsOne : words.sources.years}
            values={{
              count: <MeasureValue measures={measures} index={cell.years_row} value={{ count: years.count }} noun={null} column="coverage" />,
              total: <MeasureValue measures={measures} index={cell.years_row} value={{ count: years.denominator }} noun={null} column="coverage" />,
            }}
          />
        </Qualifier>
      )}
      <Badge status={cell.status} />
    </Stack>
  );
}

function scopeText(row: Extract<SourceRow, { type: "measured" | "unmeasured" }>): ReactNode {
  const scope = row.scope;
  const where =
    scope.kind === "every_country" ? (
      words.sources.scope.every_country
    ) : scope.kind === "countries" ? (
      scope.names.length > 1
        ? scope.names.slice(0, -1).join(words.sources.scope.join) + words.sources.scope.lastJoin + scope.names.at(-1)
        : scope.names[0]
    ) : scope.count === 1 ? (
      words.sources.scope.oneProject
    ) : (
      <Template text={words.sources.scope.projects} values={{ count: plain(scope.count) }} />
    );
  return row.covers ? (
    <>
      {where}
      {words.sources.scope.join}
      {row.covers}
    </>
  ) : (
    where
  );
}

function sourceRows(result: Readiness, measures: Measures): ReadinessRow[] {
  return result.sources.map((row): ReadinessRow => {
    if (row.type === "gap") {
      return {
        id: row.id,
        header: row.label,
        caption: words.sources.gapYears(String(row.first_fiscal_year), String(row.last_fiscal_year).slice(2)),
        span: (
          <div className="flex flex-col items-start gap-1">
            <span className="flex flex-wrap items-center gap-2">
              <span className="font-semibold">{words.sources.nonePublished}</span>
              <StatusBadge kind="gap" />
            </span>
            <span className="text-body">{row.note}</span>
          </div>
        ),
      };
    }
    if (row.type === "unmeasured") {
      return { id: row.id, header: row.label, caption: scopeText(row), span: <span className="text-ink-muted">{words.sources.notMeasuredRow}</span> };
    }
    return {
      id: row.id,
      header: row.label,
      caption: scopeText(row),
      cells: Object.fromEntries(COLUMNS.map((column) => [column, measureCell(row.cells[column], column, measures)])),
    };
  });
}

function kindRows(kinds: Kind[], measures: Measures): ReadinessRow[] {
  return kinds.map((kind) => {
    const ready = kind.ready_for !== null ? measures.rows[kind.ready_for] : null;
    return {
      id: kind.kind,
      header: words.kinds.names[kind.kind] ?? kind.kind,
      cells: {
        readyFor: (
          <Stack>
            {ready && kind.ready_for !== null ? (
              <span className="font-semibold">
                <MeasureValue measures={measures} index={kind.ready_for} value={{ value: ready.count ?? 0, options: { compact: false } }} noun={words.kinds.counts[kind.kind] ?? null} />
              </span>
            ) : (
              <span className="text-ink-muted">{words.sources.notMeasured}</span>
            )}
            <Qualifier>{words.kinds.counts[kind.kind]}</Qualifier>
            <Badge status={kind.status === "ready" ? null : kind.status} />
          </Stack>
        ),
        holds: (
          <div className="flex flex-col gap-1">
            {kind.holds_back.map((sentence, index) => (
              <p key={index}>
                <Sentence segments={sentence} measures={measures} />
              </p>
            ))}
          </div>
        ),
      },
    };
  });
}

// ── Column heads ─────────────────────────────────────────────────────────

function columnHead(column: Column): ReadinessColumn {
  const head = words.sources.columns[column];
  return {
    key: column,
    name: head.label,
    label: (
      <DefinitionWindow label={head.label} title={head.label}>
        {words.sources.definitions[column]}
      </DefinitionWindow>
    ),
    about: head.about,
    numeric: true,
    width: "w-[18%]",
  };
}

const KIND_COLUMNS: ReadinessColumn[] = [
  {
    key: "readyFor",
    name: words.kinds.readyFor,
    label: (
      <DefinitionWindow label={words.kinds.readyFor} title={words.kinds.readyFor}>
        {words.kinds.readyForDefinition}
      </DefinitionWindow>
    ),
    about: words.kinds.readyForAbout,
    numeric: true,
    width: "w-[30%]",
  },
  {
    key: "holds",
    name: words.kinds.holds,
    label: (
      <DefinitionWindow label={words.kinds.holds} title={words.kinds.holds}>
        {words.kinds.holdsDefinition}
      </DefinitionWindow>
    ),
    about: words.kinds.holdsAbout,
    width: "w-[42%]",
  },
];

// ── The page ─────────────────────────────────────────────────────────────

function Provenance({ result }: { result: Readiness }) {
  if (!result.measured) return null;
  const { first, last } = result.measured;
  return (
    <p className="mt-2 text-caption text-ink-muted" data-numbers>
      {first === last ? (
        <Template text={words.provenance} values={{ date: day(last, result.as_of) }} />
      ) : (
        <Template text={words.provenanceRange} values={{ from: day(first, result.as_of), to: day(last, result.as_of) }} />
      )}
    </p>
  );
}

function sourceLine(result: Readiness): ReactNode {
  return result.measured ? <Template text={words.sourceLine} values={{ date: day(result.measured.last, result.as_of, "table") }} /> : null;
}

function FilterNotice({ result }: { result: Readiness }) {
  const filter = result.filter;
  if (!filter.sources) return null;
  const fromNoun = words.server.fromNouns[(filter.from ?? "unknown") as keyof typeof words.server.fromNouns];
  const shown = filter.sources.length;
  return (
    <Alert state="info" action={<TextLink href={DATA_HREF.data}>{words.filtered.showAll}</TextLink>}>
      <Template text={shown === 1 ? words.filtered.one : words.filtered.many} values={{ count: plain(shown), fromNoun }} />
      {filter.unknown > 0 && (
        <>
          {" "}
          <Template text={words.filtered.unknown} values={{ count: plain(filter.unknown) }} />
        </>
      )}
    </Alert>
  );
}

function Fixes({ fixes, measures, filtered }: { fixes: Fix[]; measures: Measures; filtered: boolean }) {
  return (
    <section aria-labelledby="data-fixes" data-fixes className="rounded-md border border-line bg-surface p-4 md:p-6">
      <h2 id="data-fixes" className="text-title text-ink-heading">
        {words.fixes.title}
      </h2>
      <p className="mt-1 text-caption text-ink-muted">{words.fixes.caption}</p>
      {fixes.length === 0 ? (
        <p className="mt-3 text-body">{filtered ? words.fixes.noneHere : words.fixes.none}</p>
      ) : (
        <ol className="mt-3 flex flex-col gap-3">
          {fixes.map((fix) => (
            <li key={fix.gap} className="grid grid-cols-[1.5rem_1fr] gap-x-2">
              <span aria-hidden="true" className="text-body font-semibold tabular-nums text-ink-heading">
                {fix.rank}
              </span>
              <div>
                <p className="text-body">
                  <Sentence segments={fix.sentence} measures={measures} />
                </p>
                <p className="text-small" data-numbers>
                  <Template
                    text={fix.projects === 1 ? words.fixes.oneProject : words.fixes.projects}
                    values={{
                      count:
                        fix.projects_row !== null ? (
                          <MeasureValue measures={measures} index={fix.projects_row} value={{ count: fix.projects }} noun={null} column={null} />
                        ) : (
                          plain(fix.projects)
                        ),
                    }}
                  />
                </p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function Failures({ result }: { result: Readiness }) {
  if (!result.filter.sources?.includes("documents") && result.filter.sources !== null) return null;
  return (
    <section aria-labelledby="data-failures" data-failures className="mt-6">
      <h3 id="data-failures" className="text-small font-semibold text-ink-heading">
        {words.failures.title}
      </h3>
      {result.parse_failures.length === 0 ? (
        <p className="mt-1 text-small text-ink-muted">{words.failures.none}</p>
      ) : (
        <ul className="mt-1 flex flex-col gap-1 text-small">
          {result.parse_failures.map((failure) => (
            <li key={`${failure.document_id}-${failure.pdf_page}`}>
              <span className="font-mono wrap-anywhere">{failure.document_id}</span>
              {words.sources.scope.join}
              <Template text={words.failures.page} values={{ page: <Num value={failure.pdf_page} />, date: day(failure.failed_on, result.as_of, "table") }} />
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Tables({ result }: { result: Readiness }) {
  const measures: Measures = { rows: result.rows, asOf: result.as_of };
  const shown = result.sources.filter((row) => row.type !== "gap").length;
  return (
    <>
      {result.kinds.length > 0 && (
        <div className="mt-12">
          <ReadinessTable
            id="kinds"
            skeleton="kinds"
            title={words.kinds.title}
            lines={words.kinds.caption}
            head={{ label: words.kinds.kind, width: "w-[28%]" }}
            columns={KIND_COLUMNS}
            state={{ status: "ready", rows: kindRows(result.kinds, measures) }}
            source={sourceLine(result)}
          />
        </div>
      )}
      <div className="mt-12">
        <ReadinessTable
          id="sources"
          skeleton="sources"
          title={words.sources.title}
          lines={<Template text={words.sources.showing} values={{ shown: plain(shown), total: plain(result.filter.total) }} />}
          head={{ label: words.sources.source, width: "w-[28%]" }}
          columns={COLUMNS.map(columnHead)}
          state={{ status: "ready", rows: sourceRows(result, measures) }}
          source={sourceLine(result)}
          spanName={COLUMNS.map((column) => words.sources.columns[column].label).join(words.sources.scope.join)}
        />
        <Failures result={result} />
      </div>
      <div className="mt-12">
        <Fixes fixes={result.fixes} measures={measures} filtered={result.filter.sources !== null} />
      </div>
    </>
  );
}

function Lead({ children, lead, busy }: { children: ReactNode; lead?: RefObject<HTMLDivElement | null>; busy?: boolean }) {
  return (
    <div ref={lead} tabIndex={-1} data-lead aria-busy={busy || undefined} className="outline-none md:max-w-[66%]">
      {children}
    </div>
  );
}

export function DataReadiness({ search }: { search: string }) {
  const [state, setState] = useState<ReadinessState>({ status: "loading" });
  const [slow, setSlow] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const lead = useRef<HTMLDivElement>(null);
  const alert = useRef<HTMLDivElement>(null);
  const retried = useRef(false);
  const known = useStore(registry);

  useEffect(() => readRegistry(), []);

  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    setSlow(false);
    const timer = setTimeout(() => setSlow(true), SLOW_MS);
    readReadiness(search, controller.signal)
      .then(setState)
      .catch(() => undefined)
      .finally(() => clearTimeout(timer));
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [search, attempt]);

  // After "Try again", focus stays on the button while the measures load, then moves to the
  // headline, or to the new alert if it failed again.
  useEffect(() => {
    if (!retried.current || state.status === "loading") return;
    retried.current = false;
    (state.status === "error" ? alert.current : lead.current)?.focus();
  }, [state]);

  return (
    <ReadinessView
      state={state}
      search={search}
      known={known}
      slow={slow}
      lead={lead}
      alert={alert}
      onRetry={() => {
        retried.current = true;
        setAttempt((count) => count + 1);
      }}
    />
  );
}

// The page in one state, with no reading of its own, so the design gallery can show each state.
// One shape for every state: a notice, the lead and the body. The lead stays the same element
// from the skeleton to the headline, so focus on it survives the measures arriving.
export function ReadinessView({
  state,
  search = "",
  known = { status: "loading" },
  slow = false,
  lead,
  alert,
  onRetry = () => undefined,
}: {
  state: ReadinessState;
  search?: string;
  known?: ReturnType<typeof registry.get>;
  slow?: boolean;
  lead?: RefObject<HTMLDivElement | null>;
  alert?: RefObject<HTMLDivElement | null>;
  onRetry?: () => void;
}) {
  const view = render(state, search, known, slow, onRetry);
  return (
    <div data-readiness={view.name} aria-busy={view.name === "loading" || undefined}>
      {view.notice && (
        <div ref={alert} tabIndex={-1} className="mb-6 outline-none md:max-w-[66%]">
          {view.notice}
        </div>
      )}
      <Lead lead={lead} busy={view.name === "loading"}>
        {view.lead}
      </Lead>
      {view.body}
    </div>
  );
}

type View = { name: string; notice?: ReactNode; lead: ReactNode; body?: ReactNode };

function render(
  state: ReadinessState,
  search: string,
  known: ReturnType<typeof registry.get>,
  slow: boolean,
  retry: () => void,
): View {
  if (state.status === "loading") {
    const kinds = known.status === "ready" ? known.registry.kinds : ROWS_BEFORE_REGISTRY;
    const rows = known.status === "ready" ? known.registry.readiness_rows : ROWS_BEFORE_REGISTRY;
    return {
      name: "loading",
      lead: (
        <>
          <span className="clip-visually">{copy.loading}</span>
          <SkeletonText className="hidden text-h3 md:flex" widths={["w-full", "w-4/5"]} />
          <SkeletonText className="text-title md:hidden" widths={["w-full", "w-full", "w-3/5"]} />
          <div role="status" className="mt-2 min-h-lh text-caption text-ink-muted">
            {slow ? words.loading.slow : null}
          </div>
        </>
      ),
      body: (
        <>
          {kinds > 0 && (
            <div className="mt-12">
              <ReadinessTable
                id="kinds"
                skeleton="kinds"
                title={words.kinds.title}
                lines={words.kinds.caption}
                head={{ label: words.kinds.kind, width: "w-[28%]" }}
                columns={KIND_COLUMNS}
                state={{ status: "loading", rows: kinds }}
              />
            </div>
          )}
          <div className="mt-12">
            <ReadinessTable
              id="sources"
              skeleton="sources"
              title={words.sources.title}
              head={{ label: words.sources.source, width: "w-[28%]" }}
              columns={COLUMNS.map(columnHead)}
              state={{ status: "loading", rows }}
            />
          </div>
          <div className="mt-12 rounded-md border border-line bg-surface p-4 md:p-6" aria-hidden="true">
            <h2 className="text-title text-ink-heading">{words.fixes.title}</h2>
            <SkeletonText className="mt-3 text-body" widths={["w-4/5", "w-3/5", "w-2/3"]} />
          </div>
        </>
      ),
    };
  }

  if (state.status === "error") {
    const message =
      state.reason === "timeout" ? (
        <Template text={words.errors.timeout} values={{ seconds: <Num value={state.seconds ?? 0} /> }} />
      ) : state.reason === "permission" ? (
        words.errors.permission
      ) : (
        words.errors.other
      );
    return {
      name: "error",
      notice: (
        <Alert
          state="error"
          live="alert"
          action={
            state.reason === "permission" ? undefined : (
              <Button variant="primary" onClick={retry}>
                {words.errors.tryAgain}
              </Button>
            )
          }
        >
          {message}
        </Alert>
      ),
      lead: null,
    };
  }

  const result = state.result;
  const abstention = result.abstention;
  if (abstention?.reason === "unknown_sources") {
    return {
      name: "no-known-source",
      notice: (
        <Alert state="info" action={<TextLink href={DATA_HREF.data}>{words.filtered.showAll}</TextLink>}>
          {words.filtered.noneKnown}
        </Alert>
      ),
      lead: null,
    };
  }
  if (abstention?.reason === "no_measures") {
    return {
      name: "empty",
      lead: (
        <>
          <p className="text-h3 text-balance text-ink-heading">{words.empty.first}</p>
          <p className="mt-2 text-body">
            {words.empty.meanwhile.before}
            <TextLink href={DATA_HREF.dataSources}>{words.empty.meanwhile.link}</TextLink>
            {words.empty.meanwhile.after}
          </p>
        </>
      ),
    };
  }
  if (abstention?.reason === "before_first_measure") {
    const params = new URLSearchParams(search);
    params.delete("asof");
    const today = `${DATA_HREF.data}${params.toString() ? `?${params}` : ""}`;
    return {
      name: "before-first",
      lead: (
        <>
          <p className="text-h3 text-balance text-ink-heading">
            <Template
              text={words.abstain.beforeFirst}
              values={{ asked: day(result.as_of, result.as_of), first: day(abstention.first_measured_on ?? result.as_of, result.as_of) }}
            />
          </p>
          <p className="mt-2 text-body">
            <TextLink href={today}>{words.abstain.showToday}</TextLink>
          </p>
        </>
      ),
    };
  }

  const measures: Measures = { rows: result.rows, asOf: result.as_of };
  return {
    name: result.filter.sources ? "filtered" : "ready",
    notice: result.filter.sources ? <FilterNotice result={result} /> : null,
    lead: (
      <>
        {result.headline ? (
          <p className="text-title text-pretty text-ink-heading md:text-h3" data-headline>
            <Sentence segments={result.headline.segments} measures={measures} about={result.filter.sources ? words.number.sources : undefined} />
          </p>
        ) : result.headline_abstention ? (
          <p className="text-title text-pretty text-ink-heading md:text-h3" data-headline>
            <Template
              text={words.abstain.unmeasured}
              values={{ count: plain(result.headline_abstention.unmeasured), total: plain(result.headline_abstention.sources) }}
            />
          </p>
        ) : null}
        <Provenance result={result} />
      </>
    ),
    body: <Tables result={result} />,
  };
}
