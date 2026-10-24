// The gallery's pages: one per group of components, each listing the states it can be in.
// Hover and keyboard focus are real interactions, so the capture command (web/capture)
// makes them happen and photographs them; everything else is shown here as it renders.
import { useState, type ReactNode } from "react";
import {
  Check,
  ChevronDown,
  Circle,
  CircleDashed,
  CircleX,
  FileDown,
  Info,
  LoaderCircle,
  Menu,
  Search,
  TriangleAlert,
  X,
  type LucideIcon,
} from "lucide-react";
import { Answer } from "../components/Answer";
import { Breadcrumb } from "../components/Breadcrumb";
import { CheckPill } from "../components/CheckPill";
import { Fill } from "../components/Fill";
import { checkPill, PlanCheck, PlanCheckHeader, PlanCheckSkeleton, planSubtitle, type CheckedPlan } from "../components/PlanCheck";
import { Alert } from "../components/Alert";
import { FreshnessStamp, OneBox, type Freshness } from "../components/BoxBand";
import { Button } from "../components/Button";
import { Card, EmptyState } from "../components/Card";
import { CheckLine, CoverageLine, RemovedBox } from "../components/Checks";
import { CitationMarker } from "../components/CitationMarker";
import { Document, type Passage } from "../components/Document";
import { Num, type NumValue } from "../components/Num";
import { PageHeader, WithIds } from "../components/PageHeader";
import { Skeleton, SkeletonText } from "../components/Skeleton";
import { DocumentSource } from "../components/Source";
import { StatusBadge, type BadgeKind } from "../components/StatusBadge";
import { Steps, type Step } from "../components/Steps";
import { Table, type Column, type Row } from "../components/Table";
import { Tabs } from "../components/Tabs";
import { DefinitionWindow, Term } from "../components/Term";
import { TextLink } from "../components/TextLink";
import type { Section } from "../components/TopNav";
import { FactsSkeleton, PackageFactsList, PackageHeader } from "../components/PackageFacts";
import { PastRange } from "../components/PastRange";
import { copy } from "../copy";
import type { Comparable, ComparablesResult, PackageFacts } from "../lib/api";
import { formatDate } from "../lib/format";
import { galleryCopy } from "./copy";

// ── The package workspace's samples (ticket 12) ──────────────────────────
// Made-up comparables in find_comparables' shape, built from the gallery copy's months so that every
// count in a sample agrees with its rows. The packages still open ran longest in every sample, so each
// quantile is a rank among the signed ones, as Kaplan-Meier gives it then.
const pr = galleryCopy.pastRange;
const DAY_MS = 86_400_000;
const isoAfter = (iso: string, days: number) => new Date(Date.parse(`${iso}T00:00:00Z`) + days * DAY_MS).toISOString().slice(0, 10);

const samplePackage = pr.package as PackageFacts;

