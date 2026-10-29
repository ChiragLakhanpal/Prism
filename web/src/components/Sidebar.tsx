// The sidebar (DESIGN.md section 5, Sidebar and Menu sheet; ticket 92): the navigation named "Main". From 1024 px it
// sits beside the page on the page grey with a hairline edge, sticky under the bar: Home, then the applied view's
// sections, then at its foot Data, the data stamp (ticket 93) and "Collapse the sidebar". It rests as a 64 px rail of
// icons at every width from 1024 px (ticket 110, the user's decision of October 27, 2026), and "Expand the sidebar"
// opens it to 224 px; the choice is kept in local storage, and web/index.html reads it before the first paint, so
// nothing moves when the app mounts. The width changes at once. A rail item shows its label in a
// tooltip on hover and on keyboard focus; the tooltip is not the item's name, which stays in the link. In the rail the
// stamp hides, and the Data item's tooltip and description carry its words.
//
// Below 1024 px the same element is the Menu sheet: a modal dialog named "Menu" that slides in from the left, with
// the page and the bar inert behind it (Frame.tsx holds its state), the stamp under Data and, below 768 px, the view
// switch's lines at its foot. It closes on Escape, on "Close the menu" and on
// the scrim, and focus goes back to the Menu button. When the window narrows past 1024 px, focus on an item moves
// to the Menu button.
//
// Under Home, for World Bank staff in their own view once Home has loaded, sits Start here (ticket 114): how many of
// the examples the person followed, and the next one as the item's link, which goes straight there and ticks it. With
// all done it says so and leads to Home's strip, where Remove stays. As a rail it shows its icon and the short count,
// and its tooltip says the rest. App.tsx decides when it shows (lib/startHere.ts).
import { useEffect, useId, useLayoutEffect, useRef, useState, type FocusEvent } from "react";
import { ListChecks, PanelLeftClose, PanelLeftOpen, X, type LucideIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatCount, formatNumber } from "../lib/format";
import { isShown, useMedia, useMediaChange } from "../lib/media";
import { markDone, progressOf, START_HERE_HREF, type StartHereList } from "../lib/startHere";
import { FreshnessStamp, stampWords, type Freshness } from "./OneBox";
import { Fill } from "./Fill";
import { fillText } from "./LessonParts";
import { useMenuSheet, WIDE } from "./Frame";
import { LanguageChoice } from "./LanguageChoice";
import { FOOT_SECTION, HOME_ITEM, SECTIONS, type Section, type SubItem, type SubItems } from "./sections";
import { Skeleton } from "./Skeleton";
import { ViewPanel, withModeOf, type NavMode, type Viewer } from "./TopNav";

export type Rest = "open" | "rail";

// The key web/index.html's first script reads, before any other script runs.
export const SIDEBAR_KEY = "strata.sidebar";
// With no choice, the sidebar rests as the rail at every width (ticket 110).
const AT_REST: Rest = "rail";
// How long a hover waits before the first tooltip opens, and how soon after one closes the next opens at once.
const TIP_DELAY = 150;
const TIP_RUN = 300;

// The person's choice, as web/index.html's first script wrote it on the root from local storage.
function chosenRest(): Rest | null {
  const value = document.documentElement.dataset.sidebarRest;
  return value === "open" || value === "rail" ? value : null;
}

// The sidebar's resting state and the button that changes it. The root's data-sidebar-rest attribute is written at once
// on a press, so the width is final in the same frame; the stored choice survives a reload.
function useRest(forced?: Rest): [Rest, () => void] {
  const [choice, setChoice] = useState<Rest | null>(() => forced ?? chosenRest());
  useLayoutEffect(() => {
    if (forced) document.documentElement.dataset.sidebarRest = forced;
  }, [forced]);
  const rest: Rest = choice ?? AT_REST;
  const toggle = () => {
    const next: Rest = rest === "open" ? "rail" : "open";
    document.documentElement.dataset.sidebarRest = next;
    try {
      window.localStorage.setItem(SIDEBAR_KEY, next);
    } catch {
      // Without storage the choice lasts until the page reloads.
    }
    setChoice(next);
  };
  return [rest, toggle];
}

const pathOf = (href: string) => href.split("?")[0];

