// The Packages tab (the 15 brief, section 7.9; ticket 100's redesign), at /packages: the packages the person is
// planning and the plans they checked, newest first, 20 a page, as one panel that spans all 12 columns (cards below
// 768 px). Its two actions, at the head's right, put the one box into a mode and move focus there: "Check a plan"
// lists a project's latest plans by agency, and "Plan a package" lists "Plan a package from this sentence" first.
// Every row and count comes from GET /api/planned-packages; the page counts nothing itself.
import { useEffect, useId, useState } from "react";
import { getJson } from "../lib/api";
import { Button } from "../components/Button";
import { FootStrip } from "../components/FootStrip";
import { Num } from "../components/Num";
import { Tag } from "../components/LessonParts";
import { PageHead } from "../components/PageHead";
import { SkeletonLine, SkeletonWords } from "../components/Skeleton";
import { Source } from "../components/Source";
import { countText, Table, type Column, type Row } from "../components/Table";
import { TaskZone } from "../components/TaskZone";
import { DefinitionWindow } from "../components/Term";
import { TextLink } from "../components/TextLink";
import { copy } from "../copy";
import { formatCount, formatDate } from "../lib/format";
import { useLoad, type Load } from "../lib/load";
import { enterBoxMode, type PlannedList, type PlannedRow } from "../lib/packages";
import { PublicView } from "./PlannedPackagePage";
import { AccessLabel } from "../components/AccessLabel";
import { PRIMARY_LINK } from "../components/Button";
import { useStore } from "../lib/store";
import { CHECK_MY_PLAN, officerAgency, uploadHref, type UploadListing } from "../lib/uploads";
import { previewReason } from "../lib/view";

