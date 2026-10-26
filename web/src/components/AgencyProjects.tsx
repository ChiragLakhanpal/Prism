// Your agency's projects (ticket 40; the 40 brief, 3.8 and 7.3): at the top of /projects in the implementing agency
// view, for an officer and in the staff preview. It answers the roles table's "Your agency's projects, with signals
// against your own plan" with the marks Strata already computes on each plan: GET /api/agency/projects runs check_plan
// on the latest disclosed Procurement Plan of each project, and the finding is written from its counts in the same
// words as the Check a plan page's (copy.checkPlan.finding), so the counts have one source. It adds no new measure.
import { useId } from "react";
import { copy } from "../copy";
import { formatDate } from "../lib/format";
import { useLoad, type Load } from "../lib/load";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { keptQuery, MODE_KEYS } from "../lib/view";
import { Fill } from "./Fill";
import { LoadError } from "./LoadError";
import { Num } from "./Num";
import { ProjectId } from "./ProjectId";
import { Skeleton } from "./Skeleton";
import { Source } from "./Source";
import { TextLink } from "./TextLink";

export type AgencyCounts = { needs_a_look: number; watch: number; data_note: number };
export type AgencyProject = {
  project_id: string;
  project_name: string;
  display_name: string | null;
  plan: { plan_date: string; disclosed_on: string | null; agency_id: string };
  counts: AgencyCounts | null;
  withheld: string | null;
};
export type AgencyProjectsAnswer = {
  agency: { name: string; short_name: string | null; agency_id: string };
  as_of: string;
  state: "ok" | "none";
  projects: AgencyProject[];
};

const words = copy.projectsAgency;

// The plan's finding, in the Check a plan page's words, from check_plan's counts.
export function AgencyFinding({ counts, withheld }: { counts: AgencyCounts | null; withheld: string | null }) {
  if (!counts) return null;
  const f = copy.checkPlan.finding;
  const { needs_a_look: look, watch, data_note: notes } = counts;
  const first = withheld ? f.withheld : look && watch ? f.lookAndWatch(look, watch) : look ? f.lookOnly(look) : watch ? f.watchOnly(watch) : f.none;
  return (
    <>
      <Fill template={first} slots={{ look: <Num count={look} capital />, watch: <Num count={watch} /> }} />
      {notes > 0 && <Fill template={f.notes(notes)} slots={{ notes: <Num count={notes} /> }} />}
      {f.end}
    </>
  );
}

export function AgencyProjectsView({ load, onRetry, asOf }: { load: Load<AgencyProjectsAnswer>; onRetry: () => void; asOf: string | null }) {
  const heading = useId();
  // Each plan link keeps the page's view, date and language, so it holds them when opened in a new tab too.
  const mode = keptQuery(useStore(address).search, [...MODE_KEYS]);
  const data = load.status === "ready" ? load.data : null;
  const agency = data ? copy.view.agencyInSentence(data.agency.name, data.agency.short_name) : null;
  return (
    <section aria-labelledby={heading} className="mt-8" data-agency-projects={load.status === "ready" ? data!.state : load.status}>
      <h2 id={heading} className="text-title text-ink-heading">
        {words.heading}
      </h2>
      {agency && <p className="mt-2 max-w-prose text-body text-ink">{data!.state === "none" ? words.none(agency) : words.lead(agency)}</p>}
      {load.status === "loading" && (
        <div className="mt-4 flex flex-col gap-3">
          <p role="status" className="sr-only">
            {words.loading}
          </p>
          {[0, 1].map((index) => (
            <div key={index} className="flex flex-col gap-1">
              <Skeleton className="h-4 w-60 max-w-full" />
              <Skeleton className="h-[13px] w-[360px] max-w-full" />
            </div>
          ))}
        </div>
      )}
      {load.status === "error" && (
        <div className="mt-4 max-w-prose">
          <LoadError error={load.error} message={words.error} permission={words.error} onRetry={onRetry} retrying={load.retrying} attempt={load.attempt} />
        </div>
      )}
      {data && data.state === "ok" && (
        <>
          <ul className="mt-4 flex flex-col gap-3">
            {data.projects.map((project) => (
              <li key={project.project_id} data-agency-project={project.project_id}>
                <TextLink
                  href={`/projects/${project.project_id}/procurement/${project.plan.agency_id}/${project.plan.plan_date}${mode}`}
                  className="text-body font-semibold"
                >
                  {words.item(formatDate(project.plan.plan_date))}
                </TextLink>
                <p className="mt-1 text-caption text-ink-muted">
                  <Fill
                    template={words.caption}
                    slots={{ name: project.display_name ?? project.project_name, pid: <ProjectId pid={project.project_id} /> }}
                  />{" "}
                  <AgencyFinding counts={project.counts} withheld={project.withheld} />
                </p>
              </li>
            ))}
          </ul>
          <Source className="mt-4">{asOf ? words.sourceAsOf(data.agency.name, formatDate(asOf)) : words.source(data.agency.name)}</Source>
        </>
      )}
    </section>
  );
}

export function AgencyProjects({ asOf }: { asOf: string | null }) {
  const [load, retry] = useLoad<AgencyProjectsAnswer>("/api/agency/projects");
  return <AgencyProjectsView load={load} onRetry={retry} asOf={asOf} />;
}