function sampleResult(signed: readonly number[], open: readonly number[], options: { plan?: boolean; abstain?: boolean } = {}): ComparablesResult {
  const total = signed.length + open.length;
  const rows: Comparable[] = [...signed.map((months) => ({ months, still: false })), ...open.map((months) => ({ months, still: true }))].map(
    ({ months, still }, index) => {
      const notice = isoAfter("2021-01-04", index * 9);
      const days = Math.round(months * 30.4375);
      return {
        evidence_id: `sample-${index}`,
        public_from: notice,
        source: { project_id: galleryCopy.sample.pcode, notice_id: `OP-SAMPLE-${index}`, contract_id: null, award_notice_id: null, signed_in: still ? null : "contract awards" },
        step_reference: `${pr.referencePrefix}${String(10 + index).padStart(2, "0")}${pr.referenceSuffix}`,
        project_id: galleryCopy.sample.pcode,
        country_code: "KE",
        country_name: pr.country,
        notice_id: `OP-SAMPLE-${index}`,
        notice_date: notice,
        signed_on: still ? null : isoAfter(notice, days),
        still_open: still,
        days,
        months: Math.round(months * 10) / 10,
        rank: 0,
      };
    },
  );
  rows.sort((a, b) => a.months - b.months || a.step_reference.localeCompare(b.step_reference));
  rows.forEach((row, index) => (row.rank = index + 1));
  const done = rows.filter((row) => !row.still_open).map((row) => row.months);
  const at = (share: number) => {
    const rank = Math.ceil(total * share);
    return rank <= done.length ? done[rank - 1] : null;
  };
  const within = done.filter((months) => months <= pr.planMonths).length;
  const longest = Math.max(...rows.map((row) => row.months));
  return {
    tool: "find_comparables",
    as_of: galleryCopy.sampleDate,
    view: "staff",
    rows,
    coverage: {
      matched: total + 3,
      used: total,
      not_used: [
        { reason: "no_step_reference", count: 2, evidence_ids: ["sample-a", "sample-b"] },
        { reason: "no_notice", count: 1, evidence_ids: ["sample-c"] },
      ],
    },
    abstention: options.abstain ? { reason: "too_few_comparables", count: total, min_comparables: 20 } : null,
    package: samplePackage,
    criteria: {
      method: pr.method,
      category: pr.category,
      market_approach: null,
      review_type: null,
      country: "KE",
      country_name: pr.country,
      notice_from: "2019-07-01",
      notice_to: "2026-10-09",
      size_from_usd: null,
      size_to_usd: null,
      from_package: ["method", "category", "country", "notice_to"],
    },
    counts: { comparables: total, signed: done.length, still_open: open.length, canceled: 0, canceled_as_still_open: false },
    past_range: options.abstain ? null : { q25: at(1 / 4), q50: at(1 / 2), q75: at(3 / 4), q80: at(4 / 5) },
    plan:
      options.plan === false
        ? null
        : {
            days: 122,
            months: pr.planMonths,
            planned_notice_on: pr.plannedNotice,
            planned_signing_on: pr.plannedSigning,
            plan_date: "2026-10-09",
            within,
            in10: options.abstain ? null : Math.round((within * 10) / total),
          },
    // Every sample's share falls between 1 and 9 in 10, so the tool's words for it are "about".
    frequencies: options.abstain
      ? null
      : { q80: [8, 10], plan: options.plan === false ? null : { words: "about", states: [Math.round((within * 10) / total), 10] } },
    quantile_dots:
      total > 60 && !options.abstain
        ? Array.from({ length: 20 }, (_, index) => {
            const reached = at((2 * index + 1) / 40);
            return { k: index + 1, days: 0, months: reached ?? longest, reached: reached !== null };
          })
        : null,
    thresholds: { min_comparables: 20, quantile_dots_above: 60, quantile_dots: 20, max_plan_months: 60, canceled_as_still_open: false },
    sources: pr.sources.map((name, index) => ({ key: `sample-${index}`, dataset_name: name })),
    records_through: "2026-10-13",
  };
}

const rangeReady = sampleResult(pr.signedMonths, pr.openMonths);
const rangeNoPlan = sampleResult(pr.signedMonths, pr.openMonths, { plan: false });
const rangeWide = sampleResult(
  Array.from({ length: pr.wideSigned }, (_, index) => 1.5 + index * 0.15),
  pr.wideOpen,
);
const rangeNarrow = sampleResult(pr.signedMonths.slice(0, pr.narrowCount), [], { abstain: true });
const rangeEmpty = (abstention: ComparablesResult["abstention"], matched: number): ComparablesResult => ({
  ...rangeReady,
  rows: [],
  counts: null,
  past_range: null,
  plan: null,
  frequencies: null,
  abstention,
  coverage: matched
    ? { matched, used: 0, not_used: [{ reason: "no_notice", count: matched, evidence_ids: [] }] }
    : { matched: 0, used: 0, not_used: [] },
});

const s = galleryCopy.states;
const t = galleryCopy.sections;
const sample = galleryCopy.sample;
const reference = galleryCopy.reference;

export type GalleryPage = {
  slug: keyof typeof galleryCopy.pages;
  // The tab the frame selects on this page.
  current?: Section;
  // A component that sizes itself to the page's 12 columns, as the plan check's table does, takes
  // them all here too, so the gallery shows it as it ships.
  wide?: boolean;
  sections: { id: string; title: string; body: ReactNode }[];
};

