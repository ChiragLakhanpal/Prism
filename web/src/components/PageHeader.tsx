// The page header (DESIGN.md section 5, Strata components): every page's h1 and, under it, one or
// two short sentences that say what the page is for, so someone arriving from a link is never
// stranded.
// The h1 takes focus when a route change moves to it (tabindex -1); it is not a control, so it
// shows no ring. An ID in the title from the address wraps after its hyphens, and anywhere as
// a last resort, so nothing scrolls sideways at 320 px.
import { createElement, Fragment, type ReactNode } from "react";

export function PageHeader({
  title,
  purpose,
  level = 1,
}: {
  title: ReactNode;
  purpose: ReactNode;
  // Every page's title is its h1. The design gallery shows samples one level down, under its own h1.
  level?: 1 | 2;
}) {
  return (
    <div>
      {createElement(
        `h${level}`,
        { tabIndex: -1, className: "text-h1 wrap-anywhere text-ink-heading focus:outline-none" },
        title,
      )}
      <p className="mt-2 max-w-prose text-body text-pretty text-ink-muted">{purpose}</p>
    </div>
  );
}

// A copy template whose {pid}, {stepRef} and {id} slots hold IDs from the address, in Roboto Mono.
export function WithIds({ template, values }: { template: string; values: Record<string, string> }) {
  const parts = template.split(/\{(\w+)\}/);
  return (
    <>
      {parts.map((part, index) =>
        index % 2 === 1 && values[part] !== undefined ? (
          <span key={index} className="font-mono font-medium">
            {values[part]}
          </span>
        ) : (
          <Fragment key={index}>{part}</Fragment>
        ),
      )}
    </>
  );
}
