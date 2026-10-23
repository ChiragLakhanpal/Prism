// Cards (DESIGN.md section 5, from The Loop): surface, a 1 px line and radius 8, with no
// shadow. Titles are 80 characters or fewer and blurbs 140; a group holds eight cards at most.
import { createElement, type ReactNode } from "react";
import { CircleDashed } from "lucide-react";
import { cx } from "../lib/cx";
import { TextLink } from "./TextLink";

type Level = 2 | 3 | 4;

export function Card({
  title,
  level = 3,
  children,
  className,
}: {
  title?: ReactNode;
  level?: Level;
  children?: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-md border border-line bg-surface p-4 md:p-6", className)}>
      {title && createElement(`h${level}`, { className: "text-title text-ink-heading" }, title)}
      {children && <div className={cx(Boolean(title) && "mt-2", "text-body text-ink")}>{children}</div>}
    </section>
  );
}

// An empty state: a card with a dashed circle, one first-person sentence as its heading, one
// or two sentences that say what will fill it, and at most one link to the next step.
export function EmptyState({
  title,
  body,
  link,
  level = 2,
  className,
}: {
  title: ReactNode;
  body: ReactNode;
  link?: { href: string; text: ReactNode };
  level?: Level;
  className?: string;
}) {
  return (
    <section data-empty-state className={cx("flex gap-3 rounded-md border border-line bg-surface p-4 md:p-6", className)}>
      <CircleDashed aria-hidden="true" className="size-6 shrink-0 text-line-strong" />
      <div className="min-w-0">
        {createElement(`h${level}`, { className: "text-title text-ink-heading" }, title)}
        <p className="mt-2 max-w-prose text-body text-ink">{body}</p>
        {link && (
          <p className="mt-4">
            <TextLink href={link.href}>{link.text}</TextLink>
          </p>
        )}
      </div>
    </section>
  );
}
