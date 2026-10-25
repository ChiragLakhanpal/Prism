// What each route shows until its own ticket fills it (the 06 design brief): its title, one or
// two short sentences that say what it is for, and an empty-state card that says, in the first
// person, what the page can't show yet and what will appear there. The not-found pages have no card: their purpose
// already says what to do, and their one link follows it.
//
// All projects, a project's page and Check a plan (ticket 10), the package workspace (ticket 12), the
// Data tab's three pages (ticket 16), the Drafts tab's pages (ticket 35), the Lessons tab's pages
// (ticket 29), and a project's Summary, Documents and the source view (ticket 21) are built, so
// they render their own pages.
import { EmptyState } from "./components/Card";
import { PageHeader, WithIds } from "./components/PageHeader";
import { TextLink } from "./components/TextLink";
import { copy } from "./copy";
import { CheckPlanPage } from "./pages/CheckPlanPage";
import { DataPage } from "./pages/data/DataPage";
import { DraftNewPage } from "./pages/DraftNewPage";
import { DraftPage } from "./pages/DraftPage";
import { DraftsPage } from "./pages/DraftsPage";
import { FollowingPage } from "./pages/FollowingPage";
import { LessonsPage, QueuePage } from "./pages/LessonsPages";
import { ReviewPage } from "./pages/ReviewPage";
import { PackagePage } from "./pages/PackagePage";
import { PackagesPage } from "./pages/PackagesPage";
import { PlannedPackagePage } from "./pages/PlannedPackagePage";
import { ProjectPage } from "./pages/ProjectPage";
import { ProjectsPage } from "./pages/ProjectsPage";
import { SourcePage } from "./pages/SourcePage";
import type { Match, ProjectTab } from "./routes";

export function RoutePage({ match, search = "" }: { match: Match; search?: string }) {
  const { pid, agencyId, version } = match.values;
  if (match.key === "projects") return <ProjectsPage />;
  if (match.key === "following") return <FollowingPage search={search} />;
  if (match.key === "project") return <ProjectPage pid={pid} tab={match.values.tab as ProjectTab} />;
  if (match.key === "document") return <SourcePage pid={pid} doc={match.values.doc} search={search} />;
  if (match.key === "checkPlan") return <CheckPlanPage pid={pid} agencyId={agencyId} version={version} />;
  if (match.key === "data" || match.key === "dataSources" || match.key === "dataHow") return <DataPage match={match} search={search} />;
  if (match.key === "drafts") return <DraftsPage search={search} />;
  if (match.key === "draftNew") return <DraftNewPage search={search} />;
  if (match.key === "draft") return <DraftPage draftId={match.values.id} search={search} />;
  if (match.key === "lessons") return <LessonsPage search={search} />;
  if (match.key === "lessonsQueue") return <QueuePage search={search} />;
  if (match.key === "lessonReview") return <ReviewPage itemId={match.values.itemId} />;
  if (match.key === "package") return <PackagePage stepRef={match.values.id} />;
  if (match.key === "packages") return <PackagesPage search={search} />;
  if (match.key === "packageNew") return <PlannedPackagePage packageId={null} search={search} />;
  if (match.key === "plannedPackage") return <PlannedPackagePage packageId={match.values.id} search={search} />;
  return (
    <div className="layout-grid">
      <div className="col-span-12 @md/page:col-span-8">
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
