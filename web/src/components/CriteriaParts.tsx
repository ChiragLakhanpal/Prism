// The parts of section 5, "Check your criteria" (ticket 31; the 31 brief, sections 4 and 6): the criteria table
// (part 1), the rejected bids (part 2, brief 28's reasons list) and the lessons (part 4). The cost estimate (part
// 3) is CostLane.tsx. Every number is a tool's, written by Num; every word is the copy file's. A part's layout
// answers to the page area's width (the page column is a size container, DESIGN.md section 4): the criteria
// table becomes a list below a 768 px page area, and the reasons list moves each group's count under its label
// below 480 px of its own width.
import { useEffect, useId, useRef, useState, type MouseEvent, type ReactNode, type Ref } from "react";
import { CircleDashed } from "lucide-react";
import { copy } from "../copy";
import type { DisagreementEvent } from "../lib/answer";
import { cx } from "../lib/cx";
import { ruleSentence, sideFull, sideMeta, sideOpen, sideShort, subjectOf, whatChanges, type SideData } from "../lib/disagreement";
import { evidenceHref, evidenceIn, known, openEvidence, visited } from "../lib/evidence";
import { itemListId, type ComparedItem, type Comparison, type LessonEntry, type LessonGroup, type Rejected, type RejectedRow } from "../lib/criteria";
import { formatCount, formatDate } from "../lib/format";
import { LESSONS_HREF } from "../lib/lessons";
import { excerpt } from "../lib/sources";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { Button } from "./Button";
import { CitationMarker } from "./CitationMarker";
import { DisagreementCard, SideSaid, type CardSide } from "./DisagreementCard";
import { FootStrip } from "./FootStrip";
import { highlighted } from "./Document";
import { Fill, Joined } from "./Fill";
import { Num } from "./Num";
import { fromLine, toolFrom } from "./NumFrom";
import { ProjectId } from "./ProjectId";
import { ReasonGroup } from "./ReasonsList";
import { Source } from "./Source";
import { DefinitionWindow } from "./Term";
import { TextLink } from "./TextLink";

const words = copy.criteria;
const lessonWords = copy.criteriaLessons;

// The drawer is open at this id now.
export function useOpenId(): string | null {
  return evidenceIn(useStore(address).search);
}

// Opens the drawer at a view the page holds, or at a source; focus goes back to the opener on close, or to the
// part's heading when a rerun took the opener away.
// highlight is where words the page quotes sit in the source's text, such as a lesson's quote in its paragraph.
export function openFrom(id: string, element: HTMLElement, highlight: [number, number] | null = null) {
  const part = element.closest("[data-criteria-part]")?.querySelector<HTMLElement>("h3") ?? null;
  openEvidence(id, { serial: null, sentence: null, marker: element, runId: null, fallback: part, highlight });
}

// A part's source line (the 31 brief, 6.5, 6.7 and 6.8): its sources by their dataset names, then the day the
// records run through, the same in every part, or on an as-of page the date the records were read as of.
export function partSource({ sources, through, asOf, template, templateAsOf, slots = {} }: {
  sources: { dataset_name: string }[]; through: string | null; asOf: string | null; template: string; templateAsOf: string;
  slots?: Record<string, ReactNode>;
}): ReactNode {
  const names = <Joined items={sources.map((source) => source.dataset_name)} />;
  if (asOf) return <Fill template={templateAsOf} slots={{ sources: names, asOf: <Num date={asOf} />, ...slots }} />;
  return <Fill template={template} slots={{ sources: names, through: through ? <Num date={through} /> : "", ...slots }} />;
}

function Mono({ text }: { text: string }) {
  return <span className="font-mono wrap-anywhere">{text}</span>;
}

export function RemovedLine({ text }: { text: string }) {
  return (
    <span className="flex items-start gap-2 text-small text-neutral" data-removed-in-place>
      <CircleDashed aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-line-strong" />
      <span>{text}</span>
    </span>
  );
}

