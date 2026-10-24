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
import { BoxBand, FreshnessStamp, OneBox } from "../components/BoxBand";
import { Frame } from "../components/Frame";
import { TopNav, type Section, type Viewer } from "../components/TopNav";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatDate } from "../lib/format";
import { galleryCopy } from "./copy";
import { PAGES, type GalleryPage } from "./pages";

// The World Bank logo, the official file the app shows (web/src/assets/world-bank-logo.md).
export function LogoSlot() {
  return <img data-logo src={logo} width={120} height={24} alt={copy.nav.logo} className="block h-6 w-[120px]" />;
}

function Box() {
  const [value, setValue] = useState("");
  return <OneBox value={value} onChange={setValue} below={copy.box.notReady} />;
}

export function GalleryFrame({
  current,
  viewer = { status: "signed-in", email: galleryCopy.sampleEmail },
  menuOpen,
  viewOpen,
  children,
}: {
  current?: Section;
  viewer?: Viewer;
  menuOpen?: boolean;
  viewOpen?: boolean;
  children: ReactNode;
}) {
  const date = formatDate(galleryCopy.sampleDate, { style: "short", today: galleryCopy.sampleDate });
  return (
    <Frame
      nav={<TopNav logo={<LogoSlot />} current={current} viewer={viewer} menuOpen={menuOpen} viewOpen={viewOpen} />}
      band={<BoxBand box={<Box />} stamp={<FreshnessStamp freshness={{ status: "ready", date }} />} />}
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
      <h2 className="text-label text-ink-muted uppercase">{galleryCopy.listLabel}</h2>
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
            <a href={`/gallery/${page.slug}`} className="text-title text-primary underline underline-offset-3 hover:text-link-hover">
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
// ?menu=open opens the Menu panel, ?view=open the view popover, and ?viewer=loading,
// ?viewer=signed-out or ?viewer=error sets what the view lines say.
function frameState(search: string): { menuOpen: boolean; viewOpen: boolean; viewer: Viewer } {
  const params = new URLSearchParams(search);
  const viewer = params.get("viewer");
  return {
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
  return (
    <div data-gallery-root>
      <GalleryFrame current={page?.current} {...frameState(search)}>
        <div className="layout layout-grid gap-y-8 pt-10">
          {page ? <Page page={page} /> : <Index />}
          <ComponentList active={page?.slug} wide={page?.wide} />
        </div>
      </GalleryFrame>
    </div>
  );
}
