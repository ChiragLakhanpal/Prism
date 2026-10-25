// A project's Procurement tab (the 10 brief, section 3, and the 21 brief, section 4): each implementing
// agency's Procurement Plan versions, newest first, in the order the route gives, then the project's
// Packages. Ticket 21 adds, to each agency, one sentence on what changed in its latest plan with a link to
// the full list on that plan's check (#changes), the Baseline mark beside the saved version, and a fold:
// the five newest versions and the baseline show, and "Show all {n} versions" shows the rest. Every count
// is the route's, so the screen counts nothing.
//
// States: loading, populated, an agency with no plan, a project with no plans, a service that didn't
// answer, and an account that can't read Strata's tables; and for Packages, no match and its own error.
import { useId, useState, type ReactNode } from "react";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/Card";
import { EightColumns } from "../../components/EightColumns";
import { Fill, Unbroken } from "../../components/Fill";
import { LoadError } from "../../components/LoadError";
import { Num } from "../../components/Num";
import { SkeletonLine } from "../../components/Skeleton";
import { Table, type Column, type Row } from "../../components/Table";
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import type { Agency, ProjectPage as Page } from "../../lib/api";
import { changed, changeList } from "../../lib/changes";
import { formatDate, formatNumber } from "../../lib/format";
import type { Load } from "../../lib/load";
import { Packages } from "./Packages";

const words = copy.projectPage;
const plans = copy.procurement;
const whole = (value: number) => formatNumber(value, { compact: false });
const short = (iso: string) => formatDate(iso, { style: "table" });

const columns: Column[] = [
  { key: "version", header: plans.columns.version, width: "w-1/2" },
  { key: "disclosed", header: plans.columns.disclosed, short: true },
  { key: "activities", header: plans.columns.activities, numeric: true },
];

// One sentence on what changed in the agency's latest plan, and its link to the full list.
function ChangesSentence({ agency, pid }: { agency: Agency; pid: string }) {
  const found = agency.changes;
  const latest = agency.versions[0];
  if (!found || !latest) return null;
  const words = plans.changes;
  let sentence: ReactNode;
  let link: string | null = null;
  // Dates in a sentence are long (DESIGN.md section 7 rule 13); the version table keeps "Plan of Oct 9, 2026".
  const long = (iso: string | null | undefined) => (iso ? formatDate(iso) : "");
  if (found.state === "earliest") sentence = <Fill template={words.earliest} slots={{ plan_date: long(latest.plan_date) }} />;
  else if (found.state === "previous_not_read") sentence = <Fill template={words.prevUnread} slots={{ prev_date: long(found.previous_plan_date) }} />;
  else if (!changed(found.counts)) {
    sentence = <Fill template={words.same} slots={{ plan_date: long(latest.plan_date), prev_date: long(found.previous_plan_date) }} />;
  } else {
    sentence = (
      <Fill
        template={words.lead}
        slots={{ prev_date: long(found.previous_plan_date), plan_date: long(latest.plan_date), change_list: <Unbroken text={changeList(found.counts!)} /> }}
      />
    );
    link = `/projects/${pid}/procurement/${agency.agency_id}/${latest.plan_date}#changes`;
  }
  return (
    <p className="max-w-[72ch] text-body text-ink" data-changes-sentence>
      {sentence}
      {link && (
        <>
          {" "}
          <TextLink href={link} className="whitespace-nowrap">
            {words.link}
          </TextLink>
        </>
      )}
    </p>
  );
}