// A part: its h3 in the title token, then its body; a div named by its h3, not a landmark (the section is).
export function Part({ heading, children, headingRef, busy = false, partKey }: {
  heading: ReactNode; children: ReactNode; headingRef?: Ref<HTMLHeadingElement>; busy?: boolean; partKey: string;
}) {
  const id = useId();
  return (
    <div role="group" aria-labelledby={id} aria-busy={busy || undefined} data-criteria-part={partKey} className="mt-8">
      <h3 ref={headingRef} id={id} tabIndex={-1} className="text-h2 text-ink-heading focus:outline-none">{heading}</h3>
      <div className="mt-2">{children}</div>
    </div>
  );
}

// ── Part 1: your criteria, item by item ──────────────────────────────────

type Cells = { asked: ReactNode; sameOrLess: ReactNode; under: ReactNode };

function cellsOf(item: ComparedItem, comparison: Comparison): Cells {
  const list = itemListId(comparison.check_id, item.item_key);
  const total = comparison.coverage?.n ?? 0;
  const open = (element: HTMLElement) => openFrom(list, element);
  // Each count opens the item's notices in the drawer, and its action line says so; each was counted from the notices
  // and contract awards the tool read (ticket 96).
  const opens = { from: fromLine(toolFrom(comparison)), act: words.items.listAct, opens: "record", onOpen: open } as const;
  const asked = item.stated ? (
    <span className="text-small tabular-nums">
      <Num part={item.stated} whole={total} show="count" check={{ tooltip: words.items.statedTooltip(item.phrase), ...opens, act: words.items.statedAct }} />
      <span className="sr-only">{words.items.statedName(String(item.stated), item.phrase)}</span>
    </span>
  ) : (
    <span className="text-small text-ink-muted">{words.items.none}</span>
  );
  const sameOrLess = !item.stated ? (
    <span className="text-small text-ink-muted">{words.items.noneToCompare}</span>
  ) : !item.compared ? (
    <span className="text-small text-ink-muted">{words.items.noneCompared}</span>
  ) : (
    <span className="text-body font-semibold tabular-nums" data-same-or-less>
      <Num part={item.same_or_less} whole={item.compared} show="count"
        check={{ tooltip: words.items.sameOrLessTooltip(item.phrase), ...opens }} />
      <span className="sr-only">{words.items.sameOrLessName(String(item.same_or_less), item.phrase)}</span>
    </span>
  );
  const small = (template: string, slot: string, value: number, tooltip: string) => (
    <span className="block text-caption text-ink-muted">
      <Fill template={template} slots={{ [slot]: <Num count={value} check={{ tooltip, ...opens }} inCaption /> }} />
    </span>
  );
  const under = (
    <>
      {item.more > 0 && small(words.items.more, "more", item.more, words.items.moreTooltip(item.phrase))}
      {item.different > 0 && small(words.items.different, "different", item.different, words.items.differentTooltip(item.phrase))}
    </>
  );
  return { asked, sameOrLess, under };
}

function Excerpt({ item }: { item: ComparedItem }) {
  return (
    <>
      <span className="text-small text-ink">{words.items.quoted(item.your_excerpt.text)}</span>
      {item.your_excerpt.shortened && <span className="sr-only">{words.items.shortened}</span>}
    </>
  );
}

function Reading({ item }: { item: ComparedItem }) {
  // A removed reading's row says it once, in its count cells, which the comparison went with (ticket 58; the 31
  // design review, round 3, P3).
  if (item.reading_removed) return null;
  if (!item.reading) return null;
  return <span className="mt-1 block text-caption text-ink-muted">{item.reading}</span>;
}

function RejectedLink({ item }: { item: ComparedItem }) {
  if (!item.rejected_packages) return null;
  const go = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    const target = document.getElementById(`rejected-${item.item_key}`);
    target?.scrollIntoView({ block: "start" });
    target?.focus({ preventScroll: true });
  };
  return (
    <a href={`#rejected-${item.item_key}`} onClick={go} className="mt-1 inline-block py-1 text-caption text-primary underline hover:text-link-hover">
      {item.rejected_packages === 1 ? words.items.rejectedOne : <Fill template={words.items.rejected} slots={{ r: String(item.rejected_packages) }} />}
    </a>
  );
}

