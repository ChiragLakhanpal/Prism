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
import { Alert } from "../components/Alert";
import { FreshnessStamp, OneBox, type Freshness } from "../components/BoxBand";
import { Button } from "../components/Button";
import { Card, EmptyState } from "../components/Card";
import { CheckLine, CoverageLine, RemovedBox } from "../components/Checks";
import { CitationMarker } from "../components/CitationMarker";
import { Document, type Passage } from "../components/Document";
import { Num } from "../components/Num";
import { Skeleton, SkeletonText } from "../components/Skeleton";
import { StatusBadge, type BadgeKind } from "../components/StatusBadge";
import { Steps, type Step } from "../components/Steps";
import { Table, type Column, type Row } from "../components/Table";
import { Tabs } from "../components/Tabs";
import { DefinitionWindow, Term } from "../components/Term";
import { TextLink } from "../components/TextLink";
import type { Section } from "../components/TopNav";
import { copy } from "../copy";
import { formatDate } from "../lib/format";
import { galleryCopy } from "./copy";

const s = galleryCopy.states;
const t = galleryCopy.sections;
const sample = galleryCopy.sample;

export type GalleryPage = {
  slug: keyof typeof galleryCopy.pages;
  // The tab the frame selects on this page.
  current?: Section;
  sections: { id: string; title: string; body: ReactNode }[];
};

function Row({ children }: { children: ReactNode }) {
  return <div className="flex flex-wrap items-center gap-4">{children}</div>;
}

