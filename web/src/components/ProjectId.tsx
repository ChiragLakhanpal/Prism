// ProjectId (the 21 brief, section 9; DESIGN.md section 5): every P-code in Strata is a link to its
// project page, in Roboto Mono 500 at the size of the text around it, primary and underlined. A link to
// the page you are on carries aria-current="page", as the h1's P-code does on a project's Summary.
//
// linkProjectIds is the one helper for text Strata does not write itself, such as a passage, an answer
// sentence or a STEP description: it wraps every P and six digits in a ProjectId and changes no words.
// The Playwright sweep in web/tests/hub.spec.ts finds any P-code on any route that is not such a link,
// outside the places PROJECT_ID_EXEMPT names.
import { Fragment, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { TextLink } from "./TextLink";

// A P-code where it stands alone in text: P and six digits.
export const PROJECT_ID = /\bP\d{6}\b/g;

// The places the sweep leaves out, in one list (the 21 brief, section 9): text a person types (form
// fields), the one box's scope chip, whose only action is to remove it, and visually hidden text that
// repeats a link already on screen. The page's <title> is outside the body, so the sweep never reads it.
// Briefs 37 and 41 add theirs here.
export const PROJECT_ID_EXEMPT = ["input", "textarea", "[data-scope-chip]", ".sr-only", "[data-project-id-exempt]"];

export function projectHref(pid: string): string {
  return `/projects/${pid}`;
}

export function ProjectId({ pid, className }: { pid: string; className?: string }) {
  const here = useStore(address);
  const current = here.pathname === projectHref(pid);
  return (
    <TextLink href={projectHref(pid)} aria-current={current ? "page" : undefined} data-project-id={pid} className={cx("font-mono font-medium whitespace-nowrap", className)}>
      {pid}
    </TextLink>
  );
}

// Text with each P-code in it as a ProjectId.
export function linkProjectIds(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  let at = 0;
  for (const match of text.matchAll(PROJECT_ID)) {
    const start = match.index ?? 0;
    if (start > at) parts.push(<Fragment key={`t${at}`}>{text.slice(at, start)}</Fragment>);
    parts.push(<ProjectId key={`p${start}`} pid={match[0]} />);
    at = start + match[0].length;
  }
  if (at < text.length) parts.push(<Fragment key={`t${at}`}>{text.slice(at)}</Fragment>);
  return parts;
}