export function CriteriaTable({ comparison }: { comparison: Comparison }) {
  const captionId = useId();
  const items = comparison.items;
  const total = comparison.coverage?.n ?? 0;
  const caption =
    items.length === 1 ? (
      <Fill template={words.items.captionOne} slots={{ n: <Num value={total} /> }} />
    ) : (
      <Fill template={words.items.caption} slots={{ count: formatCount(items.length), n: <Num value={total} /> }} />
    );
  // No count line: every item shows (ticket 126). Each column's definition is in its head's window, never a second line
  // under it, and the rule for "asked for less" and "for more" opens with the head it explains (pattern 3).
  const head = (label: string, definition: ReactNode) => (
    <DefinitionWindow label={label} title={label} inText={false} triggerClassName="inline-flex min-h-6 items-center text-balance">
      {definition}
    </DefinitionWindow>
  );
  const open = useOpenId();
  const isOpen = (item: ComparedItem) => open === itemListId(comparison.check_id, item.item_key);
  return (
    <div data-criteria-table>
      {/* A table from a 768 px page area. */}
      <div className="hidden @md/page:block">
        <table className="w-full table-fixed border-collapse text-left">
          <caption className="text-left">
            <span className="mb-3 block text-body font-semibold text-ink">{caption}</span>
          </caption>
          <colgroup>
            <col className="w-[22%]" />
            <col className="w-[36%]" />
            <col className="w-[18%]" />
            <col className="w-[24%]" />
          </colgroup>
          <thead className="bg-surface-2">
            <tr>
              <th scope="col" className="p-3 align-bottom text-small font-semibold text-ink">
                {head(words.items.columns.item, words.items.columns.itemDefinition)}
              </th>
              <th scope="col" className="p-3 align-bottom text-small font-semibold text-ink">
                {head(words.items.columns.words, words.items.columns.wordsDefinition)}
              </th>
              <th scope="col" className="p-3 text-right align-bottom text-small font-semibold text-ink [&_[data-term]]:text-right">
                {head(words.items.columns.asked, <Fill template={words.items.columns.askedDefinition} slots={{ n: <Num value={total} /> }} />)}
              </th>
              <th scope="col" className="p-3 text-right align-bottom text-small font-semibold text-ink [&_[data-term]]:text-right">
                {head(
                  words.items.columns.sameOrLess,
                  <>
                    {words.items.columns.sameOrLessDefinition}
                    {words.items.columns.definitionEnd} {words.items.order}
                  </>,
                )}
              </th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const cells = cellsOf(item, comparison);
              return (
                <tr key={item.item_key} data-item={item.item_key} className={cx("border-t border-line", isOpen(item) && "bg-tint")}>
                  <th scope="row" className="h-12 p-3 align-top font-normal">
                    <span className="block text-small font-semibold text-ink-heading">{item.label}</span>
                    <RejectedLink item={item} />
                  </th>
                  <td className="p-3 align-top">
                    <Excerpt item={item} />
                    <Reading item={item} />
                  </td>
                  {item.reading_removed ? (
                    <td colSpan={2} className="p-3 align-top">
                      <RemovedLine text={words.items.removed} />
                    </td>
                  ) : (
                    <>
                      <td className="p-3 text-right align-top">{cells.asked}</td>
                      <td className="p-3 text-right align-top">
                        {cells.sameOrLess}
                        {cells.under}
                      </td>
                    </>
                  )}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {/* A list below a 768 px page area. */}
      <div className="@md/page:hidden">
        <p id={captionId} className="text-body font-semibold text-ink">{caption}</p>
        <ol aria-labelledby={captionId} className="mt-3 flex flex-col">
          {items.map((item) => {
            const cells = cellsOf(item, comparison);
            return (
              <li key={item.item_key} data-item={item.item_key} className={cx("-mx-2 border-t border-line px-2 py-4", isOpen(item) && "bg-tint")}>
                <h4 className="text-small font-semibold text-ink-heading">{item.label}</h4>
                <p className="mt-1">
                  <Excerpt item={item} />
                </p>
                <Reading item={item} />
                {item.reading_removed ? (
                  <p className="mt-3">
                    <RemovedLine text={words.items.removed} />
                  </p>
                ) : (
                  <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] gap-x-2 gap-y-1">
                    <span className="text-caption text-ink-muted">{words.items.columns.asked}</span>
                    <span className="text-right">{cells.asked}</span>
                    <span className="text-caption text-ink-muted">{words.items.columns.sameOrLess}</span>
                    <span className="text-right">{cells.sameOrLess}</span>
                    <span className="col-span-2 text-right">{cells.under}</span>
                  </div>
                )}
                <RejectedLink item={item} />
              </li>
            );
          })}
        </ol>
      </div>
    </div>
  );
}

