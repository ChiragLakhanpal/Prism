// The app: the frame every page shares (web/src/components/Frame.tsx), around the page the address
// names (web/src/routes.ts). The navy bar carries the World Bank logo, the wordmark, the box and the view switch
// (ticket 93); the sidebar beside the page, Home, the sections and the data-freshness stamp under Data (ticket 92);
// the page, its alert slot, title, purpose and empty state; and the footer.
//
// The app reads who is viewing (/api/me) and the stamp (/api/freshness) once per page load and
// keeps both across route changes. A route change updates the browser tab's title, scrolls to the
// top and moves focus to the new h1, and a stamp that failed tries again. Opening or closing the
// evidence drawer changes only the address's ?evidence=, which is not a route change.
//
// Ticket 14 adds the box's intents, the answer panel at the top of the page and the evidence drawer
// beside it. The answer belongs to the history entry it was asked on (web/src/lib/answer.ts).
import { useEffect, useRef, useState } from "react";
import { createPortal, flushSync } from "react-dom";
import logo from "./assets/world-bank-logo.svg";
import { Alert } from "./components/Alert";
import { AnswerPanel, scrollToAnswer } from "./components/AnswerPanel";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { Frame } from "./components/Frame";
import { IntentBox } from "./components/IntentBox";
import { AlertSlot } from "./components/PageAlert";
import { RETURNING } from "./components/Popover";
import { Sidebar } from "./components/Sidebar";
import { SECTIONS, TopNav, type NavMode, type Section, type Viewer } from "./components/TopNav";
import { ViewBanner } from "./components/ViewBanner";
import { copy } from "./copy";
import { answer, ask, earlier, removedScopes } from "./lib/answer";
import { getJson, type Me } from "./lib/api";
import { languageName, workingLanguage, type WorkingLanguage } from "./lib/lang";
import { draftScope } from "./lib/drafts";
import { askRows, type AskPage } from "./lib/intents";
import { FOLLOWING_HREF, staffRole } from "./lib/following";
import { officerAgency } from "./lib/uploads";
import { startHereVisible } from "./lib/home";
import { startHereList } from "./lib/startHere";
import { drawerClosed, evidenceIn, origin, routeOf, visited } from "./lib/evidence";
import { readStamp, retryStamp, stamp, type Problem } from "./lib/freshness";
import { formatDate } from "./lib/format";
import { agencyInSentence, appliedView, asOfOf, viewOf, withMode, type AppliedView, type Preview } from "./lib/view";
import { address, navigate, startRouter } from "./lib/router";
import { createStore, useStore } from "./lib/store";
import { pageTitle } from "./lib/title";
import { RoutePage } from "./RoutePage";
import { fill, isDay, matchRoute, type Match, type PageKey } from "./routes";

const viewer = createStore<Viewer>({ status: "loading" });

// What the address asks of /api/me: its ?lang= (ticket 42), and its ?view= and ?asof= exactly as written (ticket 40),
// so the server says which language, view and date it applied, and why it could not apply what was asked.
const ASKED = ["lang", "view", "asof"] as const;
const askedOf = (search: string) => {
  const params = new URLSearchParams(search);
  const kept = new URLSearchParams();
  for (const key of ASKED) {
    const value = params.get(key);
    if (value !== null) kept.set(key, value);
  }
  return kept.toString();
};

// The address /api/me last answered for, beside what it applied, so a fresh view change shows the address's mode
// until the server confirms it (the 40 brief, section 9).
const answeredFor = createStore<string | null>(null);