function Labelled({ label, children }: { label: string; children: ReactNode }) {
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

// The first `done` steps are done and the next one is running; later steps have not started.
const steps = (done: number): Step[] =>
  sample.steps.slice(0, done + 1).map((step, index) => ({ ...step, state: index < done ? "done" : "running" }));
const doneSteps: Step[] = sample.steps.map((step) => ({ ...step, state: "done" }));

const markers = (
  <>
    {sample.sentenceBefore}
    <CitationMarker n={1} source={sample.markerSource} href="#source-1" preview={sample.markerPreview} />{" "}
    {sample.sentenceAfter}
    <CitationMarker n={2} source={sample.markerSecond} href="#source-2" opened />
  </>
);

const checks = {
  numbers: { matched: 23, total: 23 },
  quotes: { found: 14, total: 14 },
  notChecked: ["sentences", "comparables"] as const,
  removed: [sample.removed[0]],
};

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

const columns: Column[] = sample.tableHeaders.map((header, index) => ({
  key: `c${index}`,
  header,
  numeric: index >= 2,
}));
const rows: Row[] = sample.tableRows.map(([reference, method, amount, late]) => ({
  id: reference,
  cells: {
    c0: <span className="font-mono">{reference}</span>,
    c1: method,
    c2: <Num value={Number(amount)} options={{ compact: false }} />,
    c3: <Num value={Number(late)} />,
  },
}));
const tableProps = {
  title: sample.tableTitle,
  columns,
  rowHeader: "c0",
  source: sample.tableSource,
};

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
            <Labelled label={s.withText}>
              <div className="max-w-prose pb-16">
                <SampleBox text={sample.pcode} />
              </div>
            </Labelled>
          </div>
        ),
      },
      {
        id: "stamp",
        title: t.stamp,
        body: (
          <div className="flex flex-col gap-4">
            {STAMPS.map(([label, freshness]) => (
              <Labelled key={label} label={label}>
                <div className="max-w-[20rem] rounded-md border border-line bg-surface px-3 py-1 md:[&>div]:justify-start">
                  <FreshnessStamp freshness={freshness} />
                </div>
              </Labelled>
            ))}
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
          <Row>
            <Button variant="primary">{sample.primary}</Button>
            <Button variant="secondary">{sample.secondary}</Button>
            <Button variant="ghost">{sample.ghost}</Button>
          </Row>
        ),
      },
      {
        id: "with-icon",
        title: s.withIcon,
        body: (
          <Row>
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
          </Row>
        ),
      },
      {
        id: "disabled",
        title: s.disabled,
        body: (
          <Row>
            <Button variant="primary" disabled>
              {sample.primary}
            </Button>
            <Button variant="secondary" disabled>
              {sample.secondary}
            </Button>
            <Button variant="ghost" disabled>
              {sample.ghost}
            </Button>
          </Row>
        ),
      },
      {
        id: "loading",
        title: s.loading,
        body: (
          <Row>
            <Button variant="primary" loading>
              {sample.primary}
            </Button>
            <Button variant="secondary" loading icon={FileDown}>
              {sample.secondary}
            </Button>
            <Button variant="ghost" loading>
              {sample.ghost}
            </Button>
          </Row>
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
    ],
  },
  {
    slug: "cards",
    sections: [
      { id: "card", title: t.card, body: <Card title={sample.cardTitle}>{sample.cardBody}</Card> },
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
        <Row>
          {kinds.map((kind) => (
            <StatusBadge key={kind} kind={kind} />
          ))}
        </Row>
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
          <ul className="flex flex-col gap-2 text-body">
            <li><Num part={6} whole={12} /></li>
            <li><Num part={31} whole={37} /></li>
            <li><Num part={42} whole={50} /></li>
            <li><Num part={93} whole={118} style="table" /></li>
          </ul>
        ),
      },
      {
        id: "formats",
        title: t.formats,
        body: (
          <ul className="grid max-w-[20rem] grid-cols-2 gap-2 text-body" data-numbers>
            {[1234, 12500, 295689, 1250000, 2500000000, 0.456, 45.67, 456.7].map((value) => (
              <li key={value} className="text-right">
                <Num value={value} />
              </li>
            ))}
          </ul>
        ),
      },
      {
        id: "counts",
        title: t.counts,
        body: (
          <ul className="flex flex-col gap-2 text-body">
            <li><Num count={7} />, <Num count={14} /></li>
            <li><Num year={2024} /></li>
            <li><Num date="2024-03-04" />, <Num date="2024-03-04" style="table" /></li>
          </ul>
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
          <Row>
            <Term term={sample.term} />
            <DefinitionWindow
              title={sample.measureTitle}
              rows={[
                { label: sample.measureRows[0], value: <Num value={37} /> },
                { label: sample.measureRows[1], value: <Num value={52} /> },
                { label: sample.measureRows[2], value: <Num date={galleryCopy.sampleDate} style="table" /> },
              ]}
              trigger={
                <button
                  type="button"
                  data-term
                  className="inline cursor-pointer py-0.5 underline decoration-line-strong decoration-dotted underline-offset-3 hover:decoration-solid"
                >
                  {sample.measureTitle}
                </button>
              }
            >
              {sample.measureBody}
            </DefinitionWindow>
          </Row>
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
            <Row>
              <Labelled label={s.default}>
                <span><CitationMarker n={1} source={sample.markerSource} href="#source-1" /></span>
              </Labelled>
              <Labelled label={s.opened}>
                <span><CitationMarker n={2} source={sample.markerSecond} href="#source-2" opened /></span>
              </Labelled>
              <Labelled label={s.active}>
                <span><CitationMarker n={3} source={sample.markerSource} href="#source-3" active /></span>
              </Labelled>
            </Row>
          </div>
        ),
      },
      {
        id: "check-line",
        title: t.checkLine,
        body: (
          <div className="flex max-w-prose flex-col gap-2">
            <CheckLine numbers={checks.numbers} quotes={checks.quotes} notChecked={["comparables"]} />
            <CheckLine numbers={{ matched: 1, total: 1 }} notChecked={["sentences"]} />
            <CheckLine quotes={{ found: 14, total: 14 }} notChecked={["sentences", "passages"]} />
            <CheckLine notChecked={["sentences"]} />
          </div>
        ),
      },
      {
        id: "coverage",
        title: t.coverage,
        body: <CoverageLine part={37} whole={52} noun={sample.coverageNoun} gap={sample.coverageGap} href="#data" />,
      },
      {
        id: "removed",
        title: t.removed,
        body: (
          <div className="flex max-w-prose flex-col gap-4">
            <RemovedBox removed={[]} />
            <RemovedBox removed={[sample.removed[0]]} />
            <RemovedBox removed={[...sample.removed]} names={["IDA", "ICR"]} />
            <RemovedBox removed={[...sample.removed]} all />
          </div>
        ),
      },
    ],
  },
  {
    slug: "answer",
    sections: [
      { id: "steps", title: t.steps, body: <Panel><Steps steps={steps(2)} /></Panel> },
      {
        id: "streaming",
        title: s.streaming,
        body: <Panel><Answer state={{ status: "streaming", steps: steps(1), stillWorking: true }} /></Panel>,
      },
      {
        id: "ready",
        title: s.ready,
        body: (
          <Panel>
            <Answer
              state={{ status: "ready", steps: doneSteps, runId: sample.runId, sentences: markers, checks: { ...checks, notChecked: [...checks.notChecked] } }}
            />
          </Panel>
        ),
      },
      {
        id: "abstained",
        title: s.abstained,
        body: (
          <Panel>
            <Answer
              state={{
                status: "abstained",
                steps: doneSteps,
                runId: sample.runId,
                sentence: sample.abstention,
                rows: <Table {...tableProps} count={sample.tableCount} state={{ status: "ready", rows }} />,
                checks: { numbers: checks.numbers, notChecked: ["sentences", "comparables"], removed: [] },
              }}
            />
          </Panel>
        ),
      },
      {
        id: "empty",
        title: s.empty,
        body: <Panel><Answer state={{ status: "empty", steps: doneSteps, runId: sample.runId, message: sample.empty }} /></Panel>,
      },
      {
        id: "refused",
        title: s.refused,
        body: (
          <Panel>
            <Answer state={{ status: "refused", steps: doneSteps, runId: sample.runId, message: sample.refusal, note: sample.refusalNote }} />
          </Panel>
        ),
      },
      {
        id: "error",
        title: s.error,
        body: (
          <Panel>
            <Answer state={{ status: "error", steps: doneSteps.slice(0, 2), message: sample.answerError, onRetry: () => {} }} />
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
            <Document state={{ status: "ready", passage: {
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
      {
        id: "ready",
        title: s.ready,
        body: <Table {...tableProps} count={sample.tableCount} state={{ status: "ready", rows }} />,
      },
      { id: "loading", title: s.loading, body: <Table {...tableProps} count={sample.tableCount} state={{ status: "loading", rows: 4 }} /> },
      {
        id: "empty",
        title: s.empty,
        body: (
          <Table
            {...tableProps}
            state={{ status: "empty", empty: <EmptyState level={4} title={sample.tableEmptyTitle} body={sample.tableEmptyBody} /> }}
          />
        ),
      },
      {
        id: "error",
        title: s.error,
        body: (
          <Table
            {...tableProps}
            state={{
              status: "error",
              error: (
                <Alert state="error" action={<Button variant="secondary">{copy.answer.tryAgain}</Button>}>
                  {sample.tableError}
                </Alert>
              ),
            }}
          />
        ),
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
              <SkeletonText className="mt-4" widths={["w-full", "w-11/12", "w-3/5"]} />
            </div>
          </Panel>
        ),
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
