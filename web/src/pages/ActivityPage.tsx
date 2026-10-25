// The activity page (ticket 22; the 22 brief, section 2), at /projects/:pid/packages/:stepRef: one activity traced
// from its row in the Procurement Plan to its notice, bids, signed contract and the report paragraphs that
// appeared together with the contract. It asks the server for the whole trail in one read, as the viewer and as
// of the page's date (GET /api/projects/:pid/packages/:stepRef), and calls no model.
//
// The header is the breadcrumb (Projects, the project, Procurement, the reference), the activity's description as
// the h1, its STEP reference and implementing agency as labelled pairs, and the page's purpose. The lead says what
// happened in one sentence built from the tool's parts, with each amount, date and count a Num whose tooltip says
// which record it came from and whose click opens that record in the evidence drawer. The trail follows, on 7 of
// 12 columns from 1200 px so the drawer opens into free space. The page shows records only: no signal, estimate or
// ratio, in every view. A STEP reference opened under another project is moved to its own project's address.
//
// States: loading (real breadcrumb, skeletons sized to the trail, a status that says it is loading and, after two
// seconds, that it still is), the trail, an activity no record holds, a service that didn't answer (with "Try
// again" and the reference), and an account that can't read Strata's tables.
import { useEffect, useRef, type ReactNode } from "react";
import { Breadcrumb } from "../components/Breadcrumb";
import { EmptyState } from "../components/Card";
import { ContractTrail } from "../components/ContractTrail";
import { Fill, Joined } from "../components/Fill";
import { LoadError } from "../components/LoadError";
import { Num } from "../components/Num";
import { ProjectId, ProjectIdText } from "../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../components/Skeleton";
import { copy } from "../copy";
import { openEvidence } from "../lib/evidence";
import { useLoad } from "../lib/load";
import { address, navigate } from "../lib/router";
import { useStore } from "../lib/store";
import { setPageTitle } from "../lib/title";
import { amountText, type LeadPart, type Trail } from "../lib/trail";
import { withReadParams } from "../lib/view";
import { fill } from "../routes";
import { DocumentColumn } from "./DraftPage";

const words = copy.activity;

const open = (id: string) => (element: HTMLElement) => openEvidence(id, { serial: null, sentence: null, marker: element, runId: null });

// One part of the lead, with its values as Num: "estimated at US$300,000 in the plan".
function leadPart(part: LeadPart, trail: Trail): ReactNode {
  if (part.kind === "estimated") {
    const amount = amountText(part.amount, part.currency);
    return (
      <Fill
        template={words.leadEstimated}
        slots={{ estimate: <Num written={amount} check={{ tooltip: words.fromRecord(words.recordKind.estimated, trail.activity.step_reference), onOpen: open(part.evidence_id) }} /> }}
      />
    );
  }
  if (part.kind === "advertised") {
    return (
      <Fill
        template={words.leadAdvertised}
        slots={{ notice_date: <Num date={part.date} check={{ tooltip: words.fromRecord(words.recordKind.advertised, part.reference), onOpen: open(part.evidence_id) }} /> }}
      />
    );
  }
  if (part.kind === "signed") {
    const kind = part.record_noun === "award notice" ? words.recordKind.award_notice : words.recordKind.signed;
    const tooltip = words.fromRecord(kind, part.reference);
    // A contract whose record gives no amount says only when it was signed.
    return (
      <Fill
        template={part.amount ? words.leadSigned : words.leadSignedNoAmount}
        slots={{
          signed_date: <Num date={part.date} check={{ tooltip, onOpen: open(part.evidence_id) }} />,
          amount: part.amount ? <Num written={amountText(part.amount, part.currency)} check={{ tooltip, onOpen: open(part.evidence_id) }} /> : "",
        }}
      />
    );
  }
  return (
    <Fill
      template={words.leadSignedMany}
      slots={{
        count: <Num count={part.count} />,
        first_signed_date: <Num date={part.first_date} />,
        last_signed_date: <Num date={part.last_date} />,
      }}
    />
  );
}

