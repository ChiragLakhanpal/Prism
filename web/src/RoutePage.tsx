// What each route shows until its own ticket fills it (the 06 design brief): its title, one or
// two short sentences that say what it is for, and an empty-state card that says, in the first
// person, what the page can't show yet and what will appear there. The not-found pages have no card: their purpose
// already says what to do, and their one link follows it.
//
// All projects, a project's page and Check a plan (ticket 10), the package workspace (ticket 12), the
// Data tab's three pages (ticket 16), the Drafts tab's pages (ticket 35), the Lessons tab's pages
// (ticket 29), and a project's Summary, Documents and the source view (ticket 21) are built, so
// they render their own pages, as do the activity page and a project's Connections tab (ticket 22).
import { EmptyState } from "./components/Card";
import { Skeleton } from "./components/Skeleton";
import { PageHeader, WithIds } from "./components/PageHeader";
import { TextLink } from "./components/TextLink";
import { copy } from "./copy";
import { ActivityPage } from "./pages/ActivityPage";
import { CheckPlanPage } from "./pages/CheckPlanPage";
import { CheckMyPlanPage } from "./pages/CheckMyPlanPage";
import { UploadCheckPage } from "./pages/UploadCheckPage";
import { DataPage } from "./pages/data/DataPage";
import { DraftNewPage } from "./pages/DraftNewPage";
import { DraftPage } from "./pages/DraftPage";
import { DraftsPage } from "./pages/DraftsPage";
import { FollowingPage } from "./pages/FollowingPage";
import { HomePage } from "./pages/HomePage";
import { QueuePage } from "./pages/LessonsPages";
import { LessonsPage } from "./pages/LessonsTab";
import { ReviewPage } from "./pages/ReviewPage";
import { JudgingPage, JudgingQueryPage } from "./pages/JudgingPages";
import { PassageReportPage, PassageReportsPage } from "./pages/PassageReportsPages";
import { PackagePage } from "./pages/PackagePage";
import { PackagesPage } from "./pages/PackagesPage";
import { PlannedPackagePage } from "./pages/PlannedPackagePage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SourcePage } from "./pages/SourcePage";
import type { Match, ProjectTab } from "./routes";

// A page the applied view does not show (ticket 40; the 40 brief, 3.7 and 6.4): it keeps its address, its section's
// name is the h1, and an empty-state card says why, in the words its own brief wrote when it wrote some. The server
// never sends what the page holds, so the page itself is not drawn. Like the Drafts list and Lessons it stands in for, it
// takes all 12 columns (ticket 110), and the card's sentences keep to the width of prose.
function NotInView({ match, view }: { match: Match; view: "piu" | "public" }) {
  const words = copy.view.hidden;
  const name = copy.view.name[view];
  const card: { title: string; body: string } =
    match.key === "packages"
      ? { title: copy.packageWorkspace.publicTitle, body: words.packagesBody }
      : match.key === "package" || match.key === "packageNew" || match.key === "plannedPackage"
        ? { title: copy.packageWorkspace.publicTitle, body: copy.packageWorkspace.publicBody }
        : match.key === "drafts" || match.key === "draft" || match.key === "draftNew"
          ? { title: copy.draft.page.publicTitle, body: copy.draft.page.publicBody }
          : match.key === "following"
            ? view === "piu"
              ? { title: copy.following.previewPiuTitle, body: copy.following.previewPiuBody }
              : { title: copy.following.previewPublicTitle, body: copy.following.previewPublicBody }
            : { title: words.title(name), body: words.body };
  return (
    <div className="layout-grid" data-not-in-view={match.key}>
      <div className="col-span-12 min-w-0">
        <PageHeader title={match.section ? copy.nav.tabs[match.section] : copy.pages[match.key].title} />
        <EmptyState className="mt-6" title={card.title} body={card.body} link={{ href: "/projects", text: words.link }} />
      </div>
    </div>
  );
}

