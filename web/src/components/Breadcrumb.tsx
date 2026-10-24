// The trail above a project's pages (the 10 brief): "Projects > Water and Sanitation Development
// Project (P156634) > Procurement > Plan of Oct 9, 2026", in caption type. Each step but the last is a
// link; the last is the page you are on. Each step's words sit in one span, so a flex link reads
// "Water and Sanitation Development Project (P156634)" as one name. Below 768 px the whole trail would take three lines, so
// only its parent shows, as a link back with a chevron. The chevrons are hidden from screen readers.
import type { ReactNode } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { copy } from "../copy";
import { TextLink } from "./TextLink";

export type Crumb = { text: ReactNode; href?: string };

export function Breadcrumb({ trail }: { trail: Crumb[] }) {
  const parent = [...trail].reverse().find((crumb) => crumb.href);
  return (
    <nav aria-label={copy.breadcrumb.label} data-breadcrumb className="text-caption text-ink-muted">
      <ol className="hidden flex-wrap items-center gap-x-2 @md/page:flex">
        {trail.map((crumb, index) => (
          <li key={index} className="flex min-w-0 items-center gap-2">
            {index > 0 && <ChevronRight aria-hidden="true" className="size-4 shrink-0 text-line-strong" />}
            {crumb.href ? (
              <TextLink href={crumb.href} className="inline-flex min-h-6 items-center">
                <span>{crumb.text}</span>
              </TextLink>
            ) : (
              <span aria-current="page" className="inline-flex min-h-6 items-center text-ink">
                <span>{crumb.text}</span>
              </span>
            )}
          </li>
        ))}
      </ol>
      {parent?.href && (
        <p className="@md/page:hidden">
          <TextLink href={parent.href} className="inline-flex min-h-6 items-center gap-1">
            <ChevronLeft aria-hidden="true" className="size-4 shrink-0" />
            <span>{parent.text}</span>
          </TextLink>
        </p>
      )}
    </nav>
  );
}
