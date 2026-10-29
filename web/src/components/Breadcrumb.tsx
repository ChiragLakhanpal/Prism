// The breadcrumb (DESIGN.md section 5, Page head; the 10 brief; ticket 95): the trail above a page, such as "Projects >
// Water and Sanitation Development Project (P156634) > Procurement", in caption type. Each step but the last is a
// link; the last is the page you are on, unless the trail lists parents only, as the page head's does, so an object's
// ID shows once in the head. Each link sits in a 24 px line box. Each step's words sit in one span, so a flex link
// reads "Water and Sanitation Development Project (P156634)" as one name, and a step too long for the line wraps inside
// itself and is never cut. The chevron after a step stays on that step's line, so a wrapped trail never starts a line
// with a chevron. Below 768 px the whole trail would take three lines, so only its parent shows, as a link back with a
// chevron, which wraps the same way. The chevrons are hidden from screen readers.
import type { ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { TextLink } from "./TextLink";

export type Crumb = { text: ReactNode; href?: string };

export function Breadcrumb({ trail, back, held = false, holdBack = false }: {
  trail: Crumb[];
  // The step the link back goes to below 768 px, when it is not the last one with a link, such as
  // "Drafts" on a draft's page (the 35 brief, section 3.6).
  back?: Crumb;
  // From a frame of 1200 px (the window less the sidebar), the whole trail shows whatever the page area's width, as
  // on a draft's page, whose document column keeps its place there when the evidence drawer narrows the page area
  // (ticket 94). Without it, opening the drawer would swap the trail for the link back and move the page up.
  held?: boolean;
  // While the page's object loads, the link back holds two lines in a page column under 21rem (a 320 px window),
  // where the parent it will name, such as a project's full name, wraps (ticket 101's design review, round 2).
  holdBack?: boolean;
}) {
  const parent = back ?? [...trail].reverse().find((crumb) => crumb.href);
  return (
    <nav aria-label={copy.breadcrumb.label} data-breadcrumb className="text-caption text-ink-muted">
      <ol className={cx("hidden flex-wrap items-center gap-x-2 @md/page:flex", held && "@xl/frame:flex")}>
        {trail.map((crumb, index) => (
          <li key={index} className="flex min-w-0 items-center gap-2">
            {crumb.href ? (
              <TextLink href={crumb.href} className="inline-flex min-h-6 min-w-0 items-center">
                <span>{crumb.text}</span>
              </TextLink>
            ) : (
              <span aria-current="page" className="inline-flex min-h-6 min-w-0 items-center text-ink">
                <span>{crumb.text}</span>
              </span>
            )}
            {index < trail.length - 1 && <ChevronRight aria-hidden="true" data-crumb-chevron className="size-4 shrink-0 text-line-strong" />}
          </li>
        ))}
      </ol>
      {parent?.href && (
        <p className={cx("@md/page:hidden", held && "@xl/frame:hidden", holdBack && "@max-[21rem]/page:min-h-10")}>
          <TextLink href={parent.href} className="inline-flex min-h-6 items-center gap-1">
            <ChevronLeft aria-hidden="true" className="size-4 shrink-0" />
            <span>{parent.text}</span>
          </TextLink>
        </p>
      )}
    </nav>
  );
}
