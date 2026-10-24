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
import { TopNav, type Viewer } from "./components/TopNav";
import { copy } from "./copy";
import { answer, ask, removedScopes } from "./lib/answer";
import { getJson, type Me } from "./lib/api";
import { drawerClosed, evidenceIn, origin, visited } from "./lib/evidence";
import { readStamp, retryStamp, stamp, type Problem } from "./lib/freshness";
import { formatDate } from "./lib/format";
import { address, navigate, startRouter } from "./lib/router";
import { createStore, useStore } from "./lib/store";
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
function scopeOf(match: Match): { scope: string | null; kind: "project" | "package" } {
  if (match.key === "package") return { scope: match.values.id ?? null, kind: "package" };
  if (match.key === "activity") return { scope: match.values.stepRef ?? null, kind: "package" };
  if (match.key === "project" || match.key === "checkPlan") return { scope: match.values.pid ?? null, kind: "project" };
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
  (marker ?? document.querySelector<HTMLElement>("main h1"))?.focus();
}

const VIEW_ALERTS: Record<string, string> = { piu: copy.alerts.viewPiu, public: copy.alerts.viewPublic };

// The alert slot: errors first, then what the address asks for that I can't show yet. Ticket 40
// replaces the view and as-of alerts with its preview and as-of banners in this same slot.
function alerts(problem: Problem, search: string): { state: "error" | "info"; text: string }[] {
  const params = new URLSearchParams(search);
  const found: { state: "error" | "info"; text: string }[] = [];
  if (problem === "no_access") found.push({ state: "error", text: copy.alerts.noAccess });
  if (problem === "no_identity") found.push({ state: "error", text: copy.alerts.noIdentity });
  const view = params.get("view");
  if (view !== null && view !== "staff") found.push({ state: "info", text: VIEW_ALERTS[view] ?? copy.alerts.viewUnknown });
  const asOf = params.get("asof");
  if (asOf !== null) {
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
  const { scope, kind } = scopeOf(match);
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

  const title = fill(copy.pages[match.key].title, match.values);
  useEffect(() => {
    document.title = copy.pageTitle(title);
  }, [title]);

  // A route change, but not the first page: scroll to the top, focus the new title, and try the
  // stamp again if it failed. A new page brings its scope chip back.
  const lastPath = useRef(here.pathname);
  useEffect(() => {
    if (lastPath.current === here.pathname) return;
    lastPath.current = here.pathname;
    removedScopes.set(new Set());
    window.scrollTo(0, 0);
    document.querySelector<HTMLElement>("main h1")?.focus();
    retryStamp();
  }, [here.pathname]);

  const onAsk = (question: string, chip: string | null) =>
    ask({
      question,
      scope: chip,
      asOf: asOf && isDay(asOf) ? asOf : null,
      view: view === "piu" || view === "public" ? view : null,
      lang: params.get("lang"),
      key: address.get().key,
    });

  const slot = alerts(problem, here.search);
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
            table that needs the width, such as the plan check, spans all 12. */}
        <div className="col-span-12">
          <RoutePage key={here.pathname} match={match} />
        </div>
      </div>
    </Frame>
  );
}