function AgencyPlans({ agency, pid, through }: { agency: Agency; pid: string; through: string | null }) {
  const [open, setOpen] = useState(false);
  const [opened, setOpened] = useState(false);
  const tableId = useId();
  const headingId = useId();
  if (agency.version_count === 0) {
    return (
      <section data-agency={agency.agency_id}>
        <h3 className="text-title text-ink-heading">{agency.implementing_agency}</h3>
        <p className="mt-2 text-small text-ink-muted">{plans.agencyEmpty}</p>
      </section>
    );
  }
  const shownCount = agency.shown_count ?? agency.version_count;
  const folds = shownCount < agency.version_count;
  const visible = agency.versions.filter((version) => open || !folds || version.shown !== false);
  const rows: Row[] = visible.map((version) => {
    const label = plans.versionLink(short(version.plan_date));
    const mark = (text: string) => (
      <>
        {" "}
        <span className="ml-2 text-caption text-ink-muted">{text}</span>
      </>
    );
    return {
      id: version.document_id,
      cells: {
        version: (
          <span className={opened && version.shown === false ? "animate-fade-in" : undefined}>
            {version.read ? <TextLink href={`/projects/${pid}/procurement/${agency.agency_id}/${version.plan_date}`}>{label}</TextLink> : label}
            {version.is_latest && mark(plans.latest)}
            {version.is_baseline && mark(plans.baselineMark)}
          </span>
        ),
        disclosed: version.disclosed_on ? <Num date={version.disclosed_on} style="table" /> : copy.notInRecord,
        activities:
          version.read && version.activities !== null ? (
            <Num value={version.activities} options={{ compact: false }} />
          ) : (
            <span className="text-ink-muted">{plans.notRead}</span>
          ),
      },
    };
  });
  const countText = folds && !open ? plans.versionsShowing(whole(shownCount), whole(agency.version_count)) : undefined;
  return (
    <section data-agency={agency.agency_id} className="flex flex-col gap-2">
      <h3 id={headingId} className="text-title text-ink-heading">
        {agency.implementing_agency}
      </h3>
      <ChangesSentence agency={agency} pid={pid} />
      <div id={tableId} className="mt-2">
        <Table
          title={agency.implementing_agency}
          labelledBy={headingId}
          level={3}
          count={{ noun: plans.noun, one: plans.nounOne, total: agency.version_count, text: countText }}
          columns={columns}
          rowHeader="version"
          state={{ status: "ready", rows }}
          source={
            through ? (
              <Fill template={plans.source} slots={{ date: formatDate(through) }} />
            ) : (
              plans.sourceUndated
            )
          }
        />
      </div>
      {folds && (
        <div>
          <Button
            variant="ghost"
            flush
            onPage
            aria-expanded={open}
            aria-controls={tableId}
            onClick={() => {
              setOpen(!open);
              setOpened(true);
            }}
          >
            {open ? plans.versionsLess : plans.versionsMore(whole(agency.version_count))}
          </Button>
        </div>
      )}
      {agency.versions.some((version) => !version.read) && <p className="max-w-prose text-caption text-ink-muted">{plans.unreadNote}</p>}
    </section>
  );
}

// The agencies the project record names that have published no plan, together after the ones
// with plans, so the exceptions stand out and the rest fold into one block.
function OtherAgencies({ agencies }: { agencies: Agency[] }) {
  return (
    <section data-other-agencies>
      <h3 className="text-title text-ink-heading">{plans.otherAgencies}</h3>
      <p className="mt-2 text-small text-ink-muted">{plans.othersEmpty}</p>
      <ul className="mt-2 list-disc pl-6 text-small text-ink">
        {agencies.map((agency) => (
          <li key={agency.agency_id} data-agency={agency.agency_id}>
            {agency.implementing_agency}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function ProcurementTab({ pid, load, retry }: { pid: string; load: Load<Page>; retry: () => void }) {
  // Three columns read best at the prose width, so the version tables keep to columns 1 to 8 from
  // 1200 px (EightColumns breakpoint="xl"); the alert and the empty state do from 1024 px.
  let plansBody: ReactNode;
  let hasPlans = true;
  if (load.status === "loading") {
    plansBody = (
      <EightColumns breakpoint="xl">
        <div className="flex flex-col gap-2" aria-hidden="true">
          <SkeletonLine className="text-title" width="w-2/5" />
          <SkeletonLine className="text-body" width="w-[70%]" />
        </div>
        <div className="mt-4">
          <Table title="" level={4} count={{ noun: plans.noun, total: 0 }} columns={columns} rowHeader="version" state={{ status: "loading", rows: 3 }} />
        </div>
        <p role="status" className="sr-only">
          {plans.changesLoading}
        </p>
      </EightColumns>
    );
  } else if (load.status === "error") {
    plansBody = (
      <EightColumns>
        <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
      </EightColumns>
    );
  } else if (load.data.agencies.every((agency) => agency.version_count === 0)) {
    hasPlans = false;
    plansBody = (
      <EightColumns>
        <EmptyState level={3} title={plans.projectEmptyTitle} body={plans.projectEmptyBody} link={{ href: "/data", text: plans.projectEmptyLink }} />
      </EightColumns>
    );
  } else {
    const withPlans = load.data.agencies.filter((agency) => agency.version_count > 0);
    const without = load.data.agencies.filter((agency) => agency.version_count === 0);
    plansBody = (
      <EightColumns breakpoint="xl">
        <div className="flex flex-col gap-12">
          {(without.length > 1 ? withPlans : load.data.agencies).map((agency) => (
            <AgencyPlans key={agency.agency_id} agency={agency} pid={pid} through={load.data.documents_through} />
          ))}
          {without.length > 1 && <OtherAgencies agencies={without} />}
        </div>
      </EightColumns>
    );
  }

  return (
    <div data-procurement-tab={load.status}>
      <EightColumns prose>
        <h2 className="text-h2 text-ink-heading">{plans.title}</h2>
        <p className="mt-2 text-body text-ink">{plans.purpose}</p>
      </EightColumns>
      <div className="mt-8">{plansBody}</div>
      {load.status !== "error" && (
        <div className="mt-12">
          <Packages pid={pid} none={!hasPlans} />
        </div>
      )}
    </div>
  );
}
