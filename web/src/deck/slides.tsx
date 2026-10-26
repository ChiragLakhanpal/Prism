// The sixteen slides (the 47 brief, section 5), built from the deck's data. Each slide names its template, its title
// (the finding), its figure or chart, the text beside it, its credit row and its speaker notes. The deck lays the
// same slide out on the 960 by 540 canvas in presentation mode and as a section of one page in the reading view
// (web/src/deck/Deck.tsx), so the two never say different things.
//
// A slide whose number was not measured yet says so in its own words, in place of the sentence that would hold it.
import type { ReactNode } from "react";
import { Fill } from "../components/Fill";
import { RangeFigure } from "../components/PastRange";
import { Source } from "../components/Source";
import { TextLink } from "../components/TextLink";
import { ExternalLink } from "../components/ExternalLink";
import { numText } from "../components/Num";
import { formatDate, formatNumber } from "../lib/format";
import type { FigureId } from "../figures/registry";
import { AwardChart, AwardKey, AwardTable } from "./AwardChart";
import { deckCopy } from "./copy";
import { measured, type DeckData, type DeckResult } from "./data";
import { ESTIMATE_KEY, NoteNum, ResultNum, RubricPoints, SettingWord, TOOL_KEY, ToolNum } from "./nums";

// Each slide's title has this id, so a chart and a table region can be named by it.
export const TITLE_ID = (n: number) => `slide-${n}-title`;
const ALT_ID = "slide-7-chart-alt";
const SPEND_KEY = "r:azure-spend";

export type Template = "title" | "text" | "wide" | "narrow" | "half" | "table";
export type Mode = "present" | "read";

export type Slide = {
  n: number;
  eyebrow: string | null;
  template: Template;
  title: ReactNode;
  figure?: FigureId;
  // A chart drawn from data: the drawing as each mode shows it, its table twin, and the keys of where its numbers
  // came from, separated by spaces when it draws more than one answer.
  chart?: { drawing: (mode: Mode) => ReactNode; table: ReactNode; source: string };
  credit?: ReactNode;
  side?: ReactNode;
  body?: ReactNode;
  notes: ReactNode;
};

const s = deckCopy.slides;
const whole = (value: number) => formatNumber(value, { compact: false });
const day = (iso: string | undefined | null) => (iso ? formatDate(iso) : "");

function Points({ items }: { items: ReactNode[] }) {
  return (
    <ul className="flex flex-col gap-3 text-body text-ink">
      {items.map((item, index) => (
        <li key={index}>{item}</li>
      ))}
    </ul>
  );
}

function Note({ children }: { children: ReactNode }) {
  return (
    <p className="text-caption text-ink-muted">
      <span className="font-bold">{deckCopy.states.note}</span> {children}
    </p>
  );
}

function ratio(result: DeckResult, name: string) {
  return <ResultNum result={result} resultKey={name} value={{ part: result.n ?? 0, whole: result.d ?? 0, show: "count" }} />;
}

function count(result: DeckResult, name: string) {
  return <ResultNum result={result} resultKey={name} value={{ value: result.n ?? 0, options: { compact: false } }} />;
}

// A number in the speaker notes, plain text bound to its source.
const note = (sourceKey: string, text: string) => <NoteNum sourceKey={sourceKey} text={text} />;
const noteRatio = (result: DeckResult, name: string) => note(`r:${name}`, numText({ part: result.n ?? 0, whole: result.d ?? 0, show: "count" }));
const noteWord = (data: DeckData, name: string, capital = false) =>
  note(`s:${name}`, numText({ count: data.settings[name].value, capital }));

