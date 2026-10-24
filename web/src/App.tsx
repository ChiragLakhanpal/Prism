// The app: the frame every page shares (web/src/components/Frame.tsx), around the page the address
// names (web/src/routes.ts). The navy bar carries the World Bank logo, the wordmark, the five tabs
// and the view switch; the band, the box and the data-freshness stamp; the page, its alert slot,
// title, purpose and empty state; and the footer.
//
// The app reads who is viewing (/api/me) and the stamp (/api/freshness) once per page load and
// keeps both across route changes. A route change updates the browser tab's title, scrolls to the
// top and moves focus to the new h1, and a stamp that failed tries again.
import { useEffect, useRef, useState } from "react";
import logo from "./assets/world-bank-logo.svg";
import { Alert } from "./components/Alert";
import { BoxBand, FreshnessStamp, OneBox } from "./components/BoxBand";
import { Frame } from "./components/Frame";
import { TopNav, type Viewer } from "./components/TopNav";
import { copy } from "./copy";
import { getJson, type Me } from "./lib/api";
import { readStamp, retryStamp, stamp, type Problem } from "./lib/freshness";
import { formatDate } from "./lib/format";
import { address, navigate, startRouter } from "./lib/router";
import { createStore, useStore } from "./lib/store";
import { RoutePage } from "./RoutePage";
import { fill, matchRoute } from "./routes";

const viewer = createStore<Viewer>({ status: "loading" });

async function readViewer() {
  try {
    const me = await getJson<Me>("/api/me");
    viewer.set(me.signed_in && me.email ? { status: "signed-in", email: me.email } : me.signed_in ? { status: "error" } : { status: "signed-out" });
  } catch {
    viewer.set({ status: "error" });
  }
}

// Before ticket 14 the box takes text but cannot act. Its status line says so before Enter is
// pressed; Enter submits nothing and says it again, so a screen reader hears it a second time.
// The first Escape closes the line and the second clears the box.
function Box() {
  const [value, setValue] = useState("");
  const [closed, setClosed] = useState(false);
  const [said, setSaid] = useState(0);
  return (
    <OneBox
      value={value}
      onChange={(next) => {
        setValue(next);
        setClosed(false);
      }}
      below={closed ? undefined : <span key={said}>{copy.box.notReady}</span>}
      onEnter={() => setSaid(said + 1)}
      onEscape={() => {
        if (closed || !value) return false;
        setClosed(true);
        return true;
      }}
    />
  );
}

const VIEW_ALERTS: Record<string, string> = { piu: copy.alerts.viewPiu, public: copy.alerts.viewPublic };
const DAY = /^(\d{4})-(\d{2})-(\d{2})$/;

function realDay(text: string): boolean {
  const day = DAY.exec(text);
  if (!day) return false;
  const date = new Date(`${text}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().startsWith(text);
}

// The alert slot: errors first, then what the address asks for that I can't show yet. Ticket 40
// replaces the view and as-of alerts with its preview and as-of banners in this same slot.
function alerts(problem: Problem, search: string, appliesAsOf: boolean): { state: "error" | "info"; text: string }[] {
  const params = new URLSearchParams(search);
  const found: { state: "error" | "info"; text: string }[] = [];
  if (problem === "no_access") found.push({ state: "error", text: copy.alerts.noAccess });
  if (problem === "no_identity") found.push({ state: "error", text: copy.alerts.noIdentity });
  const view = params.get("view");
  if (view !== null && view !== "staff") found.push({ state: "info", text: VIEW_ALERTS[view] ?? copy.alerts.viewUnknown });
  const asOf = params.get("asof");
  if (asOf !== null && !appliesAsOf) {
    found.push({ state: "info", text: realDay(asOf) ? copy.alerts.asOf(formatDate(asOf)) : copy.alerts.asOfUnreadable });
  }
  return found;
}

export function App() {
  const here = useStore(address);
  const who = useStore(viewer);
  const { freshness, problem } = useStore(stamp);
  const match = matchRoute(here.pathname);

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
  const words: { title: string; documentTitle?: string } = copy.pages[match.key];
  const title = fill(words.documentTitle ?? words.title, match.values);
  useEffect(() => {
    document.title = copy.pageTitle(title);
  }, [title]);

  // A route change, but not the first page: scroll to the top, focus the new title, and try the
  // stamp again if it failed. A move within one tab's pages, such as a Data sub-tab or "Show all
  // sources", focuses the new page's lead instead, as the title has not changed (the 16 brief).
  const section = useRef(match.section);
  useEffect(() => {
    const within = section.current !== undefined && section.current === match.section;
    section.current = match.section;
    if (here.moves === 0) return;
    window.scrollTo(0, 0);
    const lead = within ? document.querySelector<HTMLElement>("main [data-lead]") : null;
    (lead ?? document.querySelector<HTMLElement>("main h1"))?.focus();
    retryStamp();
  }, [here.moves]);

  // The Data readiness page applies an as-of date itself (data_readiness_for takes one), so the
  // alert that says the page shows today's data does not show there.
  const slot = alerts(problem, here.search, match.key === "data");
  // The Data tab's tables take the whole content width; every other page keeps columns 1 to 8.
  const wide = match.section === "data";
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
      band={<BoxBand box={<Box />} stamp={<FreshnessStamp freshness={freshness} />} />}
    >
      <div className="layout layout-grid pt-6 md:pt-8 lg:pt-10">
        <div className={wide ? "col-span-12" : "col-span-12 md:col-span-8"}>
          {slot.length > 0 && (
            <div className={wide ? "mb-6 flex flex-col gap-2 md:w-2/3" : "mb-6 flex flex-col gap-2"}>
              {slot.map((alert) => (
                <Alert key={alert.text} state={alert.state} live={alert.state === "error" ? "alert" : undefined}>
                  {alert.text}
                </Alert>
              ))}
            </div>
          )}
          <RoutePage match={match} search={here.search} />
        </div>
      </div>
    </Frame>
  );
}