async function readViewer(search: string = window.location.search) {
  const asked = askedOf(search);
  try {
    const me = await getJson<Me>(asked ? `/api/me?${asked}` : "/api/me");
    viewer.set(me.signed_in && me.email ? { status: "signed-in", email: me.email, agency: me.agency?.name ?? null }
      : me.signed_in ? { status: "error" } : { status: "signed-out" });
    staffRole.set(Boolean(me.staff));
    officerAgency.set(me.agency ?? null);
    workingLanguage.set(me.language ?? null);
    // Whether Home shows its Start here strip (ticket 41), so Home keeps its room while it loads.
    startHereVisible.set(Boolean(me.start_here_visible));
    // The questions the box suggests while it is focused and empty (ticket 112).
    askRows.set(me.ask ?? []);
    appliedView.set(me.applied && me.preview_agency ? ({
      own: me.own_view ?? "staff", views: me.views ?? [], applied: me.applied, preview_agency: me.preview_agency,
      tabs: me.tabs ?? [], hidden: me.hidden ?? [], capabilities: me.capabilities ?? [], reasons: me.reasons ?? {},
      asof: me.asof ?? { applied: null, problem: null },
    } as AppliedView) : null);
    answeredFor.set(asked);
  } catch {
    viewer.set({ status: "error" });
    staffRole.set(false);
    officerAgency.set(null);
    appliedView.set(null);
    askRows.set([]);
    answeredFor.set(asked);
  }
}

// The page's scope for the box's chip: a project's P-code on its pages, a package's STEP reference
// (or its id until it has one) on a package's. page is which of the box's suggestions the page shows (ticket 112):
// a plan check's are its own, and a page with no scope shows Home's.
function scopeOf(match: Match, draftProject: string | null): { scope: string | null; kind: "project" | "package"; page: AskPage | null } {
  // A draft's page carries the draft's project once the draft has loaded (the 35 brief, section 11).
  if (match.key === "draft" || match.key === "draftNew") return { scope: draftProject, kind: "project", page: "project" };
  if (match.key === "package") return { scope: match.values.id ?? null, kind: "package", page: "package" };
  if (match.key === "activity") return { scope: match.values.stepRef ?? null, kind: "package", page: "package" };
  if (match.key === "checkPlan") return { scope: match.values.pid ?? null, kind: "project", page: "plan_check" };
  if (match.key === "project" || match.key === "document") return { scope: match.values.pid ?? null, kind: "project", page: "project" };
  return { scope: null, kind: "project", page: null };
}

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

// Focus after the drawer closes: back to the marker that opened it, if focus was in the drawer. If
// that marker is gone, to the page's h1.
function returnFocus() {
  const from = origin.get();
  const marker =
    from?.marker && from.marker.isConnected
      ? from.marker
      : from
        ? (document.querySelector<HTMLElement>(`[data-citation-id="${CSS.escape(from.id)}"][data-sentence="${from.sentence ?? ""}"]`) ??
          (from.fallback?.isConnected ? from.fallback : null))
        : null;
  // Focus given back to a marker does not open its evidence card over the answer again; the card
  // opens when a person moves the focus or the pointer there (web/src/components/Popover.tsx).
  if (marker) {
    marker.setAttribute(RETURNING, "");
    marker.focus();
  } else document.querySelector<HTMLElement>("main h1")?.focus();
}

// The alert slot's alerts other than the view banners: errors first, then what the address asks for that the server
// could not apply (the 40 brief, 6.3). The banners for a preview and a past date sit between the two.
function alerts(problem: Problem, search: string, language: WorkingLanguage | null, shown: AppliedView | null): {
  errors: { state: "error" | "info"; text: string }[];
  notes: { state: "error" | "info"; text: string }[];
} {
  const params = new URLSearchParams(search);
  const errors: { state: "error" | "info"; text: string }[] = [];
  const notes: { state: "error" | "info"; text: string }[] = [];
  if (problem === "no_access") errors.push({ state: "error", text: copy.alerts.noAccess });
  if (problem === "no_identity") errors.push({ state: "error", text: copy.alerts.noIdentity });
  // A ?lang= no working language matches: I use the language in effect without the link, and never repeat the link's
  // text (the 42 brief, section 5.2).
  if (language?.link === "unknown" && params.get("lang") !== null) notes.push({ state: "info", text: copy.language.alertUnknown(languageName(language.code)) });
  const view = params.get("view");
  const unknownView = shown?.applied.problem === "unknown" || (view !== null && !["staff", "piu", "public"].includes(view));
  if (unknownView) notes.push({ state: "info", text: shown?.own === "piu" ? copy.alerts.viewUnknownOfficer : copy.alerts.viewUnknown });
  const asOf = params.get("asof");
  if (asOf !== null && !isDay(asOf)) notes.push({ state: "info", text: copy.alerts.asOfUnreadable });
  else if (shown?.asof.problem === "not_past") notes.push({ state: "info", text: copy.alerts.asOfNotPast });
  return { errors, notes };
}