export function buildSlides(data: DeckData): Slide[] {
  const r = (key: string) => measured(data, key);
  const word = (name: string, capital = false) => <SettingWord data={data} settingKey={name} capital={capital} />;
  const module = (n: string) => deckCopy.module(n);

  // ── 5: documents become passages ──
  const passages = r("passages");
  const documents = r("documents-read");
  const pages = r("pages-read-well");

  // ── 7: the gap, stated ──
  const rows = r("award-rows-by-year");
  const linked = r("linked-notice");
  const gap = data.award_gap;
  const years = (rows?.series ?? []).map((row) => Number(row.fiscal_year));

  // ── 8: the time estimate ──
  const demo = data.demo;
  const comparables = demo.comparables;
  const estimate = demo.estimate;
  const backtest = r("backtest-years");
  const latestYear = backtest?.series?.filter((row) => Number(row.d) > 0).at(-1) ?? null;
  const fewest = data.settings["fewest-comparables"].value;
  // The tool's own count (CLAUDE.md rule 1), never one made here from its rows.
  const total = comparables?.counts?.comparables ?? 0;
  const tool = (value: Parameters<typeof ToolNum>[0]["value"]) =>
    comparables ? <ToolNum step={demo.step_reference} date={comparables.as_of} value={value} /> : null;
  // The time estimate's months came from estimate_time, on the day it ran.
  const months = (value: number) =>
    estimate ? (
      <ToolNum step={demo.step_reference} date={estimate.as_of} sourceKey={ESTIMATE_KEY} value={{ value, options: { decimals: 1, compact: false } }} />
    ) : null;

  // ── 10: the six checks ──
  const passed = r("benchmark-passed");
  const refused = r("must-refuse");

  // ── 13: the hindsight test and the cost ──
  const caught = r("hindsight-caught");
  const checklist = r("hindsight-checklist");
  const interval = r("hindsight-interval");
  const spend = r("azure-spend");
  // In a sentence an amount keeps its cents, with a trailing ".00" dropped (DESIGN.md section 7, rule 49).
  const amount = (value: number) => formatNumber(value, { decimals: 2, compact: false }).replace(/\.00$/, "");
  const money = (value: number) => deckCopy.money(amount(value));

  const urls = data.urls;
  const items = data.designed_not_built;

  return [
    {
      n: 1,
      eyebrow: null,
      template: "title",
      title: s.s1.statement,
      figure: "core-sample",
      notes: s.s1.notes,
    },
    {
      n: 2,
      eyebrow: null,
      template: "narrow",
      title: s.s2.title,
      figure: "one-answer",
      side: <Points items={s.s2.points} />,
      notes: s.s2.notes,
    },
    {
      n: 3,
      eyebrow: null,
      template: "text",
      title: s.s3.title,
      body: (
        <div className="flex flex-col gap-6" data-slide-columns>
          <div className="grid grid-cols-1 gap-6 @[48rem]/deck:grid-cols-3">
            {s.s3.columns.map((column) => (
              <div key={column.heading}>
                <h3 className="text-title text-ink-heading">{column.heading}</h3>
                <p className="mt-2 text-small text-ink">{column.body}</p>
              </div>
            ))}
          </div>
          <p className="text-body text-ink">{s.s3.across}</p>
        </div>
      ),
      notes: s.s3.notes,
    },
    {
      n: 4,
      eyebrow: module("1"),
      template: "wide",
      title: s.s4.title,
      figure: "pipeline",
      notes: s.s4.notes,
    },
    {
      n: 5,
      eyebrow: module("1"),
      template: "narrow",
      title: s.s5.title,
      figure: "reading",
      side: (
        <div className="flex flex-col gap-4">
          <Points
            items={[
              passages && documents ? (
                <Fill template={s.s5.passages} slots={{ passages: count(passages, "passages"), documents: count(documents, "documents-read") }} />
              ) : (
                s.s5.passagesNone
              ),
              pages ? <Fill template={s.s5.pages} slots={{ ratio: ratio(pages, "pages-read-well") }} /> : s.s5.pagesNone,
            ]}
          />
          {pages && (
            <Source>
              <Fill template={s.s5.source} slots={{ date: day(pages.measured_on) }} />
            </Source>
          )}
        </div>
      ),
      notes: s.s5.notes,
    },
    {
      n: 6,
      eyebrow: module("1"),
      template: "wide",
      title: s.s6.title,
      figure: "knowledge-model",
      credit: <Note>{s.s6.note}</Note>,
      notes: s.s6.notes,
    },
    {
      n: 7,
      eyebrow: module("1"),
      template: "narrow",
      title: !rows ? s.s7.titleNone : gap ? <Fill template={s.s7.title} slots={{ start: String(gap.start), end: String(gap.end) }} /> : s.s7.titleNoGap,
      chart: rows
        ? {
            source: "r:award-rows-by-year",
            drawing: () => (
              <div className="flex flex-col gap-2">
                <AwardKey result={rows} />
                <AwardChart result={rows} gap={gap} width={536} height={196} labelledById={TITLE_ID(7)} describedById={ALT_ID} />
                <p id={ALT_ID} className="sr-only">
                  <Fill template={s.s7.chartAlt} slots={{ first: String(Math.min(...years)), last: String(Math.max(...years)) }} />{" "}
                  {gap && <Fill template={s.s7.chartGap} slots={{ start: String(gap.start), end: String(gap.end) }} />}
                </p>
              </div>
            ),
            table: <AwardTable result={rows} caption={s.s7.table.rows} />,
          }
        : undefined,
      credit: rows ? (
        <Source>
          <Fill template={s.s7.source} slots={{ date: day(rows.measured_on) }} />
        </Source>
      ) : undefined,
      side: (
        <div className="flex flex-col gap-4">
          <Points
            items={[
              ...(gap ? [s.s7.gapNote] : []),
              ...(linked ? [<Fill key="linked" template={s.s7.linked} slots={{ ratio: ratio(linked, "linked-notice") }} />] : []),
            ]}
          />
          <p className="text-body">
            <TextLink href="/data">{s.s7.link}</TextLink>
          </p>
        </div>
      ),
      notes:
        rows && gap && linked ? (
          <Fill
            template={s.s7.notes}
            slots={{ start: String(gap.start), end: String(gap.end), ratio: noteRatio(linked, "linked-notice") }}
          />
        ) : (
          s.s7.notesNone
        ),
    },
    {
      n: 8,
      eyebrow: module("2"),
      template: "narrow",
      title: !comparables
        ? s.s8.titleNone
        : total < fewest
          ? <Fill template={s.s8.titleFew} slots={{ total: tool({ count: total }) }} />
          : !comparables.plan
            ? <Fill template={s.s8.titleNoPlan} slots={{ total: tool({ count: total }) }} />
            : (
            <Fill
              template={s.s8.title}
              slots={{
                ratio: tool({ written: numText({ part: comparables.plan.within, whole: total, show: "count" }) }),
                months: tool({ value: comparables.plan.months, options: { decimals: 1, compact: false } }),
              }}
            />
          ),
      chart: comparables
        ? {
            // The top lane draws find_comparables' answer; the lower lane, estimate_time's.
            source: estimate ? `${TOOL_KEY} ${ESTIMATE_KEY}` : TOOL_KEY,
            drawing: (mode) =>
              mode === "present" ? (
                <div className="origin-top-left" style={{ width: 831, transform: `scale(${268 / 392})` }} data-scaled-chart>
                  <RangeFigure result={comparables} estimate={estimate ? { status: "ready", result: estimate } : undefined} twin={false} />
                </div>
              ) : (
                <RangeFigure result={comparables} estimate={estimate ? { status: "ready", result: estimate } : undefined} twin={false} />
              ),
            table: <RangeFigure result={comparables} twin />,
          }
        : undefined,
      credit: comparables ? (
        <Source>
          {!estimate || estimate.as_of === comparables.as_of ? (
            <Fill template={s.s8.source} slots={{ step: <span className="font-mono">{demo.step_reference}</span>, date: day(comparables.as_of) }} />
          ) : (
            <Fill
              template={s.s8.sourceTwoDates}
              slots={{ step: <span className="font-mono">{demo.step_reference}</span>, date: day(comparables.as_of), estimateDate: day(estimate.as_of) }}
            />
          )}
        </Source>
      ) : undefined,
      side: !comparables ? (
        <Points items={[s.s8.none]} />
      ) : total < fewest ? (
        <Points items={[s.s8.dots, <Fill key="few" template={s.s8.few} slots={{ min: word("fewest-comparables") }} />]} />
      ) : (
        <Points
          items={[
            s.s8.dots,
            estimate?.estimate ? (
              <Fill
                template={s.s8.estimate}
                slots={{ low: months(estimate.estimate.q25), high: months(estimate.estimate.q75) }}
              />
            ) : (
              s.s8.estimateNone
            ),
            ...(backtest && latestYear
              ? [
                  <Fill
                    key="backtest"
                    template={s.s8.backtest}
                    slots={{
                      year: String(latestYear.label),
                      ratio: (
                        <ResultNum
                          result={{ ...backtest, n: Number(latestYear.n), d: Number(latestYear.d) }}
                          resultKey="backtest-years"
                          value={{ part: Number(latestYear.n), whole: Number(latestYear.d), show: "count" }}
                        />
                      ),
                    }}
                  />,
                ]
              : []),
          ]}
        />
      ),
      notes: <Fill template={s.s8.notes} slots={{ step: note(TOOL_KEY, demo.step_reference), agency: demo.agency }} />,
    },
    {
      n: 9,
      eyebrow: module("2"),
      template: "wide",
      title: s.s9.title,
      figure: "retrieval",
      notes: s.s9.notes,
    },
    {
      n: 10,
      eyebrow: module("3"),
      template: "text",
      title: <Fill template={s.s10.title} slots={{ checks: word("check-count") }} />,
      body: (
        <div className="grid grid-cols-1 gap-6 @[48rem]/deck:grid-cols-2">
          <div className="flex flex-col gap-3">
            <ol className="list-decimal space-y-1 pl-6 text-body text-ink">
              {data.checks.map((check) => (
                <li key={check}>{s.s10.checks[check]}</li>
              ))}
            </ol>
            <p className="text-body text-ink">{s.s10.removed}</p>
          </div>
          <div className="flex flex-col gap-3">
            <h3 className="text-title text-ink-heading">{s.s10.heading}</h3>
            {passed && refused ? (
              <>
                <ul className="flex flex-col gap-2 text-small text-ink">
                  <li>
                    <Fill template={s.s10.passed} slots={{ ratio: ratio(passed, "benchmark-passed") }} />
                  </li>
                  <li>
                    <Fill template={s.s10.refused} slots={{ ratio: ratio(refused, "must-refuse") }} />
                  </li>
                </ul>
                <Source>
                  <Fill template={s.s10.source} slots={{ date: day(passed.measured_on) }} />
                </Source>
              </>
            ) : (
              <p className="text-small text-ink">
                <Fill template={s.s10.none} slots={{ checks: word("check-count") }} />
              </p>
            )}
          </div>
        </div>
      ),
      notes: s.s10.notes,
    },
    {
      n: 11,
      eyebrow: module("3"),
      template: "half",
      title: s.s11.title,
      figure: "ladder",
      side: (
        <div className="flex flex-col gap-3" data-showcase>
          <p className="text-body text-ink">{s.s11.point}</p>
          <p className="text-small text-ink">
            <Fill template={s.s11.example} slots={{ project: <span className="font-mono">{data.showcase.project_id}</span> }} />
          </p>
          <Source>
            <Fill template={s.s11.source} slots={{ project: <span className="font-mono">{data.showcase.project_id}</span> }} />
          </Source>
        </div>
      ),
      notes: s.s11.notes,
    },
    {
      n: 12,
      eyebrow: module("4"),
      template: "wide",
      title: <Fill template={s.s12.title} slots={{ loops: word("loop-count", true) }} />,
      figure: "loops",
      notes: s.s12.notes,
    },
    {
      n: 13,
      eyebrow: module("4"),
      template: "text",
      title: caught ? <Fill template={s.s13.title} slots={{ ratio: ratio(caught, "hindsight-caught") }} /> : s.s13.titleNone,
      body: (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-1 gap-6 @[48rem]/deck:grid-cols-2">
            <div className="flex flex-col gap-3 text-body text-ink">
              {caught ? (
                <>
                  <p>
                    <Fill template={s.s13.method} slots={{ coders: word("hindsight-coders") }} />
                  </p>
                  {checklist && (
                    <p>
                      <Fill
                        template={s.s13.checklist}
                        slots={{ top: word("risks-per-package"), checklist: word("checklist-size"), ratio: ratio(checklist, "hindsight-checklist") }}
                      />
                    </p>
                  )}
                </>
              ) : (
                <p>{s.s13.none}</p>
              )}
            </div>
            <div className="flex flex-col gap-3 text-body text-ink">
              <h3 className="text-title text-ink-heading">{s.s13.costHeading}</h3>
              {spend ? (
                <p>
                  <Fill
                    template={s.s13.spend}
                    slots={{
                      date: day(spend.latest ?? spend.measured_on),
                      spent: <ResultNum result={spend} resultKey="azure-spend" value={{ written: money(spend.n ?? 0) }} tooltipValue={amount(spend.n ?? 0)} />,
                      budget: (
                        <ResultNum
                          result={{ ...spend, n: spend.budget ?? spend.d }}
                          resultKey="azure-spend"
                          value={{ written: money(spend.budget ?? spend.d ?? 0) }}
                          tooltipValue={amount(spend.budget ?? spend.d ?? 0)}
                        />
                      ),
                      period: <NoteNum sourceKey={SPEND_KEY} text={spend.period ?? ""} />,
                    }}
                  />
                </p>
              ) : (
                <p>{s.s13.noSpend}</p>
              )}
              <p>{s.s13.caps}</p>
            </div>
          </div>
          {(caught || spend) && (
            <Source>
              {caught && spend ? (
                <Fill template={s.s13.source} slots={{ hindsight: day(caught.measured_on), cost: day(spend.latest ?? spend.measured_on) }} />
              ) : caught ? (
                <Fill template={s.s13.sourceHindsight} slots={{ hindsight: day(caught.measured_on) }} />
              ) : (
                <Fill template={s.s13.sourceCost} slots={{ cost: day(spend!.latest ?? spend!.measured_on) }} />
              )}
            </Source>
          )}
        </div>
      ),
      notes: (
        <>
          <Fill template={s.s13.notes} slots={{ coders: noteWord(data, "hindsight-coders", true) }} />
          {interval && interval.low !== undefined && interval.high !== undefined && interval.level !== undefined && (
            <>
              {" "}
              <Fill
                template={s.s13.notesInterval}
                slots={{
                  level: note("r:hindsight-interval", deckCopy.percent(whole(interval.level))),
                  low: note("r:hindsight-interval", whole(interval.low)),
                  high: note("r:hindsight-interval", whole(interval.high)),
                }}
              />
            </>
          )}{" "}
          {s.s13.notesEnd}
        </>
      ),
    },
    {
      n: 14,
      eyebrow: module("4"),
      template: "table",
      title: <Fill template={s.s14.title} slots={{ phases: word("rollout-phases") }} />,
      body: (
        <div className="overflow-x-auto rounded-md border border-line bg-surface" tabIndex={0} role="region" aria-label={s.s14.caption}>
          <table className="w-full min-w-120 border-collapse text-left text-small text-ink">
            <caption className="sr-only">{s.s14.caption}</caption>
            <thead className="bg-surface-2">
              <tr>
                <th scope="col" className="w-1/6 px-3 py-2 font-semibold">{s.s14.columns.phase}</th>
                <th scope="col" className="w-1/3 px-3 py-2 font-semibold">{s.s14.columns.who}</th>
                <th scope="col" className="px-3 py-2 font-semibold">{s.s14.columns.measured}</th>
              </tr>
            </thead>
            <tbody>
              {s.s14.rows.map((row) => (
                <tr key={row.phase} className="border-t border-line align-top">
                  <th scope="row" className="px-3 py-2 font-semibold">{row.phase}</th>
                  <td className="px-3 py-2">
                    <Fill template={row.who} slots={{ countries: word("pilot-countries") }} />
                  </td>
                  <td className="px-3 py-2">{row.measured}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ),
      notes: <Fill template={s.s14.notes} slots={{ countries: noteWord(data, "pilot-countries") }} />,
    },
    {
      n: 15,
      eyebrow: null,
      template: "table",
      title: s.s15.title,
      body: (
        <div className="flex flex-col gap-3">
          <div className="overflow-x-auto rounded-md border border-line bg-surface" tabIndex={0} role="region" aria-label={s.s15.caption}>
            <table className="w-full min-w-150 border-collapse text-left text-small text-ink">
              <caption className="sr-only">{s.s15.caption}</caption>
              <thead className="bg-surface-2">
                <tr>
                  <th scope="col" className="w-1/4 px-3 py-2 font-semibold">{s.s15.columns.dimension}</th>
                  <th scope="col" className="px-3 py-2 text-right font-semibold">{s.s15.columns.points}</th>
                  <th scope="col" className="w-5/12 px-3 py-2 font-semibold">{s.s15.columns.where}</th>
                  <th scope="col" className="w-1/4 px-3 py-2 font-semibold">{s.s15.columns.open}</th>
                </tr>
              </thead>
              <tbody>
                {data.rubric.dimensions.map((dimension) => (
                  <tr key={dimension.key} className="border-t border-line align-top">
                    <th scope="row" className="px-3 py-2 font-semibold">{dimension.name}</th>
                    <td className="px-3 py-2 text-right tabular-nums">
                      <RubricPoints dimensionKey={dimension.key} points={dimension.points} />
                    </td>
                    <td className="px-3 py-2">
                      <Fill template={s.s15.where[dimension.key] ?? ""} slots={{ checks: word("check-count") }} />
                    </td>
                    <td className="px-3 py-2">
                      <RubricOpen data={data} dimension={dimension.key} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Source>{s.s15.source}</Source>
        </div>
      ),
      notes: s.s15.notes,
    },
    {
      n: 16,
      eyebrow: null,
      template: "text",
      title: s.s16.title,
      body: (
        <div className="grid grid-cols-1 gap-6 @[48rem]/deck:grid-cols-2">
          <div className="flex flex-col gap-3">
            <h3 className="text-title text-ink-heading">{s.s16.left}</h3>
            {items.length === 0 ? (
              <p className="text-body text-ink">{s.s16.empty}</p>
            ) : (
              <ul className="flex flex-col gap-2 text-body text-ink">
                {items.map((item) => (
                  <li key={item.key}>
                    <Fill template={s.s16.itemAt} slots={{ name: item.name, route: <span className="font-mono">{item.route}</span> }} />
                  </li>
                ))}
              </ul>
            )}
          </div>
          <div className="flex flex-col gap-3">
            <h3 className="text-title text-ink-heading">{s.s16.right}</h3>
            <ul className="flex flex-col gap-2 text-body">
              <li>
                <TextLink href="/">{s.s16.links.app}</TextLink>
              </li>
              {urls.proposal && (
                <li>
                  <ExternalLink href={urls.proposal} className="text-body">{s.s16.links.proposal}</ExternalLink>
                </li>
              )}
              {urls.dashboard && (
                <li>
                  <ExternalLink href={urls.dashboard} className="text-body">{s.s16.links.dashboard}</ExternalLink>
                </li>
              )}
              {urls.repo && (
                <li>
                  <ExternalLink href={urls.repo} className="text-body">{s.s16.links.repo}</ExternalLink>
                </li>
              )}
            </ul>
          </div>
        </div>
      ),
      notes: items.length === 0 ? s.s16.notesEmpty : s.s16.notes,
    },
  ];
}

// What a reviewer can open for a dimension of the rubric: screens in the app, and the dashboard when its address is set.
function RubricOpen({ data, dimension }: { data: DeckData; dimension: string }) {
  const o = s.s15.open;
  const showcase = data.showcase.project_id;
  const links: Record<string, ReactNode[]> = {
    architecture: [
      <TextLink key="data" href="/data">{o.readiness}</TextLink>,
      <TextLink key="connections" href={`/projects/${showcase}/connections`}>
        <Fill template={o.connections} slots={{ project: <span className="font-mono">{showcase}</span> }} />
      </TextLink>,
    ],
    method: [<TextLink key="workspace" href={`/packages/${data.demo.step_reference}`}>{o.workspace}</TextLink>],
    domain: [
      <TextLink key="check" href={data.demo.plan_href}>{o.checkPlan}</TextLink>,
      <TextLink key="data" href="/data">{o.readiness}</TextLink>,
    ],
    operations: data.urls.dashboard ? [<ExternalLink key="dashboard" href={data.urls.dashboard}>{o.dashboard}</ExternalLink>] : [],
  };
  return (
    <ul className="flex flex-col gap-1">
      {(links[dimension] ?? []).map((link, index) => (
        <li key={index}>{link}</li>
      ))}
    </ul>
  );
}
