// The Packages tab (the 15 brief, section 7.9), at /packages: the packages the person is planning and the plans
// they checked, newest first, 20 a page, as one table that spans all 12 columns (cards below 768 px). Its two
// actions put the one box into a mode and move focus there: "Check a plan" lists a project's latest plans by
// agency, and "Plan a package" lists "Plan a package from this sentence" first. Every row and count comes from
// GET /api/planned-packages; the page counts nothing itself.
import { useState } from "react";
import { Button } from "../components/Button";
import { Num } from "../components/Num";
import { PageHeader } from "../components/PageHeader";
import { Table, type Column, type Row } from "../components/Table";
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

// An implementing agency team's uploads, newest first, each with the compact access label (ticket 38). Only the team
// gets them from the server; a preview gets none.
function UploadsList() {
  const [load] = useLoad<{ uploads: UploadListing[] }>("/api/uploads");
  if (load.status !== "ready" || load.data.uploads.length === 0) return null;
  return (
    <section className="mt-6" aria-labelledby="uploads-heading" data-uploads>
      <h2 id="uploads-heading" className="text-title text-ink-heading">{words.uploadsTitle}</h2>
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
            <TextLink href={`/packages/${encodeURIComponent(row.package_id)}`}>{name}</TextLink>
            <span className="text-caption text-ink-muted">
              {row.step_reference ? mono(row.step_reference) : words.noReference}
              {row.guesses > 0 && <> {copy.packageWorkspace.card.guesses(row.guesses, formatCount(row.guesses, { capital: true }))}</>}
            </span>
          </span>
        ),
        type: words.typePackage,
        country: row.country_name ?? words.noCountry,
        project: row.project_id ? <TextLink href={`/projects/${row.project_id}`}>{mono(row.project_id)}</TextLink> : words.noProject,
        last: <Num date={row.last_worked_on.slice(0, 10)} style="table" />,
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
      last: <Num date={row.last_worked_on.slice(0, 10)} style="table" />,
    },
  };
}

// The list of packages and checked plans, in each of its states: loading, failed, empty and ready.
export function PackagesList({ load, onRetry }: { load: Load<PlannedList>; onRetry: () => void }) {
  const [page, setPage] = useState(0);
  const columns: Column[] = [
    { key: "name", header: words.columns.name, width: "w-2/5" },
    { key: "type", header: words.columns.type, short: true, width: "w-[7rem]" },
    { key: "country", header: words.columns.country, short: true, width: "w-[7rem]" },
    { key: "project", header: words.columns.project, short: true, width: "w-[7rem]" },
    {
      key: "last",
      header: (
        <>
          {words.columns.lastWorked}
          <span className="block text-caption font-normal text-ink-muted">{words.columns.lastWorkedNote}</span>
        </>
      ),
      cardHeader: words.columns.lastWorked,
      short: true,
    },
  ];

  let table;
  if (load.status === "loading") table = <Table title={null} columns={columns} rowHeader="name" state={{ status: "loading", rows: 5 }} />;
  else if (load.status === "error")
    table = <Table title={null} columns={columns} rowHeader="name" state={{ status: "error", message: words.error, onRetry }} />;
  else if (load.data.rows.length === 0)
    table = <Table title={null} columns={columns} rowHeader="name" state={{ status: "empty", title: words.emptyTitle, body: words.emptyBody }} />;
  else {
    const { rows, counts } = load.data;
    const from = page * PAGE;
    const shown = rows.slice(from, from + PAGE);
    table = (
      <>
        <Table
          title={words.title(counts.packages, formatCount(counts.packages), counts.plan_checks, formatCount(counts.plan_checks))}
          count={{ noun: words.noun, one: words.nounOne, total: counts.total, from: from + 1, to: from + shown.length }}
          columns={columns}
          rowHeader="name"
          cardsNote={words.columns.lastWorkedNote}
          state={{ status: "ready", rows: shown.map(rowOf) }}
          source={words.source}
        />
        {counts.total > PAGE && (
          <div className="mt-3 flex flex-wrap gap-3">
            <Button variant="secondary" disabled={page === 0} onClick={() => setPage(page - 1)}>
              {words.previous}
            </Button>
            <Button variant="secondary" disabled={from + PAGE >= counts.total} onClick={() => setPage(page + 1)}>
              {words.next}
            </Button>
          </div>
        )}
      </>
    );
  }

  return table;
}

// The public view holds no packages, so the route shows the not-in-this-view state and reads nothing; the
// implementing agency preview lists them with both buttons held (brief 7.9).
export function PackagesPage({ search }: { search: string }) {
  const view = new URLSearchParams(search).get("view");
  if (view === "public") return <PublicView />;
  return <PackagesTab preview={view === "piu"} />;
}

// At least a screen tall in every state, so the footer never rises into view when a short answer, such as
// the empty or error state, replaces the loading rows (design review round 2, F9).
function PackagesTab({ preview }: { preview: boolean }) {
  const [load, retry] = useLoad<PlannedList>("/api/planned-packages");
  const officer = Boolean(useStore(officerAgency)) && !preview;
  return (
    <div className="layout-grid min-h-svh" data-packages-page={load.status}>
      <div className="col-span-12">
        <PageHeader title={copy.pages.packages.title} purpose={officer ? words.purposeAgency : words.purpose} />
        <div className="mt-4 flex flex-col gap-3 @md/page:flex-row @md/page:flex-wrap @md/page:items-center">
          {officer ? (
            <a href={CHECK_MY_PLAN} className={PRIMARY_LINK} data-check-mine>
              {words.checkMine}
            </a>
          ) : (
            <Button variant="primary" held={preview} onClick={() => !preview && enterBoxMode("check")} className="w-full @md/page:w-auto">
              {words.checkPlan}
            </Button>
          )}
          <Button variant="secondary" held={preview} onClick={() => !preview && enterBoxMode("plan")} className="w-full @md/page:w-auto">
            {words.planPackage}
          </Button>
          {preview && <p className="text-caption text-ink-muted">{words.previewOff}</p>}
        </div>
        {officer && <UploadsList />}
        <div className="mt-6 @lg/page:mt-8">
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
