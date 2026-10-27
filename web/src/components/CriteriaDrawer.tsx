// The evidence drawer's views of section 5, "Check your criteria" (ticket 31; the 31 brief, section 6.11), from
// data the section holds on the page, so they open at once:
// A. the packages whose criteria are public (criteria-public:{key}), each opening its notice's text;
// B. the notices behind one item (criteria-item:{check_id}:{item_key}), grouped by how each asked compared with
//    yours, each with its requirement word for word and a button that opens the notice's text;
// E. a comparable package's cost records (package-cost:{step_ref}): the finding, its Procurement Plan row with the
//    Estimated Amount (US$) highlighted, and its contracts with each signed amount highlighted.
// C (a notice's text), D (an award notice) and F (a lesson's paragraph) are the drawer's passage and record views.
import { Fragment, useEffect, useRef, type ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import type { ComparedItem, CostRow, ItemNotice, LessonEntry, PublicEntry, Relation } from "../lib/criteria";
import { formatAmountText, formatCount } from "../lib/format";
import { IegLine } from "./RiskDrawer";
import { Fill } from "./Fill";
import { Highlight } from "./Document";
import { MonoWords } from "./MonoWords";
import { Num } from "./Num";
import { ProjectId } from "./ProjectId";

const words = copy.criteria.drawer;
const cost = copy.cost.drawer;
const PASSAGE = "strata.gold.passage:";

export type OpenEntry = (id: string, list: { id: string; count: number }, element: HTMLElement, highlight?: [number, number] | null) => void;

export function criteriaTitle(evidence: EvidenceEvent): ReactNode {
  const row = evidence.row;
  if (evidence.kind === "criteria_public") {
    return row.count === 1 ? words.publicTitleOne : <Fill template={words.publicTitle} slots={{ n: String(row.count) }} />;
  }
  if (evidence.kind === "criteria_item") return <Fill template={words.itemTitle} slots={{ phrase: String(row.phrase) }} />;
  return <Fill template={cost.title} slots={{ ref: <MonoWords text={String(row.step_reference)} /> }} />;
}

export function criteriaEyebrow(evidence: EvidenceEvent): string {
  return evidence.kind === "package_cost" ? cost.eyebrow : words.eyebrow;
}

export function criteriaClose(evidence: EvidenceEvent | null, id: string): string {
  if (id.startsWith("package-cost:")) return cost.close;
  return words.close;
}

function Entry({ children }: { children: ReactNode }) {
  return <li className="border-t border-line py-3 first:border-t-0">{children}</li>;
}

function PublicList({ evidence, onOpen, focusEntry }: { evidence: EvidenceEvent; onOpen: OpenEntry; focusEntry: string | null }) {
  const entries = (evidence.row.entries ?? []) as PublicEntry[];
  const list = useRef<HTMLUListElement>(null);
  useEffect(() => {
    if (focusEntry) list.current?.querySelector<HTMLElement>(`[data-entry="${CSS.escape(focusEntry)}"]`)?.focus();
  }, [focusEntry]);
  return (
    <div className="flex flex-col gap-3" data-criteria-public>
      <p className="text-body text-ink">{words.publicSentence}</p>
      <ul ref={list} className="flex flex-col">
        {entries.map((entry) => (
          <Entry key={entry.step_reference}>
            <button
              type="button"
              data-entry={`${PASSAGE}${entry.passage_id}`}
              onClick={(event) => onOpen(`${PASSAGE}${entry.passage_id}`, { id: evidence.id, count: Number(evidence.row.count) }, event.currentTarget)}
              className="flex min-h-11 w-full flex-col items-start rounded-xs text-left hover:bg-tint-hover"
            >
              <span className="font-mono text-small text-primary underline">
                <MonoWords text={entry.step_reference} />
              </span>
              <span className="text-caption text-ink-muted">
                <Fill template={words.notice} slots={{ id: <span className="font-mono">{entry.notice_id}</span>, date: entry.notice_date ? <Num date={entry.notice_date} style="table" /> : "" }} />
              </span>
            </button>
          </Entry>
        ))}
      </ul>
    </div>
  );
}

const ORDER: Relation[] = ["less", "same", "more", "different"];

function ItemList({ evidence, onOpen, focusEntry }: { evidence: EvidenceEvent; onOpen: OpenEntry; focusEntry: string | null }) {
  const item = evidence.row as ComparedItem & { public: number; count: number };
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (focusEntry) root.current?.querySelector<HTMLElement>(`[data-entry="${CSS.escape(focusEntry)}"]`)?.focus();
  }, [focusEntry]);
  const notices = item.notices ?? [];
  const groups = ORDER.map((relation) => ({ relation, notices: notices.filter((notice) => notice.relation === relation) }))
    .filter((group) => group.notices.length > 0);
  return (
    <div ref={root} className="flex flex-col gap-4" data-criteria-item={item.item_key}>
      <div data-claim>
        <p className="text-caption text-ink-muted">{words.fromPage}</p>
        <p className="mt-1 border-l-2 border-line-strong pl-3 text-small text-ink">
          <Fill
            template={words.claim}
            slots={{ same: <Num value={item.same_or_less} />, compared: <Num value={item.compared} />, phrase: item.phrase }}
          />
        </p>
        <p className="mt-2 text-caption text-ink-muted">
          <Fill template={words.youAsked} slots={{ words: copy.criteria.items.quoted(item.your_excerpt.text) }} />
        </p>
      </div>
      {groups.map((group) => (
        <section key={group.relation} aria-labelledby={`criteria-group-${group.relation}`} data-relation={group.relation}>
          <h3 id={`criteria-group-${group.relation}`} tabIndex={-1} className="text-small font-bold text-ink-heading focus:outline-none">
            <Fill template={words.groupCount} slots={{ label: words.groups[group.relation], count: String(item[group.relation]) }} />
          </h3>
          <ul className="mt-2 flex flex-col">
            {group.notices.map((notice) => (
              <NoticeEntry key={notice.step_reference} notice={notice} onOpen={(element) =>
                onOpen(`${PASSAGE}${notice.passage_id}`, { id: evidence.id, count: item.stated }, element,
                  [notice.requirement.start, notice.requirement.end])} />
            ))}
          </ul>
        </section>
      ))}
      {item.not_stated > 0 && (
        <p className="text-caption text-ink-muted">
          <Fill template={words.notStated} slots={{ count: <Num value={item.not_stated} />, n: <Num value={item.public} />, phrase: item.phrase }} />
        </p>
      )}
    </div>
  );
}

