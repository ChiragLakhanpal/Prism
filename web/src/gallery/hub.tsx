// The gallery's Project page parts (ticket 21): every new component of the project hub in each state a
// sample can show without a server, from the answers the server wrote on the fixture (tests/record_api.py),
// so each sample is a real project's. The pages' own states, such as loading and errors, and the baseline
// panel's states after a save, are captured from the production build (web/capture/shots.ts).
import changesMinistry from "../../../tests/fixtures/api/changes-ministry-2020-04-30.json";
import changesNwwda from "../../../tests/fixtures/api/changes-nwwda-2026-10-09.json";
import checkWithBaseline from "../../../tests/fixtures/api/check-plan-p156634-nwwda-2026-10-09-baseline.json";
import documents from "../../../tests/fixtures/api/documents-p130164.json";
import p130164 from "../../../tests/fixtures/api/project-p130164.json";
import p156634 from "../../../tests/fixtures/api/project-p156634.json";
import sourcePage from "../../../tests/fixtures/api/source-icr-p130164-23-54.json";
import sourceTable from "../../../tests/fixtures/api/source-pad-p130164-65.json";
import sourcePlanRows from "../../../tests/fixtures/api/source-plan-p161305-3.json";
import summary from "../../../tests/fixtures/api/summary-p130164.json";
import { useRef, useState, type ReactNode } from "react";
import { BaselinePanel } from "../components/BaselinePanel";
import { ChangeTables } from "../components/ChangeTables";
import { ChangeLineError } from "../components/HowIChecked";
import { ListSearch } from "../components/ListSearch";
import { Pagination } from "../components/Pagination";
import { AgencyLine, ProjectHeaderLine } from "../components/ProjectHeader";
import { ProjectId } from "../components/ProjectId";
import { copy } from "../copy";
import { ApiError, type Baseline, type CheckPlanResult, type DocumentList, type PlanChanges, type ProjectPage, type SourcePageAnswer, type Summary } from "../lib/api";
import { DocumentsList, DocumentsSkeleton } from "../pages/project/DocumentsTab";
import { SummaryFacts, SummarySkeleton } from "../pages/project/SummaryTab";
import { ChangesError } from "../pages/CheckPlanPage";
import { PageBar, Passages } from "../pages/SourcePage";
import { galleryCopy } from "./copy";
import type { GalleryPage } from "./pages";

const t = galleryCopy.sections;
const s = galleryCopy.states;
const SUMMARY = summary as unknown as Summary;
const MINISTRY = changesMinistry as unknown as PlanChanges;
const NWWDA = changesNwwda as unknown as PlanChanges;
// An activity dropped: the Ministry's added activity, as if the later version had left it out.
const DROPPED: PlanChanges = { ...MINISTRY, counts: { added: 0, dropped: 1, redated: 0, reestimated: 0 }, added: [], dropped: MINISTRY.added, redated: [] };
const SAVED = (checkWithBaseline as unknown as CheckPlanResult).baseline as Baseline;
const SOURCE = sourcePage as unknown as SourcePageAnswer;
const nothing = () => Promise.reject(new Error());
// The samples' project, agency and document, from the recordings.
const ICR_PROJECT = SOURCE.project.project_id;
const ICR_KEY = SOURCE.document!.doc_key!;
const KENYA = (p156634 as unknown as ProjectPage).project.project_id;
const PLAN = NWWDA.plan;

function Labeled({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex flex-col gap-2">
      <p className="text-caption text-ink-muted">{label}</p>
      {children}
    </div>
  );
}

// A sample as wide as the Summary's columns 1 to 7 at 1440 px.
function Column({ children }: { children: ReactNode }) {
  return <div className="max-w-[46.5rem]">{children}</div>;
}

function SearchSample() {
  const [query, setQuery] = useState("india");
  return (
    <div className="max-w-[36rem]">
      <ListSearch label={copy.projectsPage.search.label} value={query} onSearch={setQuery} />
    </div>
  );
}

function SourceSample() {
  const block = useRef<HTMLDivElement>(null);
  return (
    <Column>
      <PageBar pid={ICR_PROJECT} doc={ICR_KEY} page={SOURCE.page ?? 1} pages={SOURCE.document!.pdf_pages} full onMove={() => undefined} />
      <div className="mt-6">
        <Passages answer={SOURCE} blockRef={block} />
      </div>
    </Column>
  );
}

// A source page whose passages hold a table, or a plan's STEP rows: a table in its frame from 768 px and one card per
// row below it (ticket 60).
function SourcePassages({ answer }: { answer: SourcePageAnswer }) {
  const block = useRef<HTMLDivElement>(null);
  return (
    <Column>
      <Passages answer={answer} blockRef={block} />
    </Column>
  );
}

const header = (page: unknown) => {
  const project = (page as ProjectPage).project;
  return (
    <div>
      <h2 className="text-h1 text-ink-heading">
        <ProjectHeaderLine project={project} />
      </h2>
      <AgencyLine names={project.implementing_agencies} />
    </div>
  );
};

const panel = (baseline: Baseline | null, planDate: string, view: "staff" | "piu" = "staff") => (
  <div className="max-w-[72ch]">
    <BaselinePanel
      pid={KENYA}
      agencyId={PLAN.agency_id}
      agency={PLAN.implementing_agency}
      planDate={planDate}
      baseline={baseline}
      view={view}
      refresh={nothing}
    />
  </div>
);

