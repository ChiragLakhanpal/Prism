// The app: the frame every page shares (web/src/components/Frame.tsx), around the page the address
// names (web/src/routes.ts). The navy bar carries the World Bank logo, the wordmark, the five tabs
// and the view switch; the band, the box and the data-freshness stamp; the page, its alert slot,
// title, purpose and empty state; and the footer.
//
// The app reads who is viewing (/api/me) and the stamp (/api/freshness) once per page load and
// keeps both across route changes. A route change updates the browser tab's title, scrolls to the
// top and moves focus to the new h1, and a stamp that failed tries again. Opening or closing the
// evidence drawer changes only the address's ?evidence=, which is not a route change.
//
// Ticket 14 adds the box's intents, the answer panel at the top of the page and the evidence drawer
// beside it. The answer belongs to the history entry it was asked on (web/src/lib/answer.ts).
import { useEffect, useRef, useState } from "react";
import logo from "./assets/world-bank-logo.svg";
import { Alert } from "./components/Alert";
import { AnswerPanel } from "./components/AnswerPanel";
import { BoxBand, FreshnessStamp } from "./components/BoxBand";
import { EvidenceDrawer } from "./components/EvidenceDrawer";
import { Frame } from "./components/Frame";
import { IntentBox } from "./components/IntentBox";
import { RETURNING } from "./components/Popover";
import { TopNav, type Viewer } from "./components/TopNav";
import { copy } from "./copy";
import { answer, ask, removedScopes } from "./lib/answer";
import { getJson, type Me } from "./lib/api";
import { draftScope } from "./lib/drafts";
import { drawerClosed, evidenceIn, origin, routeOf, visited } from "./lib/evidence";
import { readStamp, retryStamp, stamp, type Problem } from "./lib/freshness";
import { formatDate } from "./lib/format";
import { address, navigate, startRouter } from "./lib/router";
import { createStore, useStore } from "./lib/store";
import { pageTitle } from "./lib/title";
import { RoutePage } from "./RoutePage";
import { fill, isDay, matchRoute, type Match } from "./routes";

const viewer = createStore<Viewer>({ status: "loading" });

async function readViewer() {
  try {
    const me = await getJson<Me>("/api/me");
    viewer.set(me.signed_in && me.email ? { status: "signed-in", email: me.email } : me.signed_in ? { status: "error" } : { status: "signed-out" });
  } catch {
    viewer.set({ status: "error" });
  }
}

// The page's scope for the box's chip: a project's P-code on its pages, a package's STEP reference
// (or its id until it has one) on a package's.
function scopeOf(match: Match, draftProject: string | null): { scope: string | null; kind: "project" | "package" } {
  // A draft's page carries the draft's project once the draft has loaded (the 35 brief, section 11).
  if (match.key === "draft" || match.key === "draftNew") return { scope: draftProject, kind: "project" };
  if (match.key === "package") return { scope: match.values.id ?? null, kind: "package" };
  if (match.key === "activity") return { scope: match.values.stepRef ?? null, kind: "package" };
  if (match.key === "project" || match.key === "checkPlan" || match.key === "document") return { scope: match.values.pid ?? null, kind: "project" };
  return { scope: null, kind: "project" };
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
        ? document.querySelector<HTMLElement>(`[data-citation-id="${CSS.escape(from.id)}"][data-sentence="${from.sentence ?? ""}"]`)
        : null;
  // Focus given back to a marker does not open its evidence card over the answer again; the card
  // opens when a person moves the focus or the pointer there (web/src/components/Popover.tsx).
  if (marker) {
    marker.setAttribute(RETURNING, "");
    marker.focus();
  } else document.querySelector<HTMLElement>("main h1")?.focus();
}

const VIEW_ALERTS: Record<string, string> = { piu: copy.alerts.viewPiu, public: copy.alerts.viewPublic };
const DRAFT_PAGES: ReadonlySet<string> = new Set(["drafts", "draft", "draftNew"]);

// The alert slot: errors first, then what the address asks for that I can't show yet. Ticket 40
// replaces the view and as-of alerts with its preview and as-of banners in this same slot.
function alerts(problem: Problem, search: string, appliesAsOf: boolean, page: string): { state: "error" | "info"; text: string }[] {
  const params = new URLSearchParams(search);
  const found: { state: "error" | "info"; text: string }[] = [];
  if (problem === "no_access") found.push({ state: "error", text: copy.alerts.noAccess });
  if (problem === "no_identity") found.push({ state: "error", text: copy.alerts.noIdentity });
  const view = params.get("view");
  // The draft pages apply the implementing agency and public previews themselves (ticket 35): they show
  // what each preview holds, so the alert that says the page shows the staff view would be untrue there.
  const appliesView = (view === "piu" || view === "public") && DRAFT_PAGES.has(page);
  if (view !== null && view !== "staff" && !appliesView) found.push({ state: "info", text: VIEW_ALERTS[view] ?? copy.alerts.viewUnknown });
  const asOf = params.get("asof");
  if (asOf !== null && !appliesAsOf) {
    found.push({ state: "info", text: isDay(asOf) ? copy.alerts.asOf(formatDate(asOf)) : copy.alerts.asOfUnreadable });
  }
  return found;
}