function Lead({ trail }: { trail: Trail }) {
  const { lead } = trail;
  const parts = lead.parts.map((part) => leadPart(part, trail));
  const joined = parts.flatMap((part, index) => [
    index > 0 ? (index === parts.length - 1 ? (parts.length === 2 ? words.join.pair : words.join.last) : words.join.list) : null,
    <span key={index}>{part}</span>,
  ]);
  const missing = lead.missing ? words.missingNoun[lead.missing] : null;
  const through = trail.data_through ?? trail.as_of;
  return (
    <div data-lead className="mt-6 max-w-prose">
      <p className="text-h3 text-ink-heading">
        {parts.length > 0 && <Fill template={words.lead} slots={{ parts: <>{joined}</> }} />}
        {lead.no_estimate && <> {words.noEstimate}</>}
        {missing && (
          <>
            {parts.length > 0 && " "}
            <Fill template={words.leadMissing} slots={{ missing, data_through: <Num date={through} /> }} />
          </>
        )}
      </p>
      {(lead.bids.length > 0 || lead.paragraphs !== null) && (
        <p className="mt-2 text-body text-ink">
          {lead.bids.length > 0 && <LeadBids trail={trail} />}
          {lead.bids.length > 0 && lead.paragraphs !== null && " "}
          {lead.paragraphs !== null &&
            (lead.paragraphs > 0 ? (
              <Fill
                template={words.leadParagraphs(lead.paragraphs === 1, lead.many_contracts)}
                slots={{ count: <Num count={lead.paragraphs} check={{ tooltip: words.fromParagraphs }} /> }}
              />
            ) : lead.many_contracts ? (
              words.leadNoParagraphsMany
            ) : (
              words.leadNoParagraphs
            ))}
        </p>
      )}
      <p className="mt-4 text-caption text-ink-muted">{copy.trail.legend}</p>
    </div>
  );
}

// The bids each award notice listed: "The award notice listed 11 bids.", or with two notices, "The award notices
// listed five and four bids." Each count opens its notice.
function LeadBids({ trail }: { trail: Trail }) {
  const listed = trail.lead.bids;
  const proposals = listed[0].proposals;
  const count = (bids: (typeof listed)[number]) => (
    <Num count={bids.count} check={{ tooltip: words.fromAwardNotice(bids.notice_id), onOpen: open(bids.evidence_id) }} />
  );
  if (listed.length === 1) return <Fill template={words.leadBids(listed[0].count === 1, proposals)} slots={{ count: count(listed[0]) }} />;
  return <Fill template={words.leadBidsMany(proposals)} slots={{ counts: <Joined items={listed.map(count)} /> }} />;
}

function Pairs({ trail }: { trail: Trail }) {
  return (
    <dl className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
      <div className="min-w-0">
        <dt className="text-caption text-ink-muted">{words.label.ref}</dt>
        <dd className="text-small font-mono font-medium wrap-anywhere text-ink">{trail.activity.step_reference}</dd>
      </div>
      {trail.activity.implementing_agency && (
        <div className="min-w-0">
          <dt className="text-caption text-ink-muted">{words.label.agency}</dt>
          <dd className="text-small text-ink">{trail.activity.implementing_agency}</dd>
        </div>
      )}
    </dl>
  );
}

// The labelled pairs while the activity loads, above the page's purpose, as the loaded page has them.
function PairsSkeleton() {
  return (
    <div aria-hidden="true" className="mt-2 flex flex-wrap gap-x-6 gap-y-1">
      <SkeletonText className="max-w-full" widths={["w-24 max-w-full", "w-48 max-w-full"]} />
      <SkeletonText className="max-w-full" widths={["w-32 max-w-full", "w-56 max-w-full"]} />
    </div>
  );
}

function TrailSkeleton() {
  return (
    <div aria-hidden="true">
      <div className="mt-6 max-w-prose">
        <SkeletonText className="text-h3" widths={["w-full", "w-4/5"]} />
        <SkeletonLine className="mt-4 text-caption" width="w-3/4" />
      </div>
      <ol className="mt-6 flex flex-col gap-4 @md/page:gap-6">
        {/* The plan, notice, bids and contract stages, each as tall as it usually is, then two paragraph cards. */}
        {["h-70", "h-40", "h-60", "h-50", "h-45"].map((height) => (
          <li key={height} className="grid grid-cols-[1rem_minmax(0,1fr)] gap-x-3 @md/page:grid-cols-[1.5rem_minmax(0,1fr)] @md/page:gap-x-4">
            <span className="relative">
              <span className="absolute top-5 left-0.5 block size-3 rounded-pill bg-surface-2 @md/page:top-7 @md/page:left-1 @md/page:size-4" />
            </span>
            <Skeleton className={`w-full ${height}`} radius="rounded-md" />
          </li>
        ))}
      </ol>
    </div>
  );
}