const missingFact = SUMMARY.dates.map((fact) => (fact.key === "approval_date" ? { ...fact, value: null } : fact));

// P130164's documents with its first other document's type left blank, as the documents API leaves P156634's
// document 40098345: it is named by its date.
const DOCUMENTS = documents as unknown as DocumentList;
const UNTYPED: DocumentList = {
  ...DOCUMENTS,
  groups: DOCUMENTS.groups.map((group) =>
    group.type === "other" ? { ...group, documents: group.documents.map((document, index) => (index === 0 ? { ...document, document_type: "" } : document)) } : group,
  ),
};
// The comparison's answer when the data service didn't answer, with the request's reference.
const CHANGES_DOWN = new ApiError(503, `/api/projects/${KENYA}/procurement/${PLAN.agency_id}/${PLAN.plan_date}/changes`, {
  code: "data_service",
  trace_id: "0af7651916cd43dd8448eb211c80319c",
});

export function hubPage(): GalleryPage {
  return {
    slug: "hub",
    current: "projects",
    sections: [
      {
        id: "header",
        title: t.projectHeader,
        body: header(p130164),
      },
      { id: "header-many", title: t.projectHeaderMany, body: header(p156634) },
      {
        id: "project-id",
        title: t.projectId,
        body: (
          <div className="flex flex-col gap-4">
            <Labeled label={s.otherPage}>
              <p className="text-body text-ink">
                <ProjectId pid={KENYA} />
              </p>
            </Labeled>
            <Labeled label={s.currentPage}>
              <p className="text-body text-ink">
                <ProjectId pid={ICR_PROJECT} current />
              </p>
            </Labeled>
          </div>
        ),
      },
      { id: "list-search", title: t.listSearch, body: <SearchSample /> },
      {
        id: "pagination",
        title: t.pagination,
        body: (
          <div className="flex max-w-[46.5rem] flex-col gap-6">
            {[
              [s.firstPage, 1],
              [s.middlePage, 3],
              [s.lastPage, 5],
            ].map(([label, page]) => (
              <Labeled key={String(label)} label={String(label)}>
                <Pagination label={copy.projectsPage.pages} page={Number(page)} pages={5} href={() => "/gallery/hub"} />
              </Labeled>
            ))}
          </div>
        ),
      },
      {
        id: "fact-table",
        title: t.factTable,
        body: (
          <Column>
            <SummaryFacts summary={SUMMARY} />
          </Column>
        ),
      },
      {
        id: "fact-missing",
        title: t.factMissing,
        body: (
          <Column>
            <SummaryFacts summary={{ ...SUMMARY, dates: missingFact, money: [], ratings: [] }} />
          </Column>
        ),
      },
      {
        id: "fact-loading",
        title: t.factLoading,
        body: (
          <Column>
            <SummarySkeleton />
          </Column>
        ),
      },
      { id: "changes-added-redated", title: t.changesAddedRedated, body: <ChangeTables changes={MINISTRY} agency={MINISTRY.plan.implementing_agency} /> },
      { id: "changes-reestimated", title: t.changesReestimated, body: <ChangeTables changes={NWWDA} agency={NWWDA.plan.implementing_agency} /> },
      { id: "changes-dropped", title: t.changesDropped, body: <ChangeTables changes={DROPPED} agency={DROPPED.plan.implementing_agency} /> },
      { id: "baseline-none", title: t.baselineNone, body: panel(null, "2025-07-21") },
      { id: "baseline-this", title: t.baselineThis, body: panel(SAVED, SAVED.plan_date) },
      { id: "baseline-another", title: t.baselineAnother, body: panel(SAVED, "2026-10-09") },
      {
        id: "baseline-piu",
        title: t.baselinePiu,
        body: (
          <div className="flex flex-col gap-4">
            {panel({ ...SAVED, saved_by: null }, "2026-10-09", "piu")}
            {panel(null, "2026-10-09", "piu")}
          </div>
        ),
      },
      {
        id: "document-list",
        title: t.documentList,
        body: (
          <Column>
            <DocumentsList data={DOCUMENTS} pid={ICR_PROJECT} />
          </Column>
        ),
      },
      {
        id: "document-loading",
        title: t.documentLoading,
        body: (
          <Column>
            <DocumentsSkeleton />
          </Column>
        ),
      },
      { id: "source-page", title: t.sourcePage, body: <SourceSample /> },
      { id: "source-table", title: t.sourceTable, body: <SourcePassages answer={sourceTable as unknown as SourcePageAnswer} /> },
      { id: "source-plan-rows", title: t.sourcePlanRows, body: <SourcePassages answer={sourcePlanRows as unknown as SourcePageAnswer} /> },
      {
        id: "page-bar-loading",
        title: t.pageBarLoading,
        body: (
          <Column>
            <PageBar pid={ICR_PROJECT} doc={ICR_KEY} page={23} pages={null} full onMove={() => undefined} />
          </Column>
        ),
      },
      {
        id: "document-untyped",
        title: t.documentUntyped,
        body: (
          <Column>
            <DocumentsList data={UNTYPED} pid={ICR_PROJECT} />
          </Column>
        ),
      },
      {
        id: "changes-error",
        title: t.changesError,
        body: (
          <div className="flex flex-col gap-6">
            <ChangeLineError className="mt-2 text-body text-ink" />
            <ChangesError error={CHANGES_DOWN} onRetry={() => undefined} attempt={0} />
          </div>
        ),
      },
    ],
  };
}