// A tooltip's label, and a second line under it: the stamp's words on the Data item.
type Tip = { text: string; line: string | null; top: number; instant: boolean };

const ITEM = cx(
  "relative flex min-h-9 w-full items-center gap-3 rounded-sm px-3 py-2 text-left text-small transition-paint",
  "rail:justify-center rail:px-0",
);
// The current mark (DESIGN.md section 2): tint, a 3 px primary bar inset on the left, the label in 600 ink-heading.
const CURRENT = "bg-tint font-semibold text-ink-heading before:absolute before:inset-y-0 before:left-0 before:w-[3px] before:rounded-l-sm before:bg-primary";
// A section whose sub-item is the page keeps 600 and its primary icon while the sub-item carries the mark; the rail hides
// the sub-items, so there the section carries the tint and the bar itself, and the page keeps one current mark.
const RAIL_CURRENT = "rail:bg-tint rail:before:absolute rail:before:inset-y-0 rail:before:left-0 rail:before:w-[3px] rail:before:rounded-l-sm rail:before:bg-primary";
// Start here in the item's style (ticket 114), with its lines stacked beside the icon; as a rail, the icon over the
// short count.
const START_ITEM = cx(
  "relative flex min-h-9 w-full items-start gap-3 rounded-sm px-3 py-2 text-left text-small text-ink transition-paint hover:bg-surface-2",
  "rail:flex-col rail:items-center rail:gap-1 rail:px-0",
);