export function RoutePage({ match, search = "", hiddenIn = null, pending = false }: {
  match: Match;
  search?: string;
  // The preview whose view does not show this page, from GET /api/me (ticket 40), or null.
  hiddenIn?: "piu" | "public" | null;
  // A preview whose rules the server has not confirmed yet: the page waits, so nothing it hides is drawn.
  pending?: boolean;
}) {
  const { pid, agencyId, version } = match.values;
  if (pending) return <Skeleton className="h-8 w-3/5 max-w-[560px]" />;
  if (hiddenIn) return <NotInView match={match} view={hiddenIn} />;
  // Home (ticket 41) draws the briefing for World Bank staff, an officer's Home, or the public's, as the server applies.
  if (match.key === "home") return <HomePage />;
  if (match.key === "projects") return <ProjectsPage />;
  if (match.key === "following") return <FollowingPage search={search} />;
  if (match.key === "project") return <ProjectPage pid={pid} tab={match.values.tab as ProjectTab} />;
  if (match.key === "activity") return <ActivityPage pid={pid} stepRef={match.values.stepRef} />;
  if (match.key === "document") return <SourcePage pid={pid} doc={match.values.doc} search={search} />;
  if (match.key === "checkPlan") return <CheckPlanPage pid={pid} agencyId={agencyId} version={version} />;
  if (match.key === "data" || match.key === "dataSources" || match.key === "dataHow") return <DataPage match={match} search={search} />;
  if (match.key === "drafts") return <DraftsPage search={search} />;
  if (match.key === "draftNew") return <DraftNewPage search={search} />;
  if (match.key === "draft") return <DraftPage draftId={match.values.id} search={search} />;
  if (match.key === "lessons") return <LessonsPage search={search} />;
  if (match.key === "lessonsQueue") return <QueuePage search={search} />;
  if (match.key === "lessonReview") return <ReviewPage itemId={match.values.itemId} />;
  if (match.key === "lessonsReports") return <PassageReportsPage search={search} />;
  if (match.key === "passageReport") return <PassageReportPage groupId={match.values.groupId} />;
  if (match.key === "lessonsJudging") return <JudgingPage search={search} />;
  if (match.key === "judgingQuery") return <JudgingQueryPage queryId={match.values.queryId} search={search} />;
  if (match.key === "package") return <PackagePage stepRef={match.values.id} />;
  if (match.key === "packages") return <PackagesPage search={search} />;
  if (match.key === "packageNew") return <PlannedPackagePage packageId={null} search={search} />;
  if (match.key === "checkMyPlan") return <CheckMyPlanPage search={search} />;
  if (match.key === "uploadCheck") return <UploadCheckPage uploadId={match.values.id} search={search} />;
  if (match.key === "plannedPackage") return <PlannedPackagePage packageId={match.values.id} search={search} />;
  return (
    <div className="layout-grid">
      <div className="col-span-12 min-w-0">
        <PlaceholderPage match={match} />
      </div>
    </div>
  );
}

function PlaceholderPage({ match }: { match: Match }) {
  const words: { title: string; purpose: string; emptyTitle?: string; emptyBody?: string; link?: string } = copy.pages[match.key];
  const link = words.link && match.linkHref ? { href: match.linkHref, text: <WithIds template={words.link} values={match.values} /> } : undefined;
  return (
    <>
      <PageHeader title={<WithIds template={words.title} values={match.values} />} purpose={words.purpose} />
      {words.emptyTitle && words.emptyBody ? (
        <EmptyState
          className="mt-6 @lg/page:mt-8"
          title={<WithIds whole template={words.emptyTitle} values={match.values} />}
          body={words.emptyBody}
          link={link}
        />
      ) : (
        link && (
          <p className="mt-4 text-body">
            <TextLink href={link.href}>{link.text}</TextLink>
          </p>
        )
      )}
    </>
  );
}
