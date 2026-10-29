// The gallery's zones page (ticket 95): the Task zone in its forms and states, the foot strip, the stage label, the side
// panel and the page head, each at its worst-case string (plan 7.10), and the workspace sample at
// /gallery/zones?sample=workspace, which lays out as a workspace page does beside the evidence drawer. ?drawer=open
// opens the drawer on load; the side panel's marker and the facts line's button open it too.
import { useEffect, useRef, useState, type ReactNode } from "react";
import { Alert } from "../components/Alert";
import { Button } from "../components/Button";
import { CitationMarker } from "../components/CitationMarker";
import { EvidenceDrawerView } from "../components/EvidenceDrawer";
import { Unbroken } from "../components/Fill";
import { FootStrip } from "../components/FootStrip";
import { Num } from "../components/Num";
import { PageHead, type FactsLine } from "../components/PageHead";
import { SidePanel, type SideFact } from "../components/SidePanel";
import { StageLabel } from "../components/StageLabel";
import { TaskZone, ZoneBlock } from "../components/TaskZone";
import { TextLink } from "../components/TextLink";
import { Workspace } from "../components/Workspace";
import { copy } from "../copy";
import { createStore, useStore } from "../lib/store";
import { PLAN_RECORD } from "./answers";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const z = galleryCopy.zones;
const DRAWER_ID = "zones-drawer";

// The sample drawer: open or not, and the button or marker that opened it, where focus goes back on close.
type DrawerState = { open: boolean; opener: HTMLElement | null };
const drawer = createStore<DrawerState>({
  open: typeof window !== "undefined" && new URLSearchParams(window.location.search).get("drawer") === "open",
  opener: null,
});
const openDrawer = (opener: HTMLElement) => drawer.set({ open: true, opener });

const NARROW = "(width < 48rem)";
function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(() => window.matchMedia(NARROW).matches);
  useEffect(() => {
    const query = window.matchMedia(NARROW);
    const update = () => setNarrow(query.matches);
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return narrow;
}

// The frame's evidence drawer for the zones page: the plan row's record, beside the page, or a sheet below 768 px.
export function ZonesDrawer() {
  const { open, opener } = useStore(drawer);
  const narrow = useNarrow();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (open) heading.current?.focus({ preventScroll: true });
  }, [open]);
  if (!open) return null;
  return (
    <EvidenceDrawerView
      id={PLAN_RECORD.id}
      data={{ status: "ready", evidence: PLAN_RECORD }}
      run={null}
      from={null}
      narrow={narrow}
      preview={false}
      dialogId={DRAWER_ID}
      headingRef={heading}
      onClose={() => {
        drawer.set({ open: false, opener: null });
        requestAnimationFrame(() => opener?.focus());
      }}
      onChoose={() => {}}
    />
  );
}

// While the drawer is a sheet below 768 px, the page behind it takes no focus.
export function useZonesSheet(): boolean {
  const { open } = useStore(drawer);
  return useNarrow() && open;
}

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

function Label({ children }: { children: ReactNode }) {
  return <b className="font-semibold text-ink">{children}</b>;
}

// Zone 1's first block, the past range, with its foot strip.
function TookBlock() {
  return (
    <ZoneBlock
      data-block="took"
      foot={
        <FootStrip>
          <p>
            <Label>{z.took.noteLabel}</Label> {z.took.note}
          </p>
          <p data-coverage>
            {z.took.basedOn} <Num part={49} whole={65} show="count" check={{ tooltip: z.took.coverageTip }} /> {z.took.basedOnEnd}
          </p>
          <p>
            <Label>{z.took.sourceLabel}</Label> {z.took.source}
          </p>
        </FootStrip>
      }
    >
      <p className="max-w-[22.5em] text-finding text-balance text-ink-heading">{z.took.finding}</p>
      <p className="max-w-prose text-body text-ink">{z.took.body}</p>
    </ZoneBlock>
  );
}

// Zone 1's first block when its request failed: the error alert takes the block's place.
function FailedBlock() {
  return (
    <ZoneBlock data-block="failed">
      <Alert state="error" action={<Button variant="secondary">{z.took.tryAgain}</Button>}>
        {z.took.failed}
      </Alert>
    </ZoneBlock>
  );
}

// Zone 1's second block, "Advertised again", with its own foot strip.
function AgainBlock() {
  return (
    <ZoneBlock
      data-block="again"
      foot={
        <FootStrip>
          <p>
            <Label>{z.took.sourceLabel}</Label> {z.again.source}
          </p>
        </FootStrip>
      }
    >
      <h3 className="text-h3 text-ink-heading">{z.again.name}</h3>
      <p className="max-w-prose text-small text-ink-muted">{z.again.why}</p>
      <p className="text-lead text-ink">{z.again.lead}</p>
    </ZoneBlock>
  );
}

function TookZone({ failed = false }: { failed?: boolean }) {
  return (
    <TaskZone number={1} name={z.took.name} panel sectionKey={failed ? "failed" : "took"}>
      {failed ? <FailedBlock /> : <TookBlock />}
      <AgainBlock />
    </TaskZone>
  );
}