// The notes under the table, in its foot strip, in the brief's order: the parts not compared, how items are put in
// order, the coverage line and the source line. No currency note: no notice's amount was converted (fx_count is 0).
export function CriteriaNotes({ comparison, readinessHref, asOf = null }: { comparison: Comparison; readinessHref: string; asOf?: string | null }) {
  const [shown, setShown] = useState(false);
  const listId = useId();
  const firstPart = useRef<HTMLLIElement>(null);
  const k = comparison.unplaced.length;
  const coverage = comparison.coverage;
  useEffect(() => {
    if (shown) firstPart.current?.focus();
  }, [shown]);
  const toggle = k === 1 ? (shown ? words.items.hideIt : words.items.showIt) : shown ? words.items.hideThem : words.items.showThem;
  // The notes end the part in its foot strip, as each block of evidence ends (ticket 101's critique, round 2).
  return (
    <FootStrip part>
    <div className="flex flex-col gap-2" data-criteria-notes>
      {k > 0 && (
        <div>
          <p>
            {k === 1 ? words.items.unplacedOne : <Fill template={words.items.unplaced} slots={{ k: formatCount(k) }} />}
          </p>
          <Button variant="ghost" flush aria-expanded={shown} aria-controls={listId} onClick={() => setShown((value) => !value)}>
            {toggle}
          </Button>
          <ul id={listId} hidden={!shown} className="mt-1 flex list-disc flex-col gap-1 pl-4 text-small text-ink">
            {comparison.unplaced.map((part, index) => (
              <li key={index} ref={index === 0 ? firstPart : undefined} tabIndex={-1} className="focus:outline-none">
                {words.items.quoted(part)}
              </li>
            ))}
          </ul>
        </div>
      )}
      {/* From 768 px the rule is in the "Asked for the same or less" head's window (ticket 126); the cards below that
          have no heads, so it stays here for them. */}
      <p className="@md/page:hidden">{words.items.order}</p>
      {coverage && (
        <p data-coverage-line>
          {coverage.missing + coverage.open === 0 ? (
            <Fill template={words.items.coverageAll} slots={{ total: <Num value={coverage.total} /> }} />
          ) : (
            <>
              <Fill template={words.items.coverage} slots={{ n: <Num value={coverage.n} />, total: <Num value={coverage.total} /> }} />
              {coverage.missing > 0 && (
                <>
                  {" "}
                  <Fill template={words.items.coverageMissing} slots={{ missing: <Num count={coverage.missing} capital /> }} />
                </>
              )}
              {coverage.open > 0 && (
                <>
                  {" "}
                  <Fill template={words.items.coverageOpen} slots={{ open: <Num count={coverage.open} /> }} />
                </>
              )}
            </>
          )}{" "}
          <TextLink href={readinessHref}>{words.items.coverageLink}</TextLink>
        </p>
      )}
      <Source>
        {partSource({
          sources: comparison.sources,
          through: comparison.records_through,
          asOf: asOf ? comparison.as_of : null,
          template: words.items.source,
          templateAsOf: words.items.sourceAsOf,
          slots: { compared: <Num date={comparison.compared_at.slice(0, 10)} /> },
        })}
      </Source>
    </div>
    </FootStrip>
  );
}