function NoticeEntry({ notice, onOpen }: { notice: ItemNotice; onOpen: (element: HTMLElement) => void }) {
  return (
    <Entry>
      <p className="text-small text-ink">
        <MonoWords text={notice.step_reference} />
        {notice.country_name && <span className="text-ink-muted">{copy.list.comma}{notice.country_name}</span>}
      </p>
      <p className="mt-1 text-small text-ink" lang={notice.requirement.lang !== "en" ? notice.requirement.lang : undefined}>
        {copy.evidence.quoteOpen}
        <Highlight>{notice.requirement.text}</Highlight>
        {copy.evidence.quoteClose}
      </p>
      <button
        type="button"
        data-entry={`${PASSAGE}${notice.passage_id}`}
        onClick={(event) => onOpen(event.currentTarget)}
        className="mt-2 inline-flex min-h-11 items-center rounded-sm border border-primary px-4 text-button text-primary hover:bg-tint"
      >
        <Fill template={words.openNotice} slots={{ id: <span className="ml-1 font-mono">{notice.notice_id}</span> }} />
      </button>
    </Entry>
  );
}

function CostRecords({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row as CostRow;
  const amount = (value: string) => copy.cost.amount(formatAmountText(Number(value)));
  const plan = row.source.plan;
  return (
    <div className="flex flex-col gap-4" data-cost-records={row.step_reference}>
      {row.description && <p className="text-body text-ink">{row.description}</p>}
      <p className="text-body text-ink" data-finding>
        <Fill
          template={cost.finding}
          slots={{
            signed: amount(row.signed_amount_usd),
            diff: <Num signedPercent={row.diff_pct} words />,
            estimate: amount(row.estimated_amount_usd),
          }}
        />
      </p>
      <section className="rounded-md border border-line p-4" aria-labelledby="cost-plan-row">
        <p className="text-label text-ink-muted uppercase">{cost.eyebrow}</p>
        <h3 id="cost-plan-row" className="mt-1 text-small font-bold text-ink-heading">
          <Fill template={cost.planRow} slots={{ ref: <MonoWords text={row.step_reference} /> }} />
        </h3>
        <dl className="mt-2 flex items-baseline justify-between gap-4 text-small">
          <dt className="text-caption text-ink-muted">{cost.estimated}</dt>
          <dd className="text-right text-ink tabular-nums">
            <Highlight>
              <Num value={Number(row.estimated_amount_usd)} options={{ decimals: 2, compact: false }} />
            </Highlight>
          </dd>
        </dl>
        <p className="mt-2 text-caption text-ink-muted">
          <span className="font-bold">{copy.source}</span>{" "}
          {plan.implementing_agency && <>{plan.implementing_agency}{copy.list.comma}</>}
          {row.project_id && <><ProjectId pid={row.project_id} />{copy.list.comma}</>}
          <Fill template={cost.planFrom} slots={{ date: plan.plan_date ? <Num date={plan.plan_date} /> : "", page: String(plan.pdf_page) }} />
        </p>
      </section>
      {row.contracts.map((contract) => (
        <section key={contract.contract_id} className="rounded-md border border-line p-4" aria-label={cost.contract.replace("{id}", contract.contract_id)}>
          <p className="text-label text-ink-muted uppercase">{copy.evidence.eyebrow.What}</p>
          <h3 className="mt-1 text-small font-bold text-ink-heading">
            <Fill template={cost.contract} slots={{ id: <span className="font-mono">{contract.contract_id}</span> }} />
          </h3>
          <dl className="mt-2 flex flex-col gap-1 text-small">
            <div className="flex items-baseline justify-between gap-4">
              <dt className="text-caption text-ink-muted">{cost.amount}</dt>
              <dd className="text-right text-ink tabular-nums">
                <Highlight>
                  <Num value={Number(contract.amount_usd)} options={{ decimals: 2, compact: false }} />
                </Highlight>
              </dd>
            </div>
          </dl>
          {contract.signed_on && (
            <p className="mt-1 text-caption text-ink-muted">
              <Fill template={cost.signedOn} slots={{ date: <Num date={contract.signed_on} /> }} />
            </p>
          )}
        </section>
      ))}
      {row.contracts.length > 1 && <p className="text-caption text-ink-muted">{cost.sum}</p>}
    </div>
  );
}

export function CriteriaDrawerBody({ evidence, onOpen, focusEntry }: { evidence: EvidenceEvent; onOpen: OpenEntry; focusEntry: string | null }) {
  if (evidence.kind === "criteria_public") return <PublicList evidence={evidence} onOpen={onOpen} focusEntry={focusEntry} />;
  if (evidence.kind === "criteria_item") return <ItemList evidence={evidence} onOpen={onOpen} focusEntry={focusEntry} />;
  if (evidence.kind === "package_cost") return <CostRecords evidence={evidence} />;
  return <Fragment />;
}

// View F, a lesson's paragraph opened from section 5: the lesson it was opened for, then its IEG line, ticket 30's
// info badge with IEG's own words, or the sentence that the lesson rests on the completion report alone.
export function LessonClaim({ lesson }: { lesson: LessonEntry }) {
  return (
    <div data-claim data-lesson-claim={lesson.lesson_id} className="flex flex-col gap-3">
      <div>
        <p className="text-caption text-ink-muted">{words.fromPage}</p>
        <p className="mt-1 border-l-2 border-line-strong pl-3 text-small font-semibold text-ink-heading">{lesson.statement}</p>
      </div>
      <IegLine status={lesson.ieg_status} quote={lesson.ieg_quote} />
    </div>
  );
}

// The way back from a notice opened from one of the lists above.
export function backLabel(list: { id: string; count: number }): string {
  return list.count === 1 ? words.backOne : words.back.replace("{n}", formatCount(list.count));
}