function Toggled({
  number,
  words,
  startOpen = false,
  sectionKey,
}: {
  number?: number;
  words: { name: string; summary: string; show: string; hide: string; body: string };
  startOpen?: boolean;
  sectionKey: string;
}) {
  const [open, setOpen] = useState(startOpen);
  return (
    <TaskZone
      number={number}
      name={words.name}
      summary={words.summary}
      toggle={{ open, onToggle: () => setOpen((now) => !now), show: words.show, hide: words.hide }}
      sectionKey={sectionKey}
    >
      <p className="max-w-prose text-body text-ink">{words.body}</p>
    </TaskZone>
  );
}

// The package workspace's five zones in two stages: zone 1 a panel, zones 2 to 4 rows, and zone 5 a row opened into
// a panel.
export function Sequence() {
  return (
    <div data-sequence>
      <StageLabel>{z.stages.planning}</StageLabel>
      <TookZone />
      <Toggled number={2} words={z.steps} sectionKey="steps" />
      <TaskZone
        number={3}
        name={z.risks.name}
        tag={z.risks.tag}
        summary={
          <>
            <p>{z.risks.sentence}</p>
            <p className="mt-2">
              <TextLink href="#risks">{z.risks.link}</TextLink>
            </p>
          </>
        }
        sectionKey="risks"
      />
      <TaskZone number={4} name={z.approach.name} tag={z.approach.tag} summary={<Unbroken text={z.approach.sentence} />} sectionKey="approach" />
      <StageLabel>{z.stages.tender}</StageLabel>
      <Toggled number={5} words={z.criteria} startOpen sectionKey="criteria" />
    </div>
  );
}

function Unnumbered() {
  return (
    <div>
      <TaskZone name={z.activities.name} tag={z.activities.tag} panel sectionKey="activities">
        <ZoneBlock
          foot={
            <FootStrip>
              <p>
                <Label>{z.took.sourceLabel}</Label> {z.activities.source}
              </p>
            </FootStrip>
          }
        >
          <p className="max-w-prose text-body text-ink">{z.activities.body}</p>
        </ZoneBlock>
      </TaskZone>
      <TaskZone
        name={z.baseline.name}
        summary={
          <>
            <p>{z.baseline.sentence}</p>
            <p className="mt-2">
              <Button variant="secondary">{z.baseline.action}</Button>
            </p>
          </>
        }
        sectionKey="baseline"
      />
    </div>
  );
}

function StartHere() {
  return (
    <TaskZone
      name={z.startHere.name}
      tag={z.startHere.tag}
      summary={
        <>
          <p>{z.startHere.sentence}</p>
          <p className="mt-2">
            <TextLink href="#start-here">{z.startHere.link}</TextLink>
          </p>
        </>
      }
      corner={
        <Button variant="ghost" flush onPage aria-label={z.startHere.removeName}>
          {z.startHere.remove}
        </Button>
      }
      sectionKey="start-here"
    />
  );
}

// The skeleton page's sample: a zone that loads, its button working.
export function LoadingZone() {
  const [open, setOpen] = useState(false);
  return (
    <TaskZone
      number={2}
      name={z.steps.name}
      state="loading"
      busy
      toggle={{ open, onToggle: () => setOpen((now) => !now), show: z.steps.show, hide: z.steps.hide }}
      sectionKey="skeleton-zone"
    >
      <p className="max-w-prose text-body text-ink">{z.steps.body}</p>
    </TaskZone>
  );
}

// One zone in each of its five states, each with its own Show or Hide control where it has one.
function States() {
  const [open, setOpen] = useState(true);
  const [closed, setClosed] = useState(false);
  const [loading, setLoading] = useState(false);
  const toggle = (now: boolean, set: (next: boolean) => void) => ({ open: now, onToggle: () => set(!now), show: z.steps.show, hide: z.steps.hide });
  const failed = (
    <Alert state="error" action={<Button variant="secondary">{z.took.tryAgain}</Button>}>
      {z.steps.failed}
    </Alert>
  );
  const body = <p className="max-w-prose text-body text-ink">{z.steps.body}</p>;
  return (
    <div className="flex flex-col gap-8">
      <Labeled label={z.labels.open}>
        <TaskZone number={2} name={z.steps.name} summary={z.steps.summary} toggle={toggle(open, setOpen)} sectionKey="state-open">
          {body}
        </TaskZone>
      </Labeled>
      <Labeled label={z.labels.closed}>
        <TaskZone number={2} name={z.steps.name} summary={z.steps.summary} toggle={toggle(closed, setClosed)} sectionKey="state-closed">
          {body}
        </TaskZone>
      </Labeled>
      <Labeled label={z.labels.loading}>
        <TaskZone number={2} name={z.steps.name} state="loading" busy toggle={toggle(loading, setLoading)} sectionKey="state-loading">
          {body}
        </TaskZone>
      </Labeled>
      <Labeled label={z.labels.error}>
        <TaskZone number={2} name={z.steps.name} state="error" error={failed} toggle={toggle(false, () => {})} sectionKey="state-error">
          {body}
        </TaskZone>
      </Labeled>
      <Labeled label={z.labels.empty}>
        <TaskZone
          number={2}
          name={z.steps.name}
          state="empty"
          summary={
            <>
              <p>{z.steps.empty}</p>
              <p className="mt-2">
                <TextLink href="#plan-row">{z.steps.emptyLink}</TextLink>
              </p>
            </>
          }
          toggle={toggle(false, () => {})}
          sectionKey="state-empty"
        />
      </Labeled>
    </div>
  );
}