// ── Part 2: rejected bids ─────────────────────────────────────────────────

function rowsOf(rejected: Rejected, key: string): RejectedRow[] {
  return rejected.rows.filter((row) => row.item_key === key);
}

// Markers are numbered once in DOM order across the section, counting rows not shown yet, so a number never
// changes when more rows open (brief 28's rule). An evidence id cited twice keeps its number.
export function markerNumbers(rejected: Rejected | null, lessons: LessonGroup[] | null): Map<string, number> {
  const numbers = new Map<string, number>();
  const add = (id: string) => {
    if (!numbers.has(id)) numbers.set(id, numbers.size + 1);
  };
  for (const group of rejected?.groups ?? []) for (const row of rowsOf(rejected!, group.item_key)) add(row.evidence_id);
  for (const group of lessons ?? []) for (const lesson of group.lessons) add(lesson.passage_evidence_id);
  return numbers;
}

// The words a card's side quotes, where the server marked them for the sentence the card follows, so the drawer
// opens the side on them (ticket 61's review, F3). The section remembers each side's evidence (rememberSides).
function sideHighlight(found: DisagreementEvent, id: string): [number, number] | null {
  const mark = known.get()[id]?.highlights.find((one) => one.sentence === found.after);
  return mark ? [mark.start, mark.end] : null;
}

// Every disagreement check 6 attached to a reason's or a lesson's quote, under it, one card each, so the section
// shows as many cards as the check line counts (ticket 61's verify, F1).
function CheckCards({ found }: { found: DisagreementEvent[] | undefined }) {
  return <>{(found ?? []).map((one) => <CheckCard key={one.id} found={one} />)}</>;
}

// A disagreement check 6 attached to a reason's or a lesson's quote, under it, with both sides (ticket 31's review
// round 3, F2; DESIGN.md section 5, Disagreement card: shown only beside the claim it concerns). The section offers no
// choice of side: it keeps no draft, so the card says what the reports say and lets you open each.
function CheckCard({ found }: { found: DisagreementEvent }) {
  if (found.sides.length !== 2) return null;
  const sides = found.sides as SideData[];
  const cardSides = sides.map((side) => ({
    title: sideFull(side),
    titleText: sideFull(side),
    meta: sideMeta(side),
    leaned: side.leaned,
    assertionId: side.assertion_id ?? undefined,
    said: <SideSaid side={side} />,
    open: {
      label: sideOpen(side),
      href: evidenceHref(side.evidence_id),
      onOpen: (element: HTMLElement) => openFrom(side.evidence_id, element, sideHighlight(found, side.evidence_id)),
    },
  })) as [CardSide, CardSide];
  const badge = found.changes_answer ? copy.badge.twoReportsDisagree : copy.badge.sourcesDiffer;
  return (
    <div className="mt-2" data-criteria-disagreement={found.id}>
      <DisagreementCard
        warning={found.changes_answer}
        name={copy.disagreement.groupName(badge, sideShort(sides[0]), sideShort(sides[1]))}
        subject={subjectOf(found.attribute, found.period_event ?? null)}
        level={4}
        sides={cardSides}
        rule={ruleSentence(found.rule_id, sides)}
        whatChanges={whatChanges(sides, found.if_you_keep)}
      />
    </div>
  );
}

function markerLabel(row: RejectedRow): string {
  return row.notice_date ? words.rejected.markerSource(row.notice_id, formatDate(row.notice_date)) : words.rejected.markerSourceUndated(row.notice_id);
}