// An implementing agency team's uploads, newest first, each with the compact access label (ticket 38). Only the team
// gets them from the server; a preview gets none.
function UploadsList() {
  const [load] = useLoad<{ uploads: UploadListing[] }>("/api/uploads");
  if (load.status !== "ready" || load.data.uploads.length === 0) return null;
  return (
    <section className="mt-6" aria-labelledby="uploads-heading" data-uploads>
      <h2 id="uploads-heading" className="text-h2 text-ink-heading">{words.uploadsTitle}</h2>
      <ul className="mt-3 flex flex-col gap-3">
        {load.data.uploads.map((upload) => (
          <li key={upload.upload_id} className="flex flex-col">
            <TextLink href={uploadHref(upload.upload_id)}>{words.uploadName(formatDate(upload.uploaded_on))}</TextLink>
            <span className="flex flex-wrap items-center gap-x-3 text-caption text-ink-muted">
              {words.uploadCaption(upload.activities, formatCount(upload.activities, { capital: true }))}
              <AccessLabel compact />
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

const words = copy.packagesTab;
const PAGE = 20;
const mono = (text: string) => <span className="font-mono">{text}</span>;

function rowOf(row: PlannedRow): Row {
  if (row.type === "package") {
    const name = row.description && row.country_name ? copy.packageWorkspace.title(row.description, row.country_name) : copy.packageWorkspace.titleNew;
    return {
      id: row.package_id,
      cells: {
        name: (
          <span className="flex flex-col">
            <span>
              <TextLink href={`/packages/${encodeURIComponent(row.package_id)}`}>{name}</TextLink>
              {/* A package the seed command planned for you (ticket 41). */}
              {row.example && (
                <span className="ml-2 inline-block align-middle">
                  <Tag>{copy.home.example}</Tag>
                </span>
              )}
            </span>
            <span className="text-caption text-ink-muted">
              {row.step_reference ? mono(row.step_reference) : words.noReference}
              {row.guesses > 0 && <> {copy.packageWorkspace.card.guesses(row.guesses, formatCount(row.guesses, { capital: true }))}</>}
            </span>
          </span>
        ),
        type: words.typePackage,
        country: row.country_name ?? words.noCountry,
        project: row.project_id ? <TextLink href={`/projects/${row.project_id}`}>{mono(row.project_id)}</TextLink> : words.noProject,
        last: <LastDate on={row.last_worked_on} />,
      },
    };
  }
  const agency = row.implementing_agency ?? row.agency_id;
  const href = `/projects/${row.project_id}/procurement/${row.agency_id}${row.latest ? "" : `/${row.plan_date}`}`;
  return {
    id: `${row.project_id}/${row.agency_id}/${row.plan_date}/${row.latest ? "latest" : "version"}`,
    cells: {
      name: (
        <span className="flex flex-col">
          <TextLink href={href}>{words.planName(agency, formatDate(row.plan_date))}</TextLink>
          {row.activities !== null && (
            <span className="text-caption text-ink-muted">{words.activities(row.activities, formatCount(row.activities, { capital: true }))}</span>
          )}
        </span>
      ),
      type: words.typePlan,
      country: row.country_name ?? copy.notInRecord,
      project: <TextLink href={`/projects/${row.project_id}`}>{mono(row.project_id)}</TextLink>,
      last: <LastDate on={row.last_worked_on} />,
    },
  };
}

// A row's "Last worked on" date, which never breaks inside (plan 7.10), however narrow the column is beside the sidebar.
function LastDate({ on }: { on: string }) {
  return (
    <span className="whitespace-nowrap">
      <Num date={on.slice(0, 10)} style="table" />
    </span>
  );
}

// "Last worked on" opens its definition in a window from the column head, and from each card's field below 768 px,
// since cards have no column heads (ticket 100).
function LastWorked() {
  return (
    <DefinitionWindow label={words.columns.lastWorked} title={words.columns.lastWorked}>
      {words.columns.lastWorkedDefinition}
    </DefinitionWindow>
  );
}

// The list of packages and checked plans, in each of its states (ticket 100; DESIGN.md section 5, Task zone): one panel
// with its title sentence in lead, the count line, the table and its source in the foot strip; while it loads, the same
// panel over skeleton rows; with nothing yet, a Task zone row that says so; and when it failed, the error alert in the
// list's place. The panel is the table's frame (Table's inPanel), as All projects' is: its rows run the panel's width
// on its text edge, and below 768 px they are rows with a line between them, not cards in a box.
export function PackagesList({ load, onRetry }: { load: Load<PlannedList>; onRetry: () => void }) {
  const [page, setPage] = useState(0);
  const headingId = useId();
  const columns: Column[] = [
    { key: "name", header: words.columns.name, width: "w-2/5" },
    { key: "type", header: words.columns.type, short: true, width: "w-[7rem]" },
    { key: "country", header: words.columns.country, short: true, width: "w-[7rem]" },
    { key: "project", header: words.columns.project, short: true, width: "w-[7rem]" },
    // While the rows load the table is hidden from screen readers, so its head holds the words alone, with no button.
    load.status === "loading"
      ? { key: "last", header: words.columns.lastWorked, short: true, width: "w-[8.5rem]" }
      : { key: "last", header: <LastWorked />, cardHeader: <LastWorked />, short: true, width: "w-[8.5rem]" },
  ];

  if (load.status === "error") {
    return <Table title={null} columns={columns} rowHeader="name" state={{ status: "error", message: words.error, onRetry }} />;
  }
  if (load.status === "ready" && load.data.rows.length === 0) {
    return <TaskZone name={words.emptyTitle} summary={words.emptyBody} sectionKey="packages-list" />;
  }
  if (load.status === "loading") {
    return (
      // The title and the count line as most lists read, held as skeleton words, so they take the lines the real ones
      // take at every width (ticket 59).
      <TaskZone
        panel
        leadName
        name={<SkeletonWords text={words.title(2, formatCount(2), 1, formatCount(1))} />}
        tag={<SkeletonWords text={countText({ noun: words.noun, one: words.nounOne, total: 3 })} />}
        busy
        sectionKey="packages-list"
      >
        {/* Each loading row holds a row's name and its caption line, the STEP reference under it, so the rows and the
            source line stay put when the list arrives (ticket 59; the 15 design review, round 3, G6). */}
        <Table
          title={null}
          labelledBy={headingId}
          columns={columns}
          rowHeader="name"
          inPanel
          state={{
            status: "loading",
            rows: 5,
            header: (
              <span className="flex flex-col">
                <SkeletonLine width="w-4/5" />
                <SkeletonLine className="text-caption" width="w-2/5" />
              </span>
            ),
          }}
        />
        <FootStrip>
          <SkeletonLine className="text-caption" width="w-2/5" />
        </FootStrip>
      </TaskZone>
    );
  }
  const { rows, counts } = load.data;
  const from = page * PAGE;
  const shown = rows.slice(from, from + PAGE);
  const count = { noun: words.noun, one: words.nounOne, total: counts.total, from: from + 1, to: from + shown.length };
  return (
    <TaskZone
      panel
      leadName
      headingId={headingId}
      name={words.title(counts.packages, formatCount(counts.packages), counts.plan_checks, formatCount(counts.plan_checks))}
      tag={
        <span data-count-line data-numbers>
          {countText(count)}
        </span>
      }
      sectionKey="packages-list"
    >
      <Table title={null} labelledBy={headingId} columns={columns} rowHeader="name" inPanel state={{ status: "ready", rows: shown.map(rowOf) }} />
      {counts.total > PAGE && (
        <div data-zone-pager className="flex flex-wrap gap-3">
          <Button variant="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
            {words.previous}
          </Button>
          <Button variant="secondary" disabled={from + PAGE >= counts.total} onClick={() => setPage(page + 1)}>
            {words.next}
          </Button>
        </div>
      )}
      <FootStrip>
        <Source>{words.source}</Source>
      </FootStrip>
    </TaskZone>
  );
}

// The public view holds no packages, so the route shows the not-in-this-view state and reads nothing; the
// implementing agency preview lists them with both buttons held (brief 7.9).
export function PackagesPage({ search }: { search: string }) {
  const view = new URLSearchParams(search).get("view");
  if (view === "public") return <PublicView />;
  return <PackagesTab preview={view === "piu"} search={search} />;
}

// Home's "Plan a package from a sentence" (ticket 41) lands here with ?box=plan&example={key}: the one box in plan mode,
// with the examples registry's sentence filled in and focus in the box. The address carries the key, never the
// sentence, so the page never shows words taken from the address.
function useBoxFromAddress(search: string, preview: boolean) {
  useEffect(() => {
    const params = new URLSearchParams(search);
    if (params.get("box") !== "plan" || preview) return;
    const example = params.get("example");
    if (!example) {
      requestAnimationFrame(() => enterBoxMode("plan"));
      return;
    }
    let live = true;
    getJson<{ sentence: string }>(`/api/examples/${encodeURIComponent(example)}`).then(
      (found) => live && enterBoxMode("plan", found.sentence),
      () => live && enterBoxMode("plan"),
    );
    return () => {
      live = false;
    };
  }, []);
}

// At least a screen tall in every state, so the footer never rises into view when a short answer, such as
// the empty or error state, replaces the loading rows (design review round 2, F9).
function PackagesTab({ preview, search }: { preview: boolean; search: string }) {
  const [load, retry] = useLoad<PlannedList>("/api/planned-packages");
  useBoxFromAddress(search, preview);
  const officer = Boolean(useStore(officerAgency)) && !preview;
  // The head's two verbs (ticket 100; DESIGN.md section 5, Page head): "Check a plan", the primary, then "Plan a
  // package", at the head's right when the page area allows (46rem) and under the purpose otherwise. Each puts the one
  // box in its mode with focus in the box. An officer's primary is "Check my plan"; a preview holds both, and says why.
  const actions = (
    <>
      {officer ? (
        <a href={CHECK_MY_PLAN} className={PRIMARY_LINK} data-check-mine>
          {words.checkMine}
        </a>
      ) : (
        <Button variant="primary" held={preview} onClick={() => !preview && enterBoxMode("check")} className="w-full @head/page:w-auto">
          {words.checkPlan}
        </Button>
      )}
      <Button variant="secondary" held={preview} onClick={() => !preview && enterBoxMode("plan")} className="w-full @head/page:w-auto">
        {words.planPackage}
      </Button>
    </>
  );
  return (
    <div className="layout-grid min-h-svh" data-packages-page={load.status}>
      <div className="col-span-12">
        <PageHead title={copy.pages.packages.title} purpose={officer ? words.purposeAgency : words.purpose} action={actions} />
        {preview && <p className="mt-3 text-caption text-ink-muted">{previewReason("plan_package") ?? words.previewOff}</p>}
        {officer && <UploadsList />}
        <div className="mt-8">
          <PackagesList load={load} onRetry={retry} />
        </div>
        {load.status === "loading" && (
          <p role="status" className="sr-only">
            {words.loading}
          </p>
        )}
      </div>
    </div>
  );
}