// The visually hidden line that says the mode, which describes every page's h1 and, in a preview, the Menu button.
const MODE_LINE = "strata-mode-line";

function modeWords(preview: Preview | null, asOf: string | null): { line: string | null; title: (title: string) => string } {
  const words = copy.view;
  const date = asOf ? formatDate(asOf) : null;
  const short = asOf ? formatDate(asOf, { style: "short" }) : null;
  if (preview && date && short) {
    return { line: preview === "piu" ? words.mode.piuAsOf(date) : words.mode.publicAsOf(date),
             title: (title) => (preview === "piu" ? words.title.piuAsOf(title, short) : words.title.publicAsOf(title, short)) };
  }
  if (preview) return { line: words.mode[preview], title: (title) => words.title[preview](title) };
  if (date && short) return { line: words.mode.asOf(date), title: (title) => words.title.asOf(title, short) };
  return { line: null, title: (title) => copy.pageTitle(title) };
}

// The pages that show today's state whatever the as-of date, and the sentence the as-of banner adds on each, so the
// banner never claims a date the page does not keep (the 35, 38 and 40 briefs).
const TODAY_STATE: Partial<Record<PageKey, keyof typeof copy.view.banner>> = {
  checkMyPlan: "uploads",
  uploadCheck: "uploads",
  packages: "packages",
  lessonsQueue: "reviewQueue",
  lessonReview: "reviewQueue",
  lessonsReports: "passageReports",
  passageReport: "passageReports",
  lessonsJudging: "judging",
  judgingQuery: "judging",
};

function todayStateLine(match: Match): string | null {
  const key = match.section === "drafts" ? "drafts" : TODAY_STATE[match.key];
  const line = key ? copy.view.banner[key] : null;
  return typeof line === "string" ? line : null;
}

