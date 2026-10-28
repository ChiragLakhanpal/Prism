// Cards (DESIGN.md section 5, from The Loop): surface, a 1 px line and radius 8, with no
// shadow. Titles are 80 characters or fewer and blurbs 140; a group holds eight cards at most.
// A card that states a finding ends with its source line (DESIGN.md principle 1).
import { createElement, type ReactNode } from "react";
import { CircleDashed } from "lucide-react";
import { cx } from "../lib/cx";
import { Source } from "./Source";
import { TextLink } from "./TextLink";

type Level = 2 | 3 | 4 | 5;

export function Card({
  title,
  level = 3,
  children,
  source,
  className,
}: {
  title?: ReactNode;
  level?: Level;
  children?: ReactNode;
  // Where the card's finding came from, after "Source:".
  source?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-md border border-line bg-surface p-4 @md/page:p-6", className)}>
      {title && createElement(`h${level}`, { className: "text-h2 text-ink-heading" }, title)}
      {children && <div className={cx(Boolean(title) && "mt-2", "text-body text-ink")}>{children}</div>}
      {source && <Source className="mt-4">{source}</Source>}
    </section>
  );
}

// An empty state: a card with a dashed circle, one first-person sentence as its heading, one
// or two sentences that say what will fill it, and at most one link to the next step.
export function EmptyState({
  title,
  body,
  more,
  link,
  level = 2,
  bare = false,
  className,
}: {
  title: ReactNode;
  body: ReactNode;
  // A second paragraph, for the one card that must also say where its content shows up (the Lessons library's,
  // ticket 114).
  more?: ReactNode;
  link?: { href: string; text: ReactNode };
  level?: Level;
  // Inside a Task zone panel, which is its card already, as All projects' no match (ticket 99): no border, fill or
  // padding of its own, a 20 px circle and the title in h3.
  bare?: boolean;
  className?: string;
}) {
  return (
    <section data-empty-state className={cx("flex gap-3", !bare && "rounded-md border border-line bg-surface p-4 @md/page:p-6", className)}>
      <CircleDashed aria-hidden="true" className={cx("shrink-0 text-line-strong", bare ? "mt-0.5 size-5" : "size-6")} />
      <div className="min-w-0">
        {createElement(`h${level}`, { className: cx(bare ? "text-h3" : "text-h2", "text-balance text-ink-heading") }, title)}
        <p className="mt-2 max-w-prose text-body text-pretty text-ink">{body}</p>
        {more && <p className="mt-2 max-w-prose text-body text-pretty text-ink">{more}</p>}
        {link && (
          <p className="mt-4">
            <TextLink href={link.href}>{link.text}</TextLink>
          </p>
        )}
      </div>
    </section>
  );
}
