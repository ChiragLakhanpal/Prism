// The design gallery: every component in each of its states, inside the frame every page
// shares, for development and design reviews. It exists only in development and gallery
// builds (see web/src/main.tsx) and nothing links to it.
//
// From 1024 px the list of components sits in columns 1 to 3 and the page in columns 4 to 12.
// Below 1024 px a component page puts the list after its content, and the index leaves it
// out, because its cards already link to every page. A wide page, such as the Plan check,
// takes all 12 columns at every width, as its screen does, and puts the list after it.
import { useState, type ReactNode } from "react";
import logo from "../assets/world-bank-logo.svg";
import { OneBox } from "../components/BoxBand";
import { Frame } from "../components/Frame";
import { subItemsFor, type SubItems } from "../components/sections";
import { Sidebar, type Rest } from "../components/Sidebar";
import { STAFF_MODE, TopNav, type NavMode, type Section, type Viewer } from "../components/TopNav";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { galleryCopy } from "./copy";
import { PAGES, type GalleryPage } from "./pages";
import { useZonesSheet } from "./zones";

// The World Bank logo, the official file the app shows (web/src/assets/world-bank-logo.md).
export function LogoSlot() {
  return <img data-logo src={logo} width={120} height={24} alt={copy.nav.logo} className="block h-6 w-[120px]" />;
}

// The bar's box. With ?scope= it holds a package's scope chip, such as the longest reference in the fixture (ticket 93).
function Box({ scope }: { scope?: string }) {
  const [value, setValue] = useState("");
  const [chip, setChip] = useState(scope ?? null);
  return <OneBox value={value} onChange={setValue} scope={chip} scopeKind="package" onRemoveScope={() => setChip(null)} />;
}

// The bar's sample views (ticket 40): World Bank staff, an implementing agency officer in their own view, each preview.
// The sections and hidden pages here are a sample; in the app they come from the roles file through GET /api/me.
const PUBLIC_TABS: Section[] = ["projects", "lessons", "data"];
const REVIEWER_PAGES = ["lessonsQueue", "lessonReview", "lessonsReports", "passageReport", "lessonsJudging", "judgingQuery"];
const PUBLIC_HIDDEN = ["packages", "drafts", "following", ...REVIEWER_PAGES];
const OFFICER_HIDDEN = ["following", ...REVIEWER_PAGES];

export function sampleMode(pill: string | null): NavMode {
  const agency = copy.view.agencyInSentence(galleryCopy.sampleAgency, galleryCopy.sampleAgencyShort);
  const officer = pill === "officer" || pill === "officer-public";
  const preview = pill === "piu" ? "piu" : pill === "public" || pill === "officer-public" ? "public" : null;
  return {
    ...STAFF_MODE,
    own: officer ? "piu" : "staff",
    preview,
    offered: officer ? ["piu", "public"] : ["staff", "piu", "public"],
    agency,
    tabs: preview === "public" ? PUBLIC_TABS : STAFF_MODE.tabs,
    hidden: preview === "public" ? PUBLIC_HIDDEN : preview === "piu" || officer ? OFFICER_HIDDEN : [],
    pathname: "/gallery/navigation",
  };
}

// A section's own pages under its item while it is current (ticket 92's slot): Projects' as World Bank staff see them
// (ticket 99), and a sample of what the Lessons ticket adds.
const SAMPLE_SUB_ITEMS: SubItems = {
  ...subItemsFor(true),
  lessons: [{ page: "lessonsQueue", label: copy.pages.lessonReview.title, href: "/lessons/review" }],
};

// Each section's own page, which the gallery's sample page stands for, so the current item reads as that page.
const SECTION_PAGE: Record<Section, string> = { packages: "/packages", projects: "/projects", lessons: "/lessons", drafts: "/drafts", data: "/data" };

export function GalleryFrame({
  current,
  viewer = { status: "signed-in", email: galleryCopy.sampleEmail },
  menuOpen,
  viewOpen,
  mode = sampleMode(null),
  rest,
  subs = false,
  scope,
  aside,
  inertPage,
  children,
}: {
  current?: Section;
  viewer?: Viewer;
  menuOpen?: boolean;
  viewOpen?: boolean;
  mode?: NavMode;
  // The sidebar's resting state, open or rail, whatever the width (?sidebar=open or ?sidebar=rail).
  rest?: Rest;
  // Draw the sample sub-items, with All projects as the page (?sub=1).
  subs?: boolean;
  // A package's scope chip in the box (?scope=).
  scope?: string;
  // The evidence drawer a page's samples open beside the page (ticket 95), and whether it is a modal sheet now.
  aside?: ReactNode;
  inertPage?: boolean;
  children: ReactNode;
}) {
  const date = formatDate(galleryCopy.sampleDate, { style: "short", today: galleryCopy.sampleDate });
  // The current section's own page, which the gallery's sample page stands for.
  const pathname = current ? SECTION_PAGE[current] : mode.pathname;
  return (
    <Frame
      menuOpen={menuOpen}
      aside={aside}
      inertPage={inertPage}
      nav={<TopNav logo={<LogoSlot />} viewer={viewer} viewOpen={viewOpen} mode={mode} />}
      box={<Box scope={scope} />}
      sidebar={
        <Sidebar
          mode={mode}
          viewer={viewer}
          current={current}
          pathname={pathname}
          subItems={subs ? SAMPLE_SUB_ITEMS : undefined}
          freshness={{ status: "ready", date }}
          rest={rest}
        />
      }
    >
      {children}
    </Frame>
  );
}