export function App() {
  const here = useStore(address);
  const who = useStore(viewer);
  const staff = useStore(staffRole);
  const { freshness, problem } = useStore(stamp);
  const run = useStore(answer);
  const kept = useStore(earlier);
  const seen = useStore(visited);
  const from = useStore(origin);
  const narrow = useNarrow();
  const match = matchRoute(here.pathname);
  const draftProject = useStore(draftScope);
  const { scope, kind, page: askPage } = scopeOf(match, draftProject);
  const evidenceId = evidenceIn(here.search);
  const language = useStore(workingLanguage);
  // The language of answers and drafts (ticket 42), and the view and date (ticket 40), follow the address as it changes:
  // /api/me says again what the server applies.
  const asked = askedOf(here.search);
  const firstAsked = useRef(asked);
  useEffect(() => {
    if (firstAsked.current === asked) return;
    firstAsked.current = asked;
    void readViewer(here.search);
  }, [asked]);
  // What the server applied to this address, or null while it has not answered for it. Until it has, a preview's pill
  // and banner come from the address, and a page the preview may hide waits.
  const applied = useStore(appliedView);
  const answered = useStore(answeredFor);
  const fresh = applied && answered === asked ? applied : null;
  const addressPreview = viewOf(here.search) === "staff" ? null : (viewOf(here.search) as Preview);
  const preview: Preview | null = fresh ? (fresh.applied.preview ? (fresh.applied.view as Preview) : null) : addressPreview;
  // The address's date, unless the server said it could not apply it (a date of today or later).
  const asOf = fresh?.asof.problem ? null : asOfOf(here.search);
  const own = applied?.own ?? (who.status === "signed-in" && who.agency ? "piu" : "staff");
  const navMode: NavMode = {
    own,
    preview,
    offered: applied?.views ?? [],
    agency: applied ? agencyInSentence(applied) : null,
    tabs: fresh ? (fresh.tabs as Section[]) : preview ? null : SECTIONS.map((section) => section.key),
    hidden: fresh?.hidden ?? [],
    pathname: match.key === "notFound" || match.key === "notAProject" ? "/" : here.pathname,
    search: here.search,
    asOf,
    unknown: !applied && !preview && who.status === "loading",
  };
  const mode = modeWords(preview, asOf);
  // Start here in the sidebar (ticket 114): World Bank staff in their own view, today, while GET /api/me says the strip
  // shows, once Home has kept its links in this browser. Remove takes it off every page at once.
  const stripShows = useStore(startHereVisible);
  const startHereKept = useStore(startHereList);
  const startHere = stripShows && own === "staff" && !preview && !asOf ? startHereKept : null;
  // The answer shows on the history entry it was asked on: the current one, or the last one finished there.
  const shown = run && run.asked.key === here.key ? run : (kept[here.key] ?? null);

  useEffect(() => {
    const stop = startRouter();
    readStamp();
    void readViewer();
    const onVisible = () => document.visibilityState === "visible" && retryStamp();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      stop();
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);

  // A lowercase p in a project ID: the address shows the uppercase form, in place.
  useEffect(() => {
    if (match.canonical) navigate(match.canonical + window.location.search + window.location.hash, { replace: true });
  }, [match.canonical]);

  // A page with sub-pages, such as the Data tab's, names the sub-page in the browser tab.
  // A page that knows a more specific title once its data loads, such as a draft, sets it (lib/title.ts).
  // The public view's Home is titled Home: "Your briefing" is about plans and drafts, which it does not have (ticket 41).
  const words: { title: string; documentTitle?: string } = match.key === "home" && preview === "public" ? { title: copy.home.publicTitle } : copy.pages[match.key];
  const ownTitle = useStore(pageTitle);
  const title = ownTitle && ownTitle.path === here.pathname ? ownTitle.title : fill(words.documentTitle ?? words.title, match.values);
  // In a preview or as of a date, the browser tab names the mode too (the 40 brief, 6.2).
  const documentTitle = mode.title(title);
  useEffect(() => {
    document.title = documentTitle;
  }, [documentTitle]);

  // A route change, but not the first page: scroll to the top, focus the new title, and try the
  // stamp again if it failed. A move within one tab's pages, such as a Data sub-tab or "Show all
  // sources", focuses the new page's lead instead, as the title has not changed (the 16 brief).
  // A new page brings its scope chip back. Opening or closing the evidence drawer changes only
  // ?evidence=, which is not a route change (routeOf), so it leaves focus where the drawer put it;
  // a change to any other part of the address, such as ?asof=, is one. An address that names a
  // section of the page, such as How Strata works' #what-i-dont-do from the link under a refusal
  // (ticket 24), scrolls to that section and focuses its heading instead, on arrival or on load.
  const route = routeOf(here);
  // The section of the page the address names, by the heading that takes focus.
  const namedSection = () => {
    const id = decodeURIComponent(window.location.hash.slice(1));
    return id ? document.querySelector<HTMLElement>(`main [id="${CSS.escape(id)}"][tabindex="-1"]`) : null;
  };
  useEffect(() => {
    const named = namedSection();
    named?.scrollIntoView();
    named?.focus({ preventScroll: true });
  }, []);
  const lastRoute = useRef(route);
  const lastPath = useRef(here.pathname);
  const section = useRef(match.section);
  useEffect(() => {
    const moved = lastRoute.current !== route;
    lastRoute.current = route;
    // A move that keeps the page and changes only its query, such as Next page on All projects or in a
    // document (ticket 21), focuses the page's own lead for that, so the new range is read.
    const samePage = lastPath.current === here.pathname;
    lastPath.current = here.pathname;
    const within = section.current !== undefined && section.current === match.section;
    section.current = match.section;
    if (!moved || here.moves === 0 || here.quiet) return;
    removedScopes.set(new Set());
    retryStamp();
    const named = namedSection();
    if (named) {
      named.scrollIntoView();
      named.focus({ preventScroll: true });
      return;
    }
    window.scrollTo(0, 0);
    // Back to a page with the evidence drawer open, such as from the source view the drawer's "Open at
    // page" opened (ticket 21): the drawer's heading takes focus, where the person was.
    const drawerHeading = evidenceIn(here.search) ? document.querySelector<HTMLElement>("[data-evidence-drawer] h2") : null;
    const pageLead = samePage ? document.querySelector<HTMLElement>("main [data-page-lead]") : null;
    const lead = within ? document.querySelector<HTMLElement>("main [data-lead]") : null;
    (drawerHeading ?? pageLead ?? lead ?? document.querySelector<HTMLElement>("main h1"))?.focus();
  }, [route, here.moves]);

  // After a view or date change, focus moves to the new banner, so its sentence is read; leaving a preview or going
  // back to today moves it to the h1 and says so politely (the 40 brief, 8.2).
  const previewBanner = useRef<HTMLElement>(null);
  const asOfBanner = useRef<HTMLElement>(null);
  const [announce, setAnnounce] = useState("");
  const lastMode = useRef({ preview, asOf });
  useEffect(() => {
    const was = lastMode.current;
    lastMode.current = { preview, asOf };
    if (was.preview === preview && was.asOf === asOf) return;
    // Two frames on, after the evidence drawer has given focus back to the mark that opened it (its onClosed waits one
    // frame), so a change made from inside the drawer, such as "See Strata as of this date", still lands on the banner.
    const later = (target: () => HTMLElement | null | undefined) =>
      requestAnimationFrame(() => requestAnimationFrame(() => target()?.focus()));
    if (asOf && asOf !== was.asOf) later(() => asOfBanner.current);
    else if (preview && preview !== was.preview) later(() => previewBanner.current);
    else {
      later(() => document.querySelector<HTMLElement>("main h1"));
      if (was.preview && !preview) setAnnounce(own === "piu" ? copy.view.status.leftPreviewOfficer : copy.view.status.leftPreview);
      else if (was.asOf && !asOf) setAnnounce(copy.view.status.backToToday);
    }
  }, [preview, asOf]);

  // Every page's h1 is described by the mode line while a mode is on, so "Lessons, heading level 1, Public preview."
  // is read on each page (the 40 brief, 8.4). Pages draw their h1 when they are ready, so this follows the page.
  useEffect(() => {
    const main = document.querySelector("main");
    if (!main) return;
    const mark = () => {
      const heading = main.querySelector("h1");
      if (!heading) return;
      if (mode.line && heading.getAttribute("aria-describedby") !== MODE_LINE) heading.setAttribute("aria-describedby", MODE_LINE);
      if (!mode.line && heading.getAttribute("aria-describedby") === MODE_LINE) heading.removeAttribute("aria-describedby");
    };
    mark();
    const observer = new MutationObserver(mark);
    observer.observe(main, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [mode.line]);

  // The panel is drawn at once, so the page can scroll to it: the box floats at the window's foot and the answer opens
  // at the top of the page column (ticket 113).
  const onAsk = (question: string, chip: string | null) => {
    flushSync(() =>
      ask({
        question,
        scope: chip,
        asOf,
        view: preview,
        // The language in effect: the link's, your saved choice, your team's or English, as the server said (ticket 42).
        lang: workingLanguage.get()?.code ?? null,
        key: address.get().key,
      }),
    );
    scrollToAnswer();
  };

  const slot = alerts(problem, here.search, language, fresh);
  // The banners (the 40 brief, 3.4): the preview first (whose view), then the date (when). The agency banner names the
  // agency from the roles file, so it waits for /api/me the first time.
  const previewText = preview === "piu" ? (applied ? copy.view.banner.piu(agencyInSentence(applied)) : null) : preview === "public" ? copy.view.banner.public : null;
  const today = todayStateLine(match);
  const asOfLine = asOf ? `${copy.view.banner.asOf(formatDate(asOf))}${today ? ` ${today}` : ""}` : null;
  const hiddenIn = fresh?.applied.preview && fresh.hidden.includes(match.key) ? (fresh.applied.view as Preview) : null;
  const pending = Boolean(preview && !fresh && who.status !== "error");
  // The alert slot's element, which a page's own alert goes into (PageAlert.tsx).
  const [alertSlot, setAlertSlot] = useState<HTMLDivElement | null>(null);
  return (
    <AlertSlot.Provider value={alertSlot}>
    <Frame
      nav={
        <TopNav
          logo={<img src={logo} width={120} height={24} alt={copy.nav.logo} className="block h-6 w-[120px]" />}
          viewer={who}
          mode={navMode}
          modeLineId={MODE_LINE}
        />
      }
      box={<IntentBox scope={scope} scopeKind={kind} page={askPage} onAsk={onAsk} />}
      sidebar={
        <Sidebar
          mode={navMode}
          viewer={who}
          current={match.key === "home" ? "home" : match.section}
          pathname={here.pathname}
          freshness={freshness}
          // World Bank staff open Following from Projects (ticket 37); a preview, and everyone else, All projects.
          projectsHref={staff && !preview ? FOLLOWING_HREF : undefined}
          startHere={startHere}
        />
      }
      inertPage={narrow && evidenceId !== null}
      aside={
        evidenceId && (
          <EvidenceDrawer
            id={evidenceId}
            run={shown}
            narrow={narrow}
            preview={preview !== null}
            asOf={asOf}
            onClosed={(inside) => {
              drawerClosed();
              // Focus goes back to the marker that opened it, and then the drawer's origin is done
              // with, so a later sheet opened from a link takes focus as a link's sheet should.
              const was = origin.get();
              requestAnimationFrame(() => {
                if (inside) returnFocus();
                if (origin.get() === was) origin.set(null);
              });
            }}
          />
        )
      }
    >
      {/* The page's top space follows the window, as its margins do, so the drawer opening beside it moves nothing. */}
      <div className="layout layout-grid pt-6 md:pt-8 lg:pt-10">
        {/* The alert slot frames everything on the page, the answer included (DESIGN.md section 5,
            Page header), so it sits above the answer panel. */}
        <p id={MODE_LINE} className="clip-visually">
          {mode.line}
        </p>
        {/* Outside the page's main, so a page's own status line is the only one in it. */}
        {createPortal(
          <p role="status" data-mode-status className="clip-visually">
            {announce}
          </p>,
          document.body,
        )}
        {/* The page's alert slot (ticket 94): always in the page, above the answer and the page's head, so a page whose
            one read failed puts its error alert here (PageAlert.tsx); it takes no room while it is empty. */}
        <div ref={setAlertSlot} data-alert-slot className="col-span-12 mb-6 flex flex-col gap-2 empty:hidden @md/page:col-span-8">
          {slot.errors.map((alert) => (
            <Alert key={alert.text} state={alert.state} live="alert">
              {alert.text}
            </Alert>
          ))}
          {previewText && (
            <ViewBanner ref={previewBanner} kind="preview" region={copy.view.banner.previewRegion} link={copy.view.banner.leave}
              href={withMode(here.pathname, here.search, { view: null })}>
              {previewText}
            </ViewBanner>
          )}
          {asOfLine && (
            <ViewBanner ref={asOfBanner} kind="asof" region={copy.view.banner.asOfRegion} link={copy.view.banner.back}
              href={withMode(here.pathname, here.search, { asof: null })}>
              {asOfLine}
            </ViewBanner>
          )}
          {slot.notes.map((alert) => (
            <Alert key={alert.text} state={alert.state}>
              {alert.text}
            </Alert>
          ))}
        </div>
        {shown && (
          <div className="col-span-12 @lg/page:col-span-8">
            <AnswerPanel
              run={shown}
              opened={{ id: evidenceId, sentence: from && from.id === evidenceId && from.serial === shown.serial ? from.sentence : null }}
              visited={seen}
            />
          </div>
        )}
        {/* Each page lays itself out on the same 12 columns: most keep to columns 1 to 8, and a
            table that needs the width, such as the plan check or the Data tab, spans all 12. */}
        <div className="col-span-12">
          {/* A project's tabs share one page, so its header and tab row stay in place between them. */}
          {/* A new view or date is a new page: every read on it carries them (ticket 40). */}
          <RoutePage key={`${match.frame ?? here.pathname}|${preview ?? ""}|${asOf ?? ""}`} match={match} search={here.search} hiddenIn={hiddenIn} pending={pending} />
        </div>
      </div>
    </Frame>
    </AlertSlot.Provider>
  );
}