function Inline({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-4">{children}</div>;
}

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

function Panel({ children }: { children: ReactNode }) {
  return <div className="rounded-md border border-line bg-surface p-4 md:p-6">{children}</div>;
}

function SampleBox({ text }: { text: string }) {
  const [value, setValue] = useState(text);
  return <OneBox value={value} onChange={setValue} below={copy.box.notReady} shortcut={false} />;
}

const date = (iso: string, style: "short" | "sentence" | "table" = "sentence") =>
  formatDate(iso, { style, today: galleryCopy.sampleDate });

const STAMPS: [string, Freshness][] = [
  [s.loading, { status: "loading" }],
  [s.slow, { status: "loading", slow: true }],
  [s.ready, { status: "ready", date: date(galleryCopy.sampleDate, "short") }],
  [s.empty, { status: "empty" }],
  [s.error, { status: "error" }],
];

// Each answer sample's steps, done or with the last one running.
const steps = (list: Omit<Step, "state">[], running = false): Step[] =>
  list.map((step, index) => ({ ...step, state: running && index === list.length - 1 ? "running" : "done" }));
const ST = sample.steps;

// The marker's preview ends with the source line an evidence card ends with.
const preview = (
  <>
    <p>{sample.markerPreview}</p>
    <DocumentSource className="mt-2" docType={sample.docType} pcode={sample.pcode} date={date(sample.docDate)} para={54} page={23} />
  </>
);

const markers = (
  <>
    {sample.sentenceBefore}
    <CitationMarker n={1} source={sample.markerSource} href="#source-1" preview={preview} />{" "}
    {sample.sentenceAfter}
    <CitationMarker n={2} source={sample.markerSecond} href="#source-2" opened />
  </>
);

// The Answer page's sentences, with the same two sources as the Citations page.
const answerSentences = (
  <>
    {sample.answerSentences[0]}
    <CitationMarker n={1} source={sample.markerSource} href="#source-1" preview={preview} />{" "}
    {sample.answerSentences[1]}
    <CitationMarker n={2} source={sample.markerSecond} href="#source-2" />
  </>
);

// The character range of a phrase in a passage, as the evidence event will carry it.
const range = (text: string, phrase: string): [number, number] => {
  const start = text.indexOf(phrase);
  return [start, start + phrase.length];
};

const passage: Passage = {
  docType: sample.docType,
  pcode: sample.pcode,
  date: date(sample.docDate),
  para: 54,
  page: 23,
  text: sample.passage,
  highlights: [range(sample.passage, sample.passageMatch)],
  pdfHref: "#pdf",
};

const mono = (text: string) => <span className="font-mono">{text}</span>;

// The Plan check page's sample, from the gallery's copy, and its partial check: one activity whose
// plan gives no planned date gets a data note, and the counts say so.
const pc = sample.planCheck;
const planSample = pc.result as unknown as CheckedPlan;
const partialSample: CheckedPlan = {
  ...planSample,
  counts: { ...planSample.counts, ...pc.partialCounts },
  rows: planSample.rows.map((row) =>
    row.activity_reference_no === pc.partialRef ? { ...row, marks: [pc.partialMark as unknown as CheckedPlan["rows"][number]["marks"][number]] } : row,
  ),
};
const planTrail = [
  { text: copy.breadcrumb.projects, href: "#projects" },
  { text: <Fill template={copy.breadcrumb.project} slots={{ name: pc.crumbProject, pid: mono(planSample.plan.project_id) }} />, href: "#project" },
  { text: copy.breadcrumb.procurement, href: "#procurement" },
  { text: pc.crumbPlan },
];

// The Table page's sample: four activities, three of them late, as its title says.
const columns: Column[] = sample.tableHeaders.map((header, index) => ({
  key: `c${index}`,
  header,
  numeric: index >= 2,
  width: ["w-2/5", "w-3/10", "w-1/5", "w-1/10"][index],
}));
const rows: Row[] = sample.tableRows.map(([reference, method, amount, late]) => ({
  id: reference,
  cells: {
    c0: mono(reference),
    c1: method,
    c2: <Num value={Number(amount)} options={{ compact: false, decimals: 2 }} />,
    c3: <Num value={Number(late)} />,
  },
}));
const tableProps = {
  title: sample.tableTitle,
  count: { noun: sample.tableNoun, total: rows.length },
  columns,
  rowHeader: "c0",
  source: sample.tableSource,
};

// The abstention's sample: the 12 comparable packages its sentence names, with one number
// each, so its check line counts 12 numbers.
const comparableColumns: Column[] = sample.abstentionHeaders.map((header, index) => ({
  key: `c${index}`,
  header,
  numeric: index === 2,
  width: ["w-1/2", "w-3/10", "w-1/5"][index],
}));
const comparableRows: Row[] = sample.abstentionRows.map(([reference, method, months]) => ({
  id: reference,
  cells: { c0: mono(reference), c1: method, c2: <Num value={Number(months)} options={{ decimals: 1 }} /> },
}));

// The Numbers page's reference tables: the value a tool sent, the rule, and what Num shows.
// The value a tool sent is in Open Sans with tabular numerals, because DESIGN.md section 3
// keeps Roboto Mono for IDs and codes.
const h = reference.headers;
const RATIOS: [number, number, "sentence" | "table"][] = [
  [6, 12, "sentence"],
  [31, 37, "sentence"],
  [42, 50, "sentence"],
  [93, 118, "table"],
  [1, 300, "sentence"],
];
const ratioColumns: Column[] = [
  { key: "part", header: h.part, numeric: true, width: "w-1/10" },
  { key: "whole", header: h.whole, numeric: true, width: "w-1/10" },
  { key: "style", header: h.style, width: "w-1/10" },
  { key: "rule", header: h.rule },
  { key: "shows", header: h.shows, numeric: true, width: "w-1/4" },
];
const ratioRows: Row[] = RATIOS.map(([part, whole, style], index) => ({
  id: `${part}-${whole}-${style}`,
  cells: {
    part: String(part),
    whole: String(whole),
    style: style === "table" ? reference.table : reference.sentence,
    rule: reference.ratios.rules[index],
    shows: <Num part={part} whole={whole} style={style} />,
  },
}));

// Each row is named by what Num shows, as in the ratio table, so a card below 768 px leads
// with the formatted number and not the raw value.
const valueColumns: Column[] = [
  { key: "value", header: h.value, numeric: true, width: "w-1/5" },
  { key: "rule", header: h.rule },
  { key: "shows", header: h.shows, numeric: true, width: "w-1/5" },
];
const valueRows = (values: { sent: string; num: NumValue }[], rules: readonly string[]): Row[] =>
  values.map(({ sent, num }, index) => ({
    id: `${sent}-${index}`,
    cells: { value: sent, rule: rules[index], shows: <Num {...num} /> },
  }));
const FORMATS: { sent: string; num: NumValue }[] = [
  ...[1234, 12500, 295689, 1250000, 2500000000, 0.456, 45.67, 456.7].map((value) => ({
    sent: String(value),
    num: { value } as NumValue,
  })),
  // A STEP amount, as Table's sample shows it: in STEP's form, cents included.
  { sent: "2450000.00", num: { value: 2450000, options: { compact: false, decimals: 2 } } as NumValue },
];
const COUNTS: { sent: string; num: NumValue }[] = [
  { sent: "7", num: { count: 7 } },
  { sent: "14", num: { count: 14 } },
  { sent: "2024", num: { year: 2024 } },
  { sent: "2024-03-04", num: { date: "2024-03-04", style: "sentence" } },
  { sent: "2024-03-04", num: { date: "2024-03-04", style: "table" } },
];

const BADGES: [string, BadgeKind[]][] = [
  [t.signals, ["needs-a-look", "watch", "no-signals"]],
  [t.readiness, ["partial", "gap"]],
  [t.planChecks, ["data-note"]],
];

const ICONS: Record<string, LucideIcon> = {
  search: Search,
  menu: Menu,
  x: X,
  "chevron-down": ChevronDown,
  "circle-dashed": CircleDashed,
  circle: Circle,
  "circle-x": CircleX,
  info: Info,
  "triangle-alert": TriangleAlert,
  check: Check,
  "loader-circle": LoaderCircle,
  "file-down": FileDown,
};

export const PAGES: GalleryPage[] = [
  {
    slug: "navigation",
    current: "projects",
    sections: [
      {
        id: "bar",
        title: t.bar,
        body: <p className="max-w-prose text-body text-ink">{galleryCopy.notes.bar}</p>,
      },
      {
        id: "box",
        title: t.box,
        body: (
          <div className="flex flex-col gap-6">
            <Labeled label={s.withText}>
              <div className="max-w-prose pb-16">
                <SampleBox text={sample.pcode} />
              </div>
            </Labeled>
          </div>
        ),
      },
      {
        id: "stamp",
        title: t.stamp,
        body: (
          <div className="flex flex-col gap-4">
            {STAMPS.map(([label, freshness]) => (
              <Labeled key={label} label={label}>
                <div className="max-w-[20rem] rounded-md border border-line bg-surface px-3 py-1 md:[&>div]:justify-start">
                  <FreshnessStamp freshness={freshness} />
                </div>
              </Labeled>
            ))}
          </div>
        ),
      },
    ],
  },
  {
    // The app's pages in 06 (web/src/RoutePage.tsx): each route's own states are captured from
    // the production build (web/capture/shots.ts); these are the parts every page shares.
    slug: "pages",
    sections: [
      {
        id: "header",
        title: t.header,
        body: (
          <div className="max-w-[54rem]">
            <PageHeader
              level={2}
              title={<WithIds template={copy.pages.activity.title} values={{ stepRef: sample.tableRows[0][0] }} />}
              purpose={copy.pages.activity.purpose}
            />
            <EmptyState
              level={3}
              className="mt-6 lg:mt-8"
              title={<WithIds whole template={copy.pages.activity.emptyTitle} values={{ stepRef: sample.tableRows[0][0] }} />}
              body={copy.pages.activity.emptyBody}
              link={{ href: "#project", text: <WithIds template={copy.pages.activity.link} values={{ pid: sample.pcode }} /> }}
            />
          </div>
        ),
      },
      {
        id: "not-found",
        title: t.notFound,
        body: (
          <div className="max-w-[54rem]">
            <PageHeader level={2} title={copy.pages.notFound.title} purpose={copy.pages.notFound.purpose} />
            <p className="mt-4 text-body">
              <TextLink href="#home">{copy.pages.notFound.link}</TextLink>
            </p>
          </div>
        ),
      },
      {
        id: "page-alerts",
        title: t.pageAlerts,
        body: (
          <div className="flex max-w-[54rem] flex-col gap-2">
            <Alert state="error">{copy.alerts.noAccess}</Alert>
            <Alert state="error">{copy.alerts.noIdentity}</Alert>
            <Alert state="info">{copy.alerts.viewPiu}</Alert>
            <Alert state="info">{copy.alerts.viewPublic}</Alert>
            <Alert state="info">{copy.alerts.viewUnknown}</Alert>
            <Alert state="info">{copy.alerts.asOf(date(galleryCopy.sampleDate))}</Alert>
            <Alert state="info">{copy.alerts.asOfUnreadable}</Alert>
          </div>
        ),
      },
    ],
  },
  {
    slug: "buttons",
    sections: [
      {
        id: "variants",
        title: t.variants,
        body: (
          <Inline>
            <Button variant="primary">{sample.primary}</Button>
            <Button variant="secondary">{sample.secondary}</Button>
            <Button variant="ghost">{sample.ghost}</Button>
          </Inline>
        ),
      },
      {
        // DESIGN.md section 5: a ghost button in a column of text sits flush, so its icon lines
        // up with the text and its fill and focus ring stay inside the card.
        id: "flush",
        title: t.flush,
        body: (
          <Panel>
            <p className="max-w-prose text-body">{sample.flushText}</p>
            <Button variant="ghost" flush icon={ChevronDown} className="mt-2">
              {sample.ghost}
            </Button>
          </Panel>
        ),
      },
      {
        // DESIGN.md section 5: on the page background a ghost button hovers to tint.
        id: "on-page",
        title: t.onPage,
        body: (
          <Button variant="ghost" flush onPage icon={ChevronDown}>
            {sample.ghost}
          </Button>
        ),
      },
      {
        id: "with-icon",
        title: s.withIcon,
        body: (
          <Inline>
            <Button variant="primary" icon={Check}>
              {sample.primary}
            </Button>
            <Button variant="secondary" icon={FileDown}>
              {sample.secondary}
            </Button>
            <Button variant="ghost" icon={ChevronDown}>
              {sample.ghost}
            </Button>
            <Button variant="ghost" icon={X} iconOnly aria-label={sample.icon}>
              {sample.icon}
            </Button>
          </Inline>
        ),
      },
      {
        id: "disabled",
        title: s.disabled,
        body: (
          <Inline>
            <Button variant="primary" disabled>
              {sample.primary}
            </Button>
            <Button variant="secondary" disabled>
              {sample.secondary}
            </Button>
            <Button variant="ghost" disabled>
              {sample.ghost}
            </Button>
          </Inline>
        ),
      },
      {
        id: "loading",
        title: s.loading,
        body: (
          <Inline>
            <Button variant="primary" loading>
              {sample.primary}
            </Button>
            <Button variant="secondary" loading>
              {sample.secondary}
            </Button>
            <Button variant="ghost" loading>
              {sample.ghost}
            </Button>
          </Inline>
        ),
      },
    ],
  },
  {
    slug: "links",
    sections: [
      {
        id: "text-link",
        title: t.textLink,
        body: (
          <p className="text-body">
            <TextLink href="#data">{sample.textLink}</TextLink>
          </p>
        ),
      },
      {
        id: "tabs",
        title: t.tabs,
        body: (
          <Panel>
            <Tabs
              label={sample.tabsLabel}
              tabs={sample.tabs.map((label, index) => ({ key: label, label, href: `#tab-${index}`, current: index === 1 }))}
            />
          </Panel>
        ),
      },
      {
        id: "tabs-later",
        title: t.tabsLater,
        body: (
          <Panel>
            <Tabs
              label={sample.tabsLabel}
              tabs={sample.tabs.map((label, index) => ({ key: label, label, href: `#tab-${index}`, current: index === 3 }))}
            />
          </Panel>
        ),
      },
    ],
  },
  {
    slug: "cards",
    sections: [
      {
        id: "card",
        title: t.card,
        body: (
          <Card title={sample.cardTitle} source={sample.cardSource}>
            {sample.cardBody}
          </Card>
        ),
      },
      {
        id: "empty-link",
        title: s.withLink,
        body: (
          <EmptyState
            level={3}
            title={sample.emptyTitle}
            body={sample.emptyBody}
            link={{ href: "#data", text: sample.emptyLink }}
          />
        ),
      },
      {
        id: "empty-plain",
        title: s.withoutLink,
        body: <EmptyState level={3} title={sample.emptyTitle} body={sample.emptyBody} />,
      },
    ],
  },
  {
    slug: "alerts",
    sections: [
      {
        id: "states",
        title: t.states,
        body: (
          <div className="flex max-w-prose flex-col gap-4">
            <Alert state="info">{sample.info}</Alert>
            <Alert state="success">{sample.success}</Alert>
            <Alert state="warning">{sample.warning}</Alert>
            <Alert state="error">{sample.error}</Alert>
            <Alert state="neutral">{sample.neutral}</Alert>
            <Alert state="error" action={<Button variant="secondary">{copy.answer.tryAgain}</Button>}>
              {sample.answerError}
            </Alert>
          </div>
        ),
      },
    ],
  },
  {
    slug: "badges",
    sections: BADGES.map(([title, kinds]) => ({
      id: title,
      title,
      body: (
        <Inline>
          {kinds.map((kind) => (
            <StatusBadge key={kind} kind={kind} />
          ))}
        </Inline>
      ),
    })),
  },
  {
    slug: "numbers",
    sections: [
      {
        id: "ratios",
        title: t.ratios,
        body: (
          <Table
            level={3}
            title={reference.ratios.title}
            count={{ noun: reference.ratios.noun, total: ratioRows.length }}
            columns={ratioColumns}
            rowHeader="shows"
            state={{ status: "ready", rows: ratioRows }}
            source={reference.source}
          />
        ),
      },
      {
        id: "formats",
        title: t.formats,
        body: (
          <Table
            level={3}
            title={reference.formats.title}
            count={{ noun: reference.formats.noun, total: FORMATS.length }}
            columns={valueColumns}
            rowHeader="shows"
            state={{ status: "ready", rows: valueRows(FORMATS, reference.formats.rules) }}
            source={reference.source}
          />
        ),
      },
      {
        id: "counts",
        title: t.counts,
        body: (
          <Table
            level={3}
            title={reference.counts.title}
            count={{ noun: reference.counts.noun, total: COUNTS.length }}
            columns={valueColumns}
            rowHeader="shows"
            state={{ status: "ready", rows: valueRows(COUNTS, reference.counts.rules) }}
            source={reference.source}
          />
        ),
      },
      {
        id: "checkable",
        title: t.checkable,
        body: (
          <p className="text-body">
            <Num part={31} whole={37} check={{ tooltip: sample.numTooltip }} />
          </p>
        ),
      },
      {
        id: "terms",
        title: t.terms,
        body: (
          <Inline>
            <Term term={sample.term} />
            <DefinitionWindow
              title={sample.measureTitle}
              rows={[
                { label: sample.measureRows[0], value: <Num value={37} /> },
                { label: sample.measureRows[1], value: <Num value={52} /> },
                { label: sample.measureRows[2], value: <Num date={galleryCopy.sampleDate} style="table" /> },
              ]}
              label={sample.measureTitle}
            >
              {sample.measureBody}
            </DefinitionWindow>
          </Inline>
        ),
      },
    ],
  },
  {
    slug: "citations",
    sections: [
      {
        id: "markers",
        title: t.markers,
        body: (
          <div className="flex flex-col gap-4">
            <p className="max-w-prose text-body">{markers}</p>
            {/* A marker keeps 4 px of space on each side for a sentence. Here it stands under its
                label, so the wrapper takes the left 4 px back and the two share a left edge. */}
            <Inline>
              <Labeled label={s.default}>
                <span className="-ml-1"><CitationMarker n={1} source={sample.markerSource} href="#source-1" /></span>
              </Labeled>
              <Labeled label={s.opened}>
                <span className="-ml-1"><CitationMarker n={2} source={sample.markerSecond} href="#source-2" opened /></span>
              </Labeled>
              <Labeled label={s.active}>
                <span className="-ml-1"><CitationMarker n={3} source={sample.markerSource} href="#source-3" active /></span>
              </Labeled>
            </Inline>
          </div>
        ),
      },
      {
        id: "check-line",
        title: t.checkLine,
        body: (
          <div className="flex max-w-prose flex-col gap-2">
            <CheckLine numbers={{ matched: 23, total: 23 }} quotes={{ found: 14, total: 14 }} notChecked={["comparables"]} />
            <CheckLine numbers={{ matched: 1, total: 1 }} notChecked={["sentences"]} />
            <CheckLine quotes={{ found: 14, total: 14 }} notChecked={["sentences", "passages"]} />
            <CheckLine notChecked={["sentences"]} />
          </div>
        ),
      },
      {
        id: "coverage",
        title: t.coverage,
        body: (
          <div className="flex max-w-prose flex-col gap-4">
            <Labeled label={s.withGap}>
              <CoverageLine part={37} whole={52} noun={sample.coverageNoun} gap={sample.coverageGap} href="#data" />
            </Labeled>
            <Labeled label={s.withoutGap}>
              <CoverageLine part={52} whole={52} noun={sample.coverageNoun} href="#data" />
            </Labeled>
          </div>
        ),
      },
      {
        id: "removed",
        title: t.removed,
        body: (
          <div className="flex max-w-prose flex-col gap-4">
            <RemovedBox removed={[]} />
            <RemovedBox removed={[sample.removed[0]]} />
            <RemovedBox removed={[...sample.removed]} names={[...sample.removedNames]} />
            <RemovedBox removed={[...sample.removed]} all />
          </div>
        ),
      },
    ],
  },
  {
    slug: "answer",
    sections: [
      { id: "steps", title: t.steps, body: <Panel><Steps steps={steps([ST.read, ST.searchDocuments, ST.write], true)} /></Panel> },
      {
        id: "streaming",
        title: s.streaming,
        body: <Panel><Answer state={{ status: "streaming", steps: steps([ST.read, ST.searchDocuments], true), stillWorking: true }} /></Panel>,
      },
      {
        // Three sentences written: two kept, with three numbers between them (five, three and
        // four), and one removed. A test in gallery-components.spec.ts checks these counts.
        id: "ready",
        title: s.ready,
        body: (
          <Panel>
            <Answer
              state={{
                status: "ready",
                steps: steps([ST.read, ST.searchDocuments, ST.write, ST.verify]),
                runId: sample.runId,
                sentences: answerSentences,
                checks: { numbers: { matched: 3, total: 3 }, notChecked: ["sentences"], removed: [sample.removed[0]] },
              }}
            />
          </Panel>
        ),
      },
      {
        // 12 comparable packages in the sentence, 12 rows in the table, 12 numbers checked.
        id: "abstained",
        title: s.abstained,
        body: (
          <Panel>
            <Answer
              state={{
                status: "abstained",
                steps: steps([ST.read, ST.searchComparables, ST.verifyComparables]),
                runId: sample.runId,
                sentence: sample.abstention,
                rows: (
                  <Table
                    level={4}
                    title={sample.abstentionTitle}
                    count={{ noun: sample.abstentionNoun, total: comparableRows.length }}
                    columns={comparableColumns}
                    rowHeader="c0"
                    state={{ status: "ready", rows: comparableRows }}
                    source={sample.tableSource}
                  />
                ),
                checks: { numbers: { matched: 12, total: 12 }, notChecked: ["sentences", "comparables"], removed: [] },
              }}
            />
          </Panel>
        ),
      },
      {
        id: "empty",
        title: s.empty,
        body: (
          <Panel>
            <Answer
              state={{
                status: "empty",
                steps: steps([ST.read, ST.searchNothing]),
                runId: sample.runId,
                message: (
                  <>
                    {sample.emptyLead} <TextLink href="#data">{sample.emptyLinkText}</TextLink>
                    {sample.emptyTail}
                  </>
                ),
              }}
            />
          </Panel>
        ),
      },
      {
        id: "refused",
        title: s.refused,
        body: (
          <Panel>
            <Answer
              state={{
                status: "refused",
                steps: steps([ST.read]),
                runId: sample.runId,
                message: sample.refusal,
                note: (
                  <>
                    <TextLink href="#how">{sample.refusalLinkText}</TextLink>
                    {sample.refusalTail}
                  </>
                ),
              }}
            />
          </Panel>
        ),
      },
      {
        id: "error",
        title: s.error,
        body: (
          <Panel>
            <Answer state={{ status: "error", steps: steps([ST.read, ST.searchDocuments]), message: sample.answerError, onRetry: () => {} }} />
          </Panel>
        ),
      },
    ],
  },
  {
    slug: "document",
    sections: [
      { id: "ready", title: s.ready, body: <Panel><Document state={{ status: "ready", passage }} /></Panel> },
      {
        id: "french",
        title: s.french,
        body: (
          <Panel>
            <Document
              state={{
                status: "ready",
                passage: {
                  ...passage,
                  text: sample.passageFrench,
                  lang: "fr",
                  highlights: [range(sample.passageFrench, sample.passageFrenchMatch)],
                },
              }}
            />
          </Panel>
        ),
      },
      { id: "loading", title: s.loading, body: <Panel><Document state={{ status: "loading" }} /></Panel> },
      { id: "failed", title: s.error, body: <Document state={{ status: "failed", onRetry: () => {} }} /> },
      { id: "missing", title: s.missing, body: <Document state={{ status: "missing" }} /> },
    ],
  },
  {
    slug: "table",
    sections: [
      { id: "ready", title: s.ready, body: <Table {...tableProps} state={{ status: "ready", rows }} /> },
      { id: "loading", title: s.loading, body: <Table {...tableProps} state={{ status: "loading", rows: rows.length }} /> },
      {
        // Ticket 10's plan check needs 880 px for its columns, so its rows become cards below 1024 px.
        id: "cards-below-lg",
        title: t.cardsBelowLg,
        body: <Table {...tableProps} cardsBelow="lg" state={{ status: "ready", rows }} />,
      },
      {
        id: "empty",
        title: s.empty,
        body: <Table {...tableProps} state={{ status: "empty", title: sample.tableEmptyTitle, body: sample.tableEmptyBody }} />,
      },
      {
        id: "error",
        title: s.error,
        body: <Table {...tableProps} state={{ status: "error", message: sample.tableError, onRetry: () => {} }} />,
      },
    ],
  },
  {
    slug: "skeleton",
    sections: [
      {
        id: "text",
        title: s.loading,
        body: (
          <Panel>
            <div className="max-w-prose">
              <Skeleton className="h-6 w-2/5" />
              <SkeletonText className="mt-4 text-body" widths={["w-full", "w-11/12", "w-3/5"]} />
            </div>
          </Panel>
        ),
      },
    ],
  },
  {
    // Ticket 10's Check a plan (web/src/components/PlanCheck.tsx). The page's own states, with
    // the real plan, are captured from the production build (web/capture/shots.ts).
    slug: "plan-check",
    current: "projects",
    wide: true,
    sections: [
      { id: "breadcrumb", title: t.breadcrumb, body: <Breadcrumb trail={planTrail} /> },
      {
        id: "pill",
        title: t.pill,
        body: (
          <Inline>
            {checkPill(planSample)}
            <CheckPill>{copy.checkPlan.pillPartial(String(pc.pillPartial.checked), String(pc.pillPartial.total))}</CheckPill>
          </Inline>
        ),
      },
      {
        id: "ready",
        title: t.planReady,
        body: (
          <>
            <PlanCheckHeader
              level={2}
              sticky={false}
              agency={planSample.plan.implementing_agency}
              plan={planSubtitle(planSample.plan.plan_date)}
              pill={checkPill(planSample)}
            />
            <PlanCheck result={planSample} />
          </>
        ),
      },
      { id: "open", title: t.planOpen, body: <PlanCheck result={planSample} defaultOpen /> },
      { id: "partial", title: t.planPartial, body: <PlanCheck result={partialSample} /> },
      { id: "loading", title: s.loading, body: <PlanCheckSkeleton /> },
      { id: "slow", title: s.slowTwo, body: <PlanCheckSkeleton slow /> },
    ],
  },
  {
    // Ticket 12's package workspace (web/src/components/PackageFacts.tsx, PastRange.tsx and
    // RangeChart.tsx). The page's own states, with the real comparables, are captured from the
    // production build (web/capture/shots.ts).
    slug: "past-range",
    current: "packages",
    sections: [
      {
        id: "header",
        title: t.packageHeader,
        body: (
          <>
            <PackageHeader level={2} sticky={false} title={pr.description} reference={<span className="font-mono font-medium">{pr.reference}</span>} />
            <p className="mt-4 max-w-prose text-body text-ink-muted">{copy.pages.package.purpose}</p>
            <div className="mt-4">
              <PackageFactsList pkg={samplePackage} />
            </div>
          </>
        ),
      },
      { id: "header-loading", title: s.loading, body: <FactsSkeleton /> },
      { id: "range", title: t.rangeReady, body: <PastRange state={{ status: "ready", result: rangeReady }} /> },
      { id: "no-plan", title: t.rangeNoPlan, body: <PastRange state={{ status: "ready", result: rangeNoPlan }} /> },
      { id: "dots", title: t.rangeDots, body: <PastRange state={{ status: "ready", result: rangeWide }} /> },
      { id: "abstained", title: t.rangeAbstained, body: <PastRange state={{ status: "ready", result: rangeNarrow }} /> },
      {
        id: "none",
        title: t.rangeNone,
        body: <PastRange state={{ status: "ready", result: rangeEmpty({ reason: "no_comparables", matched: 0 }, 0) }} />,
      },
      {
        id: "unmeasured",
        title: t.rangeUnmeasured,
        body: (
          <PastRange
            state={{ status: "ready", result: rangeEmpty({ reason: "none_measurable", matched: pr.unmeasured }, pr.unmeasured) }}
          />
        ),
      },
      {
        id: "not-measurable",
        title: t.rangeNotMeasurable,
        body: (
          <PastRange
            state={{
              status: "ready",
              result: rangeEmpty({ reason: "no_public_notice", field: pr.notMeasurableField, value: pr.notMeasurableValue }, 0),
            }}
          />
        ),
      },
      { id: "loading", title: s.loading, body: <PastRange state={{ status: "loading" }} /> },
      {
        id: "error",
        title: s.error,
        body: <PastRange state={{ status: "error", error: null, retrying: false, attempt: 0, onRetry: () => {} }} />,
      },
    ],
  },
  {
    slug: "icons",
    sections: [
      {
        id: "icons",
        title: s.default,
        body: (
          <ul className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {sample.iconNames.map((name) => {
              const Icon = ICONS[name];
              return (
                <li key={name} className="flex items-center gap-2 text-small text-ink">
                  <Icon aria-hidden="true" className="size-4 text-ink-muted" />
                  <span className="font-mono">{name}</span>
                </li>
              );
            })}
          </ul>
        ),
      },
    ],
  },
];