function ComponentList({ active, wide }: { active?: string; wide?: boolean }) {
  return (
    <nav
      aria-label={galleryCopy.listLabel}
      className={cx("col-span-12", !wide && "lg:order-first lg:col-span-3", active ? "order-last" : "hidden lg:block")}
    >
      <h2 className="text-label text-ink-muted">{galleryCopy.listLabel}</h2>
      <ul className="mt-2 flex flex-wrap gap-x-4 lg:flex-col lg:gap-x-0">
        {PAGES.map((page) => (
          <li key={page.slug}>
            <a
              href={`/gallery/${page.slug}`}
              aria-current={page.slug === active ? "page" : undefined}
              className={cx(
                "flex min-h-8 items-center text-small underline-offset-3 hover:text-link-hover hover:underline",
                page.slug === active ? "font-bold text-ink-heading" : "text-primary",
              )}
            >
              {galleryCopy.pages[page.slug].title}
            </a>
          </li>
        ))}
      </ul>
    </nav>
  );
}

function Page({ page }: { page: GalleryPage }) {
  const words = galleryCopy.pages[page.slug];
  return (
    <div className={cx("col-span-12 min-w-0", !page.wide && "lg:col-span-9")}>
      <p className="text-small">
        <a href="/gallery" className="inline-flex min-h-6 items-center text-primary underline underline-offset-3 hover:text-link-hover">
          {galleryCopy.allComponents}
        </a>
      </p>
      <h1 className="mt-2 text-h1 text-ink-heading">{words.title}</h1>
      <p className="mt-2 max-w-prose text-body text-ink-muted">{words.purpose}</p>
      <p className="mt-2 max-w-prose text-caption text-ink-muted">{galleryCopy.sampleNote}</p>
      <div className="mt-8 flex flex-col gap-10">
        {page.sections.map((section) => (
          <section key={section.id} aria-labelledby={`state-${section.id}`} data-state-section={section.id}>
            <h2 id={`state-${section.id}`} className="text-h3 text-ink-heading">
              {section.title}
            </h2>
            <div className="mt-4">{section.body}</div>
          </section>
        ))}
      </div>
    </div>
  );
}

function Index() {
  return (
    <div className="col-span-12 lg:col-span-9">
      <h1 className="text-h1 text-ink-heading">{galleryCopy.title}</h1>
      <p className="mt-2 max-w-prose text-body text-ink-muted">{galleryCopy.purpose}</p>
      <ul className="mt-8 grid gap-4 md:grid-cols-2">
        {PAGES.map((page) => (
          <li key={page.slug} className="rounded-md border border-line bg-surface p-4">
            <a href={`/gallery/${page.slug}`} className="text-h2 text-primary underline underline-offset-3 hover:text-link-hover">
              {galleryCopy.pages[page.slug].title}
            </a>
            <p className="mt-2 text-small text-ink">{galleryCopy.pages[page.slug].purpose}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

// The frame's own states come from the address, so the capture command can open each one:
// ?menu=open opens the Menu sheet, ?view=open the view popover, ?viewer=loading,
// ?viewer=signed-out or ?viewer=error sets what the view lines say, ?pill=officer, ?pill=piu, ?pill=public or
// ?pill=officer-public shows that view's pill and sections (ticket 40), and ?sidebar=open or ?sidebar=rail draws the
// sidebar open or as the rail at any width from 1024 px, and ?sub=1 adds the sample sub-items (ticket 92). ?scope= puts
// a package's scope chip in the box (ticket 93).
function frameState(search: string): { menuOpen: boolean; viewOpen: boolean; viewer: Viewer; mode: NavMode; rest?: Rest; subs: boolean; scope?: string } {
  const params = new URLSearchParams(search);
  const viewer = params.get("viewer");
  const rest = params.get("sidebar");
  return {
    rest: rest === "open" || rest === "rail" ? rest : undefined,
    subs: params.get("sub") === "1",
    scope: params.get("scope") ?? undefined,
    mode: sampleMode(params.get("pill")),
    menuOpen: params.get("menu") === "open",
    viewOpen: params.get("view") === "open",
    viewer:
      viewer === "loading" || viewer === "signed-out" || viewer === "error"
        ? { status: viewer }
        : { status: "signed-in", email: galleryCopy.sampleEmail },
  };
}

export function Gallery({ path, search = "" }: { path: string; search?: string }) {
  const slug = path.replace(/^\/gallery\/?/, "").replace(/\/$/, "");
  const page = PAGES.find((candidate) => candidate.slug === slug);
  // ?sample= draws one of the page's whole-page samples in place of the gallery's title and list (ticket 95).
  const sample = page?.samples?.[new URLSearchParams(search).get("sample") ?? ""];
  const sheet = useZonesSheet();
  return (
    <div data-gallery-root>
      <GalleryFrame current={page?.current} {...frameState(search)} aside={page?.aside} inertPage={sheet}>
        {sample ?? (
          <div className="layout layout-grid gap-y-8 pt-10">
            {page ? <Page page={page} /> : <Index />}
            <ComponentList active={page?.slug} wide={page?.wide} />
          </div>
        )}
      </GalleryFrame>
    </div>
  );
}