export function ActivityPage({ pid, stepRef }: { pid: string; stepRef: string }) {
  const here = useStore(address);
  const [load, retry] = useLoad<Trail>(withReadParams(`/api/projects/${encodeURIComponent(pid)}/packages/${encodeURIComponent(stepRef)}`, here.search));
  const title = useRef<HTMLHeadingElement>(null);
  const data = load.status === "ready" ? load.data : null;

  useEffect(() => {
    if (load.status === "ready" && load.afterRetry) title.current?.focus();
  }, [load]);
  useEffect(() => {
    setPageTitle(words.docTitle(stepRef));
  }, [stepRef]);
  // A STEP reference opened under another project moves to its own project's address, in place.
  useEffect(() => {
    if (data?.moved && data.activity.href) navigate(data.activity.href + window.location.search + window.location.hash, { replace: true });
  }, [data]);

  const notFound = load.status === "error" && load.error?.status === 404;
  const idText = <ProjectIdText pid={pid} />;
  const projectCrumb = data?.activity.display_name
    ? { text: <Fill template={copy.breadcrumb.project} slots={{ name: data.activity.display_name, pid: idText }} />, href: `/projects/${pid}` }
    : { text: <Fill template={copy.breadcrumb.projectId} slots={{ pid: idText }} />, href: `/projects/${pid}` };
  const trail = [
    { text: copy.breadcrumb.projects, href: "/projects" },
    projectCrumb,
    { text: words.crumbProcurement, href: `/projects/${pid}/procurement` },
    { text: <span className="font-mono">{stepRef}</span> },
  ];
  const heading = data?.activity.description ? data.activity.description : fill(words.titleFallback, { stepRef });

  // The column keeps its place and width when the drawer opens from 1200 px (DESIGN.md section 4, Document column).
  return (
    <DocumentColumn>
      <div data-activity-page={notFound ? "not-found" : load.status}>
        <Breadcrumb trail={trail} />
        <h1 ref={title} tabIndex={-1} className="mt-4 text-h1 wrap-break-word text-ink-heading focus:outline-none">
          {notFound || load.status !== "ready" ? (
            <Fill template={words.titleFallback} slots={{ stepRef: <span className="font-mono font-medium wrap-anywhere">{stepRef}</span> }} />
          ) : (
            heading
          )}
        </h1>
        {notFound ? (
          <EmptyState
            className="mt-6"
            title={<Fill template={words.notFoundTitle} slots={{ stepRef: <span className="font-mono wrap-anywhere">{stepRef}</span>, pid: <ProjectId pid={pid} /> }} />}
            body={words.notFoundBody}
            link={{ href: `/projects/${pid}/procurement`, text: <Fill template={words.notFoundLink} slots={{ pid }} /> }}
          />
        ) : load.status === "error" ? (
          <div className="mt-6">
            <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
          </div>
        ) : data ? (
          <>
            <Pairs trail={data} />
            <p className="mt-2 max-w-prose text-body text-ink-muted">{words.purpose}</p>
            <Lead trail={data} />
            <div className="mt-6">
              <ContractTrail trail={data} />
            </div>
          </>
        ) : (
          <>
            <PairsSkeleton />
            <p className="mt-2 max-w-prose text-body text-ink-muted">{words.purpose}</p>
            <TrailSkeleton />
          </>
        )}
        <p role="status" className="sr-only">
          {load.status === "loading" ? (load.slow ? words.stillLoading : words.loading) : ""}
        </p>
        {load.status === "loading" && load.slow && <p className="mt-2 text-caption text-ink-muted">{words.stillLoading}</p>}
      </div>
    </DocumentColumn>
  );
}