export function App() {
  const here = useStore(address);
  const who = useStore(viewer);
  const { freshness, problem } = useStore(stamp);
  const run = useStore(answer);
  const seen = useStore(visited);
  const from = useStore(origin);
  const narrow = useNarrow();
  const match = matchRoute(here.pathname);
  const draftProject = useStore(draftScope);
  const { scope, kind } = scopeOf(match, draftProject);
  const params = new URLSearchParams(here.search);
  const evidenceId = evidenceIn(here.search);
  const asOf = params.get("asof");
  const view = params.get("view");
  // The answer shows on the history entry it was asked on.
  const shown = run && run.asked.key === here.key ? run : null;

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
  const words: { title: string; documentTitle?: string } = copy.pages[match.key];
  const own = useStore(pageTitle);
  const title = own && own.path === here.pathname ? own.title : fill(words.documentTitle ?? words.title, match.values);
  useEffect(() => {
    document.title = copy.pageTitle(title);
  }, [title]);

  // A route change, but not the first page: scroll to the top, focus the new title, and try the
  // stamp again if it failed. A move within one tab's pages, such as a Data sub-tab or "Show all
  // sources", focuses the new page's lead instead, as the title has not changed (the 16 brief).
  // A new page brings its scope chip back. Opening or closing the evidence drawer changes only
  // ?evidence=, which is not a route change (routeOf), so it leaves focus where the drawer put it;
  // a change to any other part of the address, such as ?asof=, is one.
  const route = routeOf(here);
  const lastRoute = useRef(route);
  const section = useRef(match.section);
  useEffect(() => {
    const moved = lastRoute.current !== route;
    lastRoute.current = route;
    const within = section.current !== undefined && section.current === match.section;
    section.current = match.section;
    if (!moved || here.moves === 0 || here.quiet) return;
    removedScopes.set(new Set());
    window.scrollTo(0, 0);
    const lead = within ? document.querySelector<HTMLElement>("main [data-lead]") : null;
    (lead ?? document.querySelector<HTMLElement>("main h1"))?.focus();
    retryStamp();
  }, [route, here.moves]);

  const onAsk = (question: string, chip: string | null) =>
    ask({
      question,
      scope: chip,
      asOf: asOf && isDay(asOf) ? asOf : null,
      view: view === "piu" || view === "public" ? view : null,
      lang: params.get("lang"),
      key: address.get().key,
    });

  // The Data readiness page applies an as-of date itself (data_readiness_for takes one), so the
  // alert that says the page shows today's data does not show there.
  const slot = alerts(problem, here.search, match.key === "data", match.key);
  return (
    <Frame
      nav={
        <TopNav
          logo={<img src={logo} width={120} height={24} alt={copy.nav.logo} className="block h-6 w-[120px]" />}
          current={match.section}
          home={match.key === "home"}
          viewer={who}
        />
      }
      band={<BoxBand box={<IntentBox scope={scope} scopeKind={kind} onAsk={onAsk} />} stamp={<FreshnessStamp freshness={freshness} />} />}
      inertPage={narrow && evidenceId !== null}
      aside={
        evidenceId && (
          <EvidenceDrawer
            id={evidenceId}
            run={shown}
            narrow={narrow}
            preview={view === "piu" || view === "public"}
            asOf={asOf && isDay(asOf) ? asOf : null}
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
      <div className="layout layout-grid pt-6 @md/page:pt-8 @lg/page:pt-10">
        {/* The alert slot frames everything on the page, the answer included (DESIGN.md section 5,
            Page header), so it sits above the answer panel. */}
        {slot.length > 0 && (
          <div className="col-span-12 mb-6 flex flex-col gap-2 @md/page:col-span-8">
            {slot.map((alert) => (
              <Alert key={alert.text} state={alert.state} live={alert.state === "error" ? "alert" : undefined}>
                {alert.text}
              </Alert>
            ))}
          </div>
        )}
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
          <RoutePage key={match.frame ?? here.pathname} match={match} search={here.search} />
        </div>
      </div>
    </Frame>
  );
}