function RejectedRowView({ row, n }: { row: RejectedRow; n: number }) {
  const seen = useStore(visited);
  const open = useOpenId();
  const active = open === row.evidence_id;
  return (
    <li className={cx("flex flex-col gap-1", active && "-mx-2 rounded-xs bg-tint px-2")} data-rejected-row={row.evidence_id}>
      <p className="text-small">
        <button
          type="button"
          aria-label={words.rejected.openRecords(row.step_reference)}
          onClick={(event) => openFrom(`strata.gold.package:${row.step_reference}`, event.currentTarget)}
          className="relative -my-1 py-1 text-left font-mono text-small text-primary underline hover:text-link-hover"
          data-step-ref
        >
          <Mono text={row.step_reference} />
        </button>
        {row.country_name && <span className="text-ink-muted">{copy.list.comma}{row.country_name}</span>}
      </p>
      {row.removed ? (
        <RemovedLine text={words.removedInPlace} />
      ) : (
        <p className="text-small text-ink" lang={row.reason.lang !== "en" ? row.reason.lang : undefined}>
          {words.items.quoted(row.reason.quote)}
          <CitationMarker
            n={n}
            source={markerLabel(row)}
            href={evidenceHref(row.evidence_id)}
            opened={seen.has(row.evidence_id)}
            active={active}
            drawerId="evidence-drawer"
            evidenceId={row.evidence_id}
            onOpen={(marker) => openFrom(row.evidence_id, marker)}
          />
        </p>
      )}
      {!row.removed && <CheckCards found={row.disagreements} />}
      <p className="text-caption text-ink-muted">
        <Fill
          template={words.rejected.notice}
          slots={{ id: <Mono text={row.notice_id} />, date: row.notice_date ? <span className="whitespace-nowrap"><Num date={row.notice_date} style="table" /></span> : "" }}
        />
      </p>
      {row.bids > 1 && (
        <p className="text-caption text-ink-muted">
          <Fill template={words.rejected.sameNotice} slots={{ b: formatCount(row.bids, { capital: true }) }} />
        </p>
      )}
      {row.reason.lang !== "en" && copy.language.name[row.reason.lang] && (
        <p className="text-caption text-ink-muted">{words.rejected.inLanguage(copy.language.name[row.reason.lang])}</p>
      )}
    </li>
  );
}

function Group({ rejected, groupKey, numbers, yours, perGroup }: {
  rejected: Rejected; groupKey: string; numbers: Map<string, number>; yours: boolean; perGroup: number;
}) {
  const group = rejected.groups.find((one) => one.item_key === groupKey)!;
  const rows = rowsOf(rejected, groupKey);
  return (
    <div className="@container/reasons" data-rejected-group={groupKey}>
      <ReasonGroup
        headingId={`rejected-${groupKey}`}
        label={group.label}
        count={<Fill template={words.rejected.groupCount} slots={{ c: String(group.count), n: String(rejected.counts.m) }} />}
        name={words.rejected.groupName(group.label, String(group.count), String(rejected.counts.m))}
        note={yours ? <p className="mt-1 text-caption text-ink-muted">{words.rejected.yours}</p> : undefined}
        perGroup={perGroup}
        rows={rows.map((row) => <RejectedRowView key={row.evidence_id} row={row} n={numbers.get(row.evidence_id) ?? 0} />)}
        moreLabel={(more) => (more === 1 ? words.rejected.showOneMore : <Fill template={words.rejected.showMore} slots={{ count: formatCount(more) }} />)}
      />
    </div>
  );
}

