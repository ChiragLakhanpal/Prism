// The evidence drawer's views a project timeline's marks open (ticket 23; the 23 brief, section 6), each from a
// typed evidence id that GET /api/evidence resolves on any page:
//
// - doc:{document_id}: a report's document view: its type, number, dates and pages, what it rated with the passage
//   each rating rests on, the disagreement it is a side of, and the re-issue that replaced it.
// - ratings:{pid}:{attribute}:{first}-{last}: a band's run of ISR ratings, said to be a trajectory, not a
//   disagreement.
// - contracts:{pid}:{year}: a year's contracts, from a crowded What lane.
// - disagreement:{id}: both reports, with a switcher whose first tab, "Both reports", shows the disagreement card
//   and whose other tabs show each side's passage as the drawer shows any passage.
import { useId, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { copy } from "../copy";
import type { EvidenceEvent } from "../lib/answer";
import { sourcePageHref } from "../lib/documents";
import { evidenceHref, openEvidence } from "../lib/evidence";
import { cx } from "../lib/cx";
import { shortName } from "../lib/timeline";
import { formatDate } from "../lib/format";
import { sideContext, sideMeta, sideOpen, sideShort, sideTitle, subjectOf, ruleSentence, whatChanges, type SideData } from "../lib/disagreement";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { DisagreementCard, SideSaid, type CardSide } from "./DisagreementCard";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { ProjectId } from "./ProjectId";
import { Source } from "./Source";
import { StatusBadge } from "./StatusBadge";
import { Table, type Column } from "./Table";
import { TextLink } from "./TextLink";

const words = copy.timeline.drawer;
export const TIMELINE_KINDS = ["document", "ratings", "contracts", "disagreement"] as const;
export const isTimelineView = (evidence: EvidenceEvent | null) => Boolean(evidence && (TIMELINE_KINDS as readonly string[]).includes(evidence.kind));

const reportLabel = (row: Record<string, any>) => {
  const base = (copy.timeline.label[row.type] ?? copy.timeline.label.other).replace("{sequence}", String(row.sequence ?? ""));
  return row.replaced_by ? copy.timeline.replaced.replace("{label}", base) : row.reissued ? copy.timeline.reissued.replace("{label}", base) : base;
};

const strataOf = (sides: Record<string, any>[]) => {
  const lanes = [...new Set(sides.map((side) => (side.type === "isr" ? "How" : side.type === "record" ? "What" : "Why")))];
  const order = ["What", "How", "Why"];
  lanes.sort((a, b) => order.indexOf(a) - order.indexOf(b));
  return lanes.length === 2 ? words.strataJoin.replace("{first}", lanes[0]).replace("{second}", lanes[1]) : lanes[0];
};

// The eyebrow each view shows above its heading.
export function timelineEyebrow(evidence: EvidenceEvent): string {
  const row = evidence.row;
  if (evidence.kind === "ratings") return words.ratings.eyebrow;
  if (evidence.kind === "contracts") return words.contracts.eyebrow;
  if (evidence.kind === "disagreement") return words.disagreement.eyebrow.replace("{strata}", strataOf(row.sides ?? []));
  return copy.evidence.eyebrow[evidence.stratum ?? "Why"];
}

// The heading each view shows: "ISR 7, August 26, 2016", "ISRs 1–9, rated Satisfactory", "Contracts signed in 2019",
// "ISR 7 and ICR paragraph 78".
export function timelineTitle(evidence: EvidenceEvent): ReactNode {
  const row = evidence.row;
  if (evidence.kind === "document") return words.doc.heading.replace("{label}", reportLabel(row)).replace("{date}", formatDate(row.document_date));
  if (evidence.kind === "ratings") {
    const template = row.first === row.last ? words.ratings.headingOne : words.ratings.heading;
    return template.replace("{first}", String(row.first)).replace("{last}", String(row.last)).replace("{rating}", row.rating);
  }
  if (evidence.kind === "contracts") return words.contracts.heading.replace("{year}", String(row.year));
  const sides = (row.sides ?? []) as SideData[];
  return words.disagreement.heading.replace("{side1}", sideShort(sides[0])).replace("{side2}", sideShort(sides[1]));
}

export function timelineClose(evidence: EvidenceEvent | null): string {
  if (evidence?.kind === "ratings") return words.ratings.close;
  if (evidence?.kind === "contracts") return words.contracts.close;
  if (evidence?.kind === "disagreement") return words.disagreement.close;
  return words.doc.close;
}

// Open another timeline view in place, as the switcher and the lists do: the drawer keeps its opener.
const openInPlace = (id: string) =>
  openEvidence(id, { serial: null, sentence: null, marker: null, runId: null }, { replace: true, focus: false });

// The disagreement line a document view and a claim's drawer show: the state pill, "{this} and {other} disagree
// about this." and "Show both reports".
export function ClaimLine({ text, warning, disagreementId }: { text: string; warning: boolean; disagreementId: string }) {
  return (
    <div data-claim-line className="flex flex-col items-start gap-2">
      <StatusBadge kind={warning ? "two-reports-disagree" : "sources-differ"} />
      <p className="text-small text-ink">{text}</p>
      <Button variant="ghost" flush onClick={() => openEvidence(disagreementId, { serial: null, sentence: null, marker: null, runId: null }, { replace: false })}>
        {words.showBoth}
      </Button>
    </div>
  );
}

function DocumentView({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row;
  const thisShort = shortName(row as { type: string; sequence: number | null });
  const fields: [string, ReactNode, boolean][] = [
    [words.doc.labels.type, row.document_type, true],
    ...(row.report_number ? [[words.doc.labels.number, <span className="font-mono">{row.report_number}</span>, false] as [string, ReactNode, boolean]] : []),
    [words.doc.labels.date, <Num date={row.document_date} />, false],
    [words.doc.labels.disclosed, <Num date={row.public_from} />, false],
    [words.doc.labels.pages, <Num value={Number(row.pdf_pages)} options={{ compact: false }} />, false],
  ];
  const columns: Column[] = [
    { key: "rating", header: words.doc.ratingsCols.rating, width: "w-2/5" },
    { key: "value", header: words.doc.ratingsCols.value, width: "w-1/4", short: true },
    { key: "where", header: words.doc.ratingsCols.where },
  ];
  const where = (rating: Record<string, any>) =>
    (rating.paragraph ? words.doc.wherePara.replace("{para}", rating.paragraph) : rating.section ? words.doc.whereSection.replace("{section}", rating.section) : words.doc.wherePage).replace(
      "{page}",
      String(rating.pdf_page ?? ""),
    );
  return (
    <div data-document-view className="flex flex-col gap-4">
      {row.replaced_by && (
        <Alert state="info">
          {words.doc.replaced.replace("{date}", formatDate(row.replaced_by.date))}{" "}
          <TextLink href={evidenceHref(row.replaced_by.evidence_id)} onClick={(event) => (event.preventDefault(), openInPlace(row.replaced_by.evidence_id))}>
            {words.doc.openReissue}
          </TextLink>
        </Alert>
      )}
      {(row.disagreements ?? []).map((found: Record<string, any>) => (
        <ClaimLine
          key={found.evidence_id}
          warning={false}
          disagreementId={found.evidence_id}
          text={words.doc.inDisagreement
            .replace("{this}", thisShort)
            .replace("{other}", shortName(found.other))
            .replace("{subject}", subjectOf(found.attribute, found.period_event).replace(/^./, (first) => first.toLowerCase()))}
        />
      ))}
      <dl data-document-fields className="grid grid-cols-2 gap-x-4 gap-y-2 rounded-md border border-line p-4">
        {fields.map(([name, value, wide]) => (
          <div key={name} className={cx("min-w-0", wide && "col-span-full")}>
            <dt className="text-caption text-ink-muted">{name}</dt>
            <dd className="text-small text-ink [overflow-wrap:anywhere]">{value}</dd>
          </div>
        ))}
      </dl>
      {(row.ratings ?? []).length > 0 && (
        <Table
          title={words.doc.ratings}
          level={3}
          cardsBelow="fit"
          columns={columns}
          rowHeader="rating"
          state={{
            status: "ready",
            rows: row.ratings.map((rating: Record<string, any>, index: number) => ({
              id: String(index),
              cells: {
                rating: rating.field_name,
                value: rating.value,
                where: (
                  <TextLink href={evidenceHref(rating.evidence_id)} onClick={(event) => (event.preventDefault(), openEvidence(rating.evidence_id, { serial: null, sentence: null, marker: null, runId: null }, { replace: false }))}>
                    {where(rating)}
                  </TextLink>
                ),
              },
            })),
          }}
        />
      )}
      {row.doc_key && (
        <p>
          <TextLink href={sourcePageHref(row.project_id, row.doc_key, 1)} className="text-small">
            {words.doc.open}
          </TextLink>
        </p>
      )}
      <Source>
        <Fill
          template={words.doc.source}
          slots={{ type: row.document_type, pid: <ProjectId pid={row.project_id} />, date: <Num date={row.document_date} /> }}
        />
      </Source>
    </div>
  );
}

function RatingsView({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row;
  const columns: Column[] = [
    { key: "isr", header: words.ratings.columns.isr, width: "w-1/4" },
    { key: "date", header: words.ratings.columns.date, width: "w-1/3", short: true },
    { key: "rating", header: words.ratings.columns.rating },
  ];
  return (
    <div data-ratings-view className="flex flex-col gap-4">
      <p className="text-caption text-ink-muted">{words.ratings.trajectory}</p>
      <Table
        title={words.ratings.caption}
        level={3}
        cardsBelow="fit"
        count={{ noun: copy.timeline.itemsNoun, total: row.rows.length, text: words.ratings.count(String(row.rows.length)) }}
        columns={columns}
        rowHeader="isr"
        state={{
          status: "ready",
          rows: row.rows.map((one: Record<string, any>) => ({
            id: one.evidence_id,
            cells: {
              isr: (
                <TextLink href={evidenceHref(one.evidence_id)} onClick={(event) => (event.preventDefault(), openInPlace(one.evidence_id))}>
                  {words.ratings.isr.replace("{sequence}", String(one.sequence))}
                </TextLink>
              ),
              date: <Num date={one.date} style="table" />,
              rating: one.rating,
            },
          })),
        }}
        source={<Fill template={words.ratings.source} slots={{ pid: <ProjectId pid={row.project_id} /> }} />}
      />
    </div>
  );
}

function ContractsView({ evidence }: { evidence: EvidenceEvent }) {
  const row = evidence.row;
  const columns: Column[] = [
    { key: "contract", header: words.contracts.columns.contract, width: "w-1/2" },
    { key: "signed", header: words.contracts.columns.signed, width: "w-1/4", short: true },
    { key: "amount", header: words.contracts.columns.amount, numeric: true },
  ];
  return (
    <div data-contracts-view className="flex flex-col gap-4">
      <Table
        title={words.contracts.heading.replace("{year}", String(row.year))}
        level={3}
        cardsBelow="fit"
        count={{ noun: copy.timeline.itemsNoun, total: row.rows.length, text: words.contracts.count(String(row.rows.length)) }}
        columns={columns}
        rowHeader="contract"
        state={{
          status: "ready",
          rows: row.rows.map((one: Record<string, any>) => ({
            id: one.step_reference,
            cells: {
              contract: (
                <TextLink href={evidenceHref(one.evidence_id)} className="font-mono [overflow-wrap:anywhere]" onClick={(event) => (event.preventDefault(), openInPlace(one.evidence_id))}>
                  {one.step_reference}
                </TextLink>
              ),
              signed: <Num date={one.signed_on} style="table" />,
              amount: one.signed_amount_usd ? <Num value={Number(one.signed_amount_usd)} options={{ decimals: 2, compact: false }} /> : words.contracts.notInRecord,
            },
          })),
        }}
        source={<Fill template={words.contracts.source} slots={{ pid: <ProjectId pid={row.project_id} /> }} />}
      />
    </div>
  );
}

// The card a disagreement row draws on the timeline or in the drawer: the info variant, with no keep action, since no
// answer or draft rests on it here; each side's "Open" link selects its tab.
export function cardFromRow(row: Record<string, any>, onOpenSide: (index: number, element: HTMLElement) => void): {
  sides: [CardSide, CardSide];
  props: { name: string; subject: string; rule: string; whatChanges?: string; keep: { other: string; otherAssertionId: string; leanAssertionId: string; target: null } | undefined };
} {
  const sides = (row.sides ?? []) as SideData[];
  const lean = sides.find((side) => side.leaned);
  const other = sides.find((side) => !side.leaned);
  const cardSides = sides.map((side, index) => ({
    title: sideTitle(side),
    titleText: sideTitle(side),
    meta: sideMeta(side),
    leaned: side.leaned,
    assertionId: side.assertion_id ?? undefined,
    said: <SideSaid side={side} />,
    context: sideContext(side, row.period?.event ?? null, row.period?.start ?? null),
    open: { label: sideOpen(side), href: evidenceHref(side.evidence_id), onOpen: (element: HTMLElement) => onOpenSide(index + 1, element) },
  })) as [CardSide, CardSide];
  return {
    sides: cardSides,
    props: {
      name: copy.disagreement.groupName(copy.badge.sourcesDiffer, sideShort(sides[0]), sideShort(sides[1])),
      subject: subjectOf(row.attribute, row.period?.event ?? null),
      rule: ruleSentence(row.rule_id, sides),
      whatChanges: whatChanges(sides, row.if_you_keep),
      keep: lean && other && lean.assertion_id && other.assertion_id ? { other: sideShort(other), otherAssertionId: other.assertion_id, leanAssertionId: lean.assertion_id, target: null } : undefined,
    },
  };
}

// The disagreement view (section 6.1): a switcher, "Reports in this disagreement", whose first tab shows the card and
// whose other tabs show each side's passage. Selection follows focus.
function DisagreementView({ evidence, renderSide }: { evidence: EvidenceEvent; renderSide: (evidenceId: string) => ReactNode }) {
  const row = evidence.row;
  const [tab, setTab] = useState(0);
  const panelId = useId();
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const sides = (row.sides ?? []) as SideData[];
  // A side's tab reads "ICR ¶78", and a screen reader hears "ICR paragraph 78", as the source switcher does.
  const tabs: ReactNode[] = [
    words.disagreement.both,
    ...sides.map((side) => {
      const short = sideShort({ ...side, paragraph_numbered: false });
      const paragraph = side.paragraph_numbered ? side.paragraph : null;
      if (!paragraph) return short;
      return (
        <span>
          {short}{" "}
          <span aria-hidden="true">{copy.evidence.paraMark}</span>
          <span className="sr-only">{copy.evidence.paraSpoken}</span>
          {paragraph}
        </span>
      );
    }),
  ];
  const choose = (index: number) => {
    setTab(index);
    refs.current[index]?.focus();
  };
  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    const moves: Record<string, number> = { ArrowRight: tab + 1, ArrowLeft: tab - 1, Home: 0, End: tabs.length - 1 };
    if (!(event.key in moves)) return;
    event.preventDefault();
    choose((moves[event.key] + tabs.length) % tabs.length);
  };
  const { sides: cardSides, props } = cardFromRow(row, (index) => setTab(index));
  return (
    <div data-disagreement-view className="flex flex-col gap-4">
      <div role="tablist" aria-label={words.disagreement.switcher} className="flex flex-wrap gap-2">
        {tabs.map((one, index) => (
          <button
            key={index}
            ref={(element) => {
              refs.current[index] = element;
            }}
            type="button"
            role="tab"
            id={`${panelId}-tab-${index}`}
            aria-selected={index === tab}
            aria-controls={panelId}
            tabIndex={index === tab ? 0 : -1}
            onClick={() => choose(index)}
            onKeyDown={onKeyDown}
            className={cx(
              "inline-flex min-h-8 items-center rounded-pill border border-line-strong px-3 py-1 text-left text-small text-ink transition-paint duration-150",
              index === tab ? "bg-tint shadow-[inset_0_0_0_1px_var(--color-primary)]" : "bg-surface hover:bg-tint-hover",
            )}
          >
            {one}
          </button>
        ))}
      </div>
      <div id={panelId} role="tabpanel" aria-labelledby={`${panelId}-tab-${tab}`} className="flex flex-col gap-4">
        {tab === 0 ? <DisagreementCard warning={false} level={3} sides={cardSides} {...props} /> : renderSide(sides[tab - 1].evidence_id)}
      </div>
    </div>
  );
}

export function TimelineView({ evidence, renderSide }: { evidence: EvidenceEvent; renderSide: (evidenceId: string) => ReactNode }) {
  if (evidence.kind === "document") return <DocumentView evidence={evidence} />;
  if (evidence.kind === "ratings") return <RatingsView evidence={evidence} />;
  if (evidence.kind === "contracts") return <ContractsView evidence={evidence} />;
  if (evidence.kind === "disagreement") return <DisagreementView evidence={evidence} renderSide={renderSide} />;
  return null;
}

export function UnknownDisagreement() {
  return <Alert state="neutral">{words.disagreement.unknown}</Alert>;
}