export function Sidebar({
  mode,
  viewer,
  currentKey: current,
  pathname,
  projectsHref,
  subItems,
  freshness,
  rest: forced,
  startHere,
}: {
  // The view the server applied: its sections, the pages it hides, and the address's mode, which every link keeps.
  mode: NavMode;
  // Who is viewing, for the view lines at the Menu sheet's foot below 1024 px.
  viewer: Viewer;
  // The item that holds the page: Home, or the section routes.ts names; none on a page that is not found.
  currentKey?: Section | "home";
  // The page's path, to tell the section's own page ("page") from a page inside it ("true").
  pathname: string;
  // Where Projects goes: Following for World Bank staff (ticket 37), All projects for everyone else.
  projectsHref?: string;
  // Each section's own pages, shown under it while it is current (the tab tickets fill these).
  subItems?: SubItems;
  // The data stamp's state (lib/freshness.ts), shown under Data (ticket 93).
  freshness?: Freshness;
  // For the gallery: the resting state to draw, whatever the width or the stored choice.
  rest?: Rest;
  // Start here's examples and the ones followed (ticket 114), while the item shows; App.tsx decides when.
  startHere?: StartHereList | null;
}) {
  const sheet = useMenuSheet();
  const wide = useMedia(WIDE);
  const [rest, toggle] = useRest(forced);
  const titleId = useId();
  const stampId = useId();
  const box = useRef<HTMLDivElement>(null);
  // An item a resize just hid: Chrome can take focus from it before it reports the media change.
  const hidden = useRef<HTMLElement | null>(null);
  const [tip, setTip] = useState<Tip | null>(null);
  const tipTimer = useRef<number | undefined>(undefined);
  const tipOpen = useRef(false);
  const tipClosedAt = useRef(-Infinity);
  const rail = wide && rest === "rail";

  // Opening the sheet moves focus to the current page's item.
  const wasOpen = useRef(sheet.open);
  useEffect(() => {
    const opened = sheet.open && !wasOpen.current;
    wasOpen.current = sheet.open;
    if (!opened || wide) return;
    const root = box.current;
    (root?.querySelector<HTMLElement>("[data-sub-items] [aria-current]") ??
      root?.querySelector<HTMLElement>("nav [aria-current]") ??
      root?.querySelector<HTMLElement>("nav a"))?.focus();
  }, [sheet.open, wide]);

  // Narrowing the window past 1024 px hides the sidebar, so focus on one of its items moves to the Menu button.
  useMediaChange([WIDE], () => {
    const active = document.activeElement;
    const focused = active instanceof HTMLElement && box.current?.contains(active) ? active : active === document.body ? hidden.current : null;
    hidden.current = null;
    if (!window.matchMedia(WIDE).matches && focused) sheet.button.current?.focus();
  });

  const hideTip = () => {
    window.clearTimeout(tipTimer.current);
    if (tipOpen.current) tipClosedAt.current = performance.now();
    tipOpen.current = false;
    setTip(null);
  };
  // A rail item's tooltip: after 150 ms on the first hover, at once on focus or right after another closed.
  const showTip = (target: HTMLElement, text: string, line: string | null, wait: boolean) => {
    window.clearTimeout(tipTimer.current);
    if (!rail) return;
    const instant = tipOpen.current || performance.now() - tipClosedAt.current < TIP_RUN;
    const place = () => {
      const outer = box.current?.getBoundingClientRect();
      const item = target.getBoundingClientRect();
      if (!outer) return;
      tipOpen.current = true;
      setTip({ text, line, top: item.top - outer.top + item.height / 2, instant });
    };
    if (wait && !instant) tipTimer.current = window.setTimeout(place, TIP_DELAY);
    else place();
  };
  useEffect(() => {
    if (!rail) hideTip();
  }, [rail]);
  const tipProps = (text: string, line: string | null = null) => ({
    onPointerEnter: (event: { currentTarget: HTMLElement }) => showTip(event.currentTarget, text, line, true),
    onPointerLeave: hideTip,
    onFocus: (event: FocusEvent<HTMLElement>) => showTip(event.currentTarget, text, line, false),
    onBlur: hideTip,
  });
  // The stamp's words, which the Data item's tooltip shows in the rail, and its description says there.
  const stampLine = freshness ? stampWords(freshness) : null;

  const sections = mode.tabs === null ? null : SECTIONS.filter((section) => mode.tabs!.includes(section.key));
  const hrefOf = (key: Section, href: string) => (key === "projects" && projectsHref ? projectsHref : href);
  const subsOf = (key: Section): SubItem[] =>
    current === key ? (subItems?.[key] ?? []).filter((item) => !mode.hidden.includes(item.pageKey)) : [];

  // A sub-item's own page ("page"), or a page inside it, such as one item's review page under Waiting for review ("true").
  const subMark = (sub: SubItem): "page" | "true" | undefined =>
    pathOf(sub.href) === pathname ? "page" : sub.inside && pathname.startsWith(sub.inside) ? "true" : undefined;

  const item = (key: Section | "home", href: string, icon: LucideIcon, label: string, line: string | null = null) => {
    const subs = key === "home" ? [] : subsOf(key);
    const subPage = subs.some((sub) => subMark(sub) !== undefined);
    const marked = current === key ? (pathOf(href) === pathname && !subPage ? "page" : "true") : undefined;
    const Icon = icon;
    return (
      <li key={key}>
        <a
          href={withModeOf(href, mode.search)}
          aria-current={marked}
          data-nav-item={key}
          aria-describedby={line && rail ? stampId : undefined}
          className={cx(ITEM, marked && !subPage ? CURRENT : cx("text-ink hover:bg-surface-2", marked && "font-semibold text-ink-heading", marked && subPage && RAIL_CURRENT))}
          {...tipProps(label, line)}
        >
          <Icon aria-hidden="true" className={cx("size-4 shrink-0", marked ? "text-primary" : "text-ink-muted")} />
          <span className="truncate rail:clip-visually">{label}</span>
        </a>
        {subs.length > 0 && (
          <ul data-sub-items={key} className="mt-0.5 mb-1 flex flex-col gap-0.5 rail:hidden">
            {subs.map((sub) => {
              const here = subMark(sub);
              return (
                <li key={sub.pageKey}>
                  <a
                    href={withModeOf(sub.href, mode.search)}
                    aria-current={here}
                    // The count in a small badge, hidden at zero (ticket 102): the number alone on sight, and the link's
                    // name says what it counts, such as "Waiting for review, 3 waiting".
                    aria-label={sub.count?.words}
                    data-sub-item={sub.pageKey}
                    className={cx("relative flex min-h-8 items-center gap-2 rounded-sm py-1 pr-3 pl-10 text-small transition-paint", here ? CURRENT : "text-ink hover:bg-surface-2")}
                  >
                    <span className="min-w-0 flex-1">{sub.label}</span>
                    {sub.count && (
                      <span
                        aria-hidden="true"
                        data-sub-count
                        className="min-w-6 shrink-0 rounded-pill border border-line bg-surface px-2 text-center text-caption font-semibold text-ink tabular-nums"
                      >
                        {sub.count.text}
                      </span>
                    )}
                  </a>
                </li>
              );
            })}
          </ul>
        )}
      </li>
    );
  };

  // Start here under Home (ticket 114): one link, to the next example, or to Home's strip once all are done. Its words
  // are its name open, as a rail (where they are visually hidden and the tooltip shows them) and in the Menu sheet.
  const startHereItem = () => {
    if (!startHere || startHere.links.length === 0) return null;
    const words = copy.nav.startHere;
    const { done, total, upcoming } = progressOf(startHere);
    const [doneText, totalText] = [formatNumber(done, { compact: false }), formatNumber(total, { compact: false })];
    const example = upcoming ? (copy.home.start.links[upcoming.key] ?? upcoming.key) : null;
    const tip = upcoming && example ? words.tip(doneText, totalText, fillText(example, { pid: upcoming.pid ?? "" })) : words.tipAllDone(formatCount(total));
    return (
      <li>
        <a
          href={upcoming ? upcoming.href : START_HERE_HREF}
          data-start-here-item={upcoming ? upcoming.key : "done"}
          // Ticked once the click has finished, since the tick moves this link on to the next example, and the
          // router reads where the click goes after React has drawn (lib/router.ts).
          onClick={() => upcoming && window.setTimeout(() => markDone(upcoming.key))}
          className={START_ITEM}
          {...tipProps(tip)}
        >
          <ListChecks aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-ink-muted rail:mt-0" />
          <span className="flex min-w-0 flex-col rail:clip-visually">
            <span>{words.title}</span>
            <span className="text-caption text-ink-muted">{upcoming ? words.count(doneText, totalText) : words.allDone(formatCount(total))}</span>
            {upcoming && example && (
              <span className="mt-0.5">
                <Fill template={words.next} slots={{ example: <Fill template={example} slots={{ pid: <span className="font-mono">{upcoming.pid}</span> }} /> }} />
              </span>
            )}
          </span>
          <span aria-hidden="true" className="hidden text-caption text-ink-muted rail:block">
            {words.short(doneText, totalText)}
          </span>
        </a>
      </li>
    );
  };

  const foot = sections?.find((section) => section.key === FOOT_SECTION);
  const open = rest === "open";
  const Toggle = open ? PanelLeftClose : PanelLeftOpen;
  const toggleLabel = open ? copy.nav.collapse : copy.nav.expand;
  const dialog = !wide;
  return (
    // The column takes the sidebar's width beside the page and draws its edge the page's whole height; below 1024 px
    // it takes no room, and the sheet inside it lies over the page.
    <div data-sidebar-column className="lg:relative lg:w-(--nav-width) lg:shrink-0 lg:border-r lg:border-line">
      {dialog && sheet.open && (
        <div data-scrim aria-hidden="true" className="fixed inset-0 z-40 bg-scrim" onClick={() => sheet.setOpen(false)} />
      )}
      <div
        ref={box}
        id={sheet.sheetId}
        data-sidebar
        data-open={sheet.open && dialog ? "" : undefined}
        role={dialog ? "dialog" : undefined}
        aria-modal={dialog && sheet.open ? true : undefined}
        aria-labelledby={dialog ? titleId : undefined}
        // A link chosen in the sheet opens its page, which takes focus, so the sheet closes without handing focus back.
        onClick={(event) => {
          if (dialog && sheet.open && (event.target as Element).closest("a[href]")) sheet.setOpen(false, false);
        }}
        onBlur={(event) => {
          const target = event.target as HTMLElement;
          if (event.relatedTarget || isShown(target)) return;
          hidden.current = target;
          requestAnimationFrame(() => (hidden.current = null));
        }}
        onKeyDown={(event) => event.key === "Escape" && hideTip()}
        className={cx(
          "menu-sheet fixed inset-y-0 left-0 z-50 flex w-[min(20rem,calc(100vw-3rem))] flex-col overflow-y-auto overscroll-contain bg-surface shadow-popover",
          "lg:sticky lg:top-(--frame-top) lg:z-30 lg:h-[calc(100dvh-var(--frame-top))] lg:w-full lg:overflow-visible lg:bg-page lg:shadow-none",
        )}
      >
        <div className="flex items-center justify-between border-b border-line py-2 pr-2 pl-4 lg:hidden">
          <p id={titleId} className="text-label text-ink-muted">
            {copy.nav.menu}
          </p>
          <button
            type="button"
            aria-label={copy.nav.menuClose}
            onClick={() => sheet.setOpen(false)}
            className="flex size-11 items-center justify-center rounded-sm text-ink-muted transition-paint hover:bg-surface-2 hover:text-ink"
          >
            <X aria-hidden="true" className="size-5" />
          </button>
        </div>
        <nav
          aria-label={copy.nav.label}
          onScroll={hideTip}
          className="flex flex-none flex-col px-2 py-3 lg:min-h-0 lg:flex-1 lg:overflow-x-hidden lg:overflow-y-auto lg:overscroll-contain"
        >
          {sections === null ? (
            // Until GET /api/me says which sections the view has: static bars at the items' height.
            <div className="flex flex-col gap-0.5">
              {[0, 1, 2, 3, 4, 5].map((index) => (
                <Skeleton key={index} className="h-9 w-full" radius="rounded-sm" />
              ))}
            </div>
          ) : (
            <>
              <ul className="flex flex-col gap-0.5">
                {item("home", HOME_ITEM.href, HOME_ITEM.icon, copy.nav.home)}
                {startHereItem()}
              </ul>
              <ul className="mt-4 flex flex-col gap-0.5">
                {sections
                  .filter((section) => section.key !== FOOT_SECTION)
                  .map((section) => item(section.key, hrefOf(section.key, section.href), section.icon, copy.nav.tabs[section.key]))}
              </ul>
              <div className="mt-auto flex flex-col gap-0.5 pt-6">
                {foot && <ul className="flex flex-col gap-0.5">{item(foot.key, foot.href, foot.icon, copy.nav.tabs[foot.key], stampLine)}</ul>}
                {/* The stamp under Data, on its label's left edge (8 + 12 + 16 + 12 px in); the rail hides it. */}
                {freshness && (
                  <div data-sidebar-stamp className="mb-2 ml-10 rail:hidden">
                    <FreshnessStamp freshness={freshness} href={withModeOf("/data", mode.search)} />
                  </div>
                )}
                {stampLine && (
                  <span id={stampId} hidden>
                    {stampLine}
                  </span>
                )}
                <button
                  type="button"
                  data-sidebar-toggle
                  aria-expanded={open}
                  aria-controls={sheet.sheetId}
                  onClick={() => {
                    toggle();
                    hideTip();
                  }}
                  className={cx(ITEM, "mt-2 hidden text-ink-muted hover:bg-surface-2 hover:text-ink lg:flex")}
                  {...tipProps(toggleLabel)}
                >
                  <Toggle aria-hidden="true" className="size-4 shrink-0" />
                  <span className="truncate rail:clip-visually">{toggleLabel}</span>
                </button>
              </div>
            </>
          )}
        </nav>
        {/* Below 768 px the view lines and the language of answers and drafts sit at the sheet's foot (tickets 40, 42);
            from 768 px the view switch is in the bar (ticket 93). */}
        <div data-menu-panel className="border-t border-line px-4 pt-4 pb-4 md:hidden">
          <ViewPanel viewer={viewer} mode={mode} onDone={() => sheet.setOpen(false, false)} />
          {viewer.status !== "error" && (
            <div className="mt-4 border-t border-line pt-4">
              <LanguageChoice />
            </div>
          )}
        </div>
        {tip && (
          <span
            data-rail-tip
            aria-hidden="true"
            data-instant={tip.instant ? "" : undefined}
            style={{ top: tip.top }}
            className="rail-tip pointer-events-none absolute left-full z-10 ml-2 w-max max-w-(--tooltip-width) -translate-y-1/2 rounded-sm border border-line bg-surface px-3 py-2 text-small text-ink shadow-popover"
          >
            {tip.text}
            {tip.line && <span className="block text-caption text-ink-muted">{tip.line}</span>}
          </span>
        )}
      </div>
    </div>
  );
}