export function RejectedBids({ rejected, numbers, yourItems, perGroup, readinessHref, asOf = null }: {
  rejected: Rejected; numbers: Map<string, number>; yourItems: Set<string>; perGroup: number; readinessHref: string;
  // The page's as-of date, when it has one: the source line then says the records were read as of it.
  asOf?: string | null;
}) {
  const { m, n, total } = rejected.counts;
  const focusFirstGroup = () => {
    const first = rejected.groups[0];
    if (first) document.getElementById(`rejected-${first.item_key}`)?.focus();
  };
  const num = (value: number) => (
    <Num value={value} check={{ tooltip: words.rejected.countTooltip, from: fromLine(toolFrom(rejected)), act: words.rejected.countAct, opens: "rows", onOpen: focusFirstGroup }} />
  );
  if (rejected.state === "no_award_notices" || rejected.state === "no_comparables") {
    return (
      <div className="flex flex-col gap-2" data-rejected="none">
        <p className="text-body text-ink">{words.rejected.noNotices}</p>
        <p className="text-caption">
          <TextLink href={readinessHref}>{words.rejected.noneLink}</TextLink>
        </p>
      </div>
    );
  }
  const count =
    n === 0 ? (
      <Fill template={words.rejected.countNone} slots={{ m: num(m) }} />
    ) : n === m ? (
      <Fill template={words.rejected.countAll} slots={{ m: num(m) }} />
    ) : n === 1 ? (
      <Fill template={words.rejected.countOne} slots={{ m: num(m) }} />
    ) : (
      <Fill template={words.rejected.count} slots={{ n: num(n), m: num(m) }} />
    );
  return (
    <div className="flex flex-col gap-2" data-rejected={rejected.state}>
      <p className="text-body text-ink" data-rejected-count>{count}</p>
      {m < total && (
        <p className="text-caption text-ink-muted">
          <Fill template={words.rejected.denominator} slots={{ m: <Num value={m} />, total: <Num value={total} /> }} />
        </p>
      )}
      {/* With none rejected, the link to the award notices' readiness stays and the coverage line says what is missing
          (ticket 126); with some, how I quoted them is in the title's window. */}
      {n === 0 ? (
        <p className="text-caption">
          <TextLink href={readinessHref}>{words.rejected.noneLink}</TextLink>
        </p>
      ) : (
        <>
          <div className="mt-2 flex flex-col gap-6">
            {rejected.groups.map((group) => (
              <Group key={group.item_key} rejected={rejected} groupKey={group.item_key} numbers={numbers}
                yours={yourItems.has(group.item_key)} perGroup={perGroup} />
            ))}
          </div>
        </>
      )}
      {(rejected.records_through || asOf) && (
        <FootStrip part>
          <Source>
            {partSource({ sources: rejected.sources, through: rejected.records_through, asOf, template: words.rejected.source,
              templateAsOf: words.rejected.sourceAsOf })}
          </Source>
        </FootStrip>
      )}
    </div>
  );
}

// ── Part 4: lessons on cost estimates and specifications ─────────────────

function statusOf(lesson: LessonEntry, firstIeg: boolean): string {
  if (lesson.ieg_status === "restated") return firstIeg ? lessonWords.status.restatedSpelled : lessonWords.status.restated;
  if (lesson.ieg_status === "awaiting") return firstIeg ? lessonWords.status.awaitingSpelled : lessonWords.status.awaiting;
  return lessonWords.status[lesson.ieg_status] ?? lessonWords.status.awaiting;
}