const FACTS: SideFact[] = [
  { label: z.facts.method, value: z.facts.methodValue },
  { label: z.facts.market, value: z.facts.marketValue },
  { label: z.facts.review, value: z.facts.reviewValue },
  { label: z.facts.amount, value: <span className="whitespace-nowrap tabular-nums">{z.facts.amountValue}</span> },
  { label: z.facts.status, value: z.facts.statusValue, wide: true },
  { label: z.facts.plan, value: <TextLink href="#plan">{z.facts.planValue}</TextLink>, wide: true },
];

function FactsPanel({ loading = false }: { loading?: boolean }) {
  const { open } = useStore(drawer);
  return (
    <SidePanel
      title={z.facts.title}
      facts={FACTS}
      loading={loading}
      source={
        <p>
          <Label>{z.facts.sourceLabel}</Label>{" "}
          {z.facts.source}
          <CitationMarker
            n={1}
            source={z.facts.sourceName}
            href="?sample=workspace&drawer=open"
            drawerId={DRAWER_ID}
            active={open}
            onOpen={openDrawer}
          />
        </p>
      }
    />
  );
}

function factsLine(expanded: boolean): FactsLine {
  return { line: z.facts.line, show: z.facts.show, onShow: openDrawer, expanded };
}

const trail = [
  { text: z.head.packages, href: "/packages" },
  {
    text: (
      <>
        {z.head.project} (<span className="font-mono font-medium">{z.head.pid}</span>)
      </>
    ),
    href: "#project",
  },
];

function Head({ level, facts }: { level: 1 | 2; facts: boolean }) {
  const { open } = useStore(drawer);
  return (
    <PageHead
      level={level}
      trail={trail}
      held
      title={z.head.description}
      id={z.head.reference}
      purpose={copy.pages.package.purpose}
      facts={facts ? factsLine(open) : undefined}
      action={facts ? undefined : <Button variant="primary">{z.head.action}</Button>}
    />
  );
}

// The workspace sample (?sample=workspace): the page head at its longest strings, the facts in the side panel, and the
// numbered zones, as the package workspace will draw them.
export function WorkspaceSample() {
  return (
    <div className="layout layout-grid pt-6 md:pt-8 lg:pt-10" data-workspace-sample>
      <div className="col-span-12 min-w-0">
        <Workspace head={<Head level={1} facts />} side={<FactsPanel />} fold="head">
          <Sequence />
        </Workspace>
      </div>
    </div>
  );
}

export function zonesPage(): GalleryPage {
  const t = z.sections;
  return {
    slug: "zones",
    current: "packages",
    aside: <ZonesDrawer />,
    samples: { workspace: <WorkspaceSample /> },
    sections: [
      {
        id: "workspace",
        title: t.workspace,
        body: (
          <div className="flex max-w-prose flex-col gap-2">
            <p className="text-body text-ink">{z.workspaceNote}</p>
            <p>
              <TextLink href="/gallery/zones?sample=workspace">{z.workspaceLink}</TextLink>
            </p>
            <p>
              <TextLink href="/gallery/zones?sample=workspace&drawer=open">{z.workspaceDrawerLink}</TextLink>
            </p>
          </div>
        ),
      },
      { id: "sequence", title: t.sequence, body: <Sequence /> },
      { id: "unnumbered", title: t.unnumbered, body: <Unnumbered /> },
      { id: "tag-under", title: t.tagUnder, body: <StartHere /> },
      { id: "failed", title: t.failed, body: <TookZone failed /> },
      { id: "states", title: t.states, body: <States /> },
      {
        id: "side",
        title: t.side,
        body: (
          <div className="flex max-w-[22.5rem] flex-col gap-8">
            <Labeled label={z.labels.sidePanel}>
              <FactsPanel />
            </Labeled>
            <Labeled label={z.labels.sideLoading}>
              <FactsPanel loading />
            </Labeled>
            <Labeled label={z.labels.sideRow}>
              <SidePanel title={z.waiting.title} sentence={z.waiting.sentence} />
            </Labeled>
          </div>
        ),
      },
      {
        id: "head",
        title: t.head,
        body: (
          <div className="flex flex-col gap-10">
            <Labeled label={z.labels.headFacts}>
              <Head level={2} facts />
            </Labeled>
            <Labeled label={z.labels.headPlain}>
              <Head level={2} facts={false} />
            </Labeled>
          </div>
        ),
      },
    ],
  };
}