function LessonCardView({ lesson, n, firstIcr, firstIeg }: { lesson: LessonEntry; n: number; firstIcr: boolean; firstIeg: boolean }) {
  const seen = useStore(visited);
  const open = useOpenId();
  const active = open === lesson.passage_evidence_id;
  const titleId = useId();
  const docType = lesson.doc_short === "ICR" && firstIcr ? lessonWords.icrSpelled : lesson.document_type;
  const date = lesson.document_date ? formatDate(lesson.document_date) : "";
  const source = lesson.locator === "section"
    ? lessonWords.markerSection(lesson.document_type, date, lesson.para ?? "")
    : lessonWords.markerParagraph(lesson.document_type, date, lesson.para ?? "");
  // The paragraph around the lesson's words, with them highlighted (DESIGN.md section 5, Evidence card); the
  // quote alone when the paragraph could not be read.
  const shown = lesson.excerpt && lesson.excerpt.range ? excerpt(lesson.excerpt.text, lesson.excerpt.range as [number, number]) : null;
  return (
    <article aria-labelledby={titleId} className="relative rounded-md border border-line bg-surface p-4 @md/page:p-6" data-lesson-card={lesson.lesson_id}>
      {/* No stratum eyebrow (ticket 126): the statement is the card's title. */}
      <h4 id={titleId} className="pr-8 text-h2 text-ink-heading">
        {lesson.statement}
      </h4>
      {/* The citation number sits top right, after the title in the DOM, so the card's name is its title alone. */}
      <span className="absolute top-4 right-4 @md/page:top-6 @md/page:right-6" data-lesson-marker>
        <CitationMarker
          n={n}
          source={source}
          href={evidenceHref(lesson.passage_evidence_id)}
          opened={seen.has(lesson.passage_evidence_id)}
          active={active}
          drawerId="evidence-drawer"
          evidenceId={lesson.passage_evidence_id}
          onOpen={(marker) => openFrom(lesson.passage_evidence_id, marker, (lesson.excerpt?.range as [number, number] | null) ?? null)}
        />
      </span>
      {lesson.removed ? (
        <p className="mt-2">
          <RemovedLine text={words.removedInPlace} />
        </p>
      ) : shown ? (
        <p className="mt-2 text-small text-ink" lang={lesson.excerpt?.lang} data-lesson-excerpt>
          {copy.evidence.quoteOpen}
          {shown.cutBefore && copy.evidence.cut}
          {highlighted(shown.text, shown.range ? [shown.range] : [])}
          {shown.cutAfter && copy.evidence.cut}
          {copy.evidence.quoteClose}
        </p>
      ) : (
        <p className="mt-2 text-small text-ink" lang={lesson.excerpt?.lang}>{lessonWords.quoted(lesson.quote)}</p>
      )}
      {!lesson.removed && <CheckCards found={lesson.disagreements} />}
      <p className="mt-2 text-caption text-ink-muted" data-source>
        <span className="font-bold">{lessonWords.sourceLead}</span>{" "}
        <Fill
          template={lesson.locator === "section" ? lessonWords.sourceLineSection : lessonWords.sourceLine}
          slots={{
            type: docType,
            pid: <ProjectId pid={lesson.project_id} />,
            date: lesson.document_date ? <Num date={lesson.document_date} /> : "",
            para: <span className="whitespace-nowrap">{lesson.para}</span>,
            page: String(lesson.page ?? ""),
          }}
        />
      </p>
      <p className="mt-1 text-caption text-ink-muted" data-lesson-status>
        <Fill template={statusOf(lesson, firstIeg)} slots={{ v: String(lesson.version) }} />
      </p>
    </article>
  );
}

export function CriteriaLessons({ groups, numbers }: { groups: LessonGroup[]; numbers: Map<string, number> }) {
  let icrSeen = false;
  let iegSeen = false;
  return (
    <div className="flex flex-col gap-2" data-criteria-lessons>
      <p className="text-caption text-ink-muted">{lessonWords.intro}</p>
      {groups.length === 0 ? (
        <>
          <p className="text-body text-ink">{lessonWords.none}</p>
          <p className="text-caption">
            <TextLink href={LESSONS_HREF}>{lessonWords.noneLink}</TextLink>
          </p>
        </>
      ) : (
        <div className="mt-2 flex flex-col gap-6">
          {groups.map((group) => (
            <div key={group.factor} data-lesson-group={group.factor}>
              <h4 className="text-small font-bold text-ink-heading">{lessonWords.groups[group.factor]}</h4>
              <div className="mt-2 flex flex-col gap-4">
                {group.lessons.map((lesson) => {
                  const firstIcr = !icrSeen && lesson.doc_short === "ICR";
                  icrSeen ||= lesson.doc_short === "ICR";
                  const firstIeg = !iegSeen;
                  iegSeen = true;
                  return (
                    <LessonCardView key={lesson.lesson_id} lesson={lesson} n={numbers.get(lesson.passage_evidence_id) ?? 0}
                      firstIcr={firstIcr} firstIeg={firstIeg} />
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
