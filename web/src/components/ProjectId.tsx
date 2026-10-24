// ProjectId (the 21 brief, section 9; DESIGN.md section 5): every P-code in Strata is a link to its
// project page, in Roboto Mono 500 at the size of the text around it, primary and underlined. A link to
// the page you are on carries aria-current="page", as the h1's P-code does on a project's Summary.
//
// linkProjectIds is the one helper for text Strata does not write itself, such as a passage, an answer
// sentence or a STEP description: it wraps every P and six digits in a ProjectId and changes no words.
// The Playwright sweep in web/tests/sweep.spec.ts finds any P-code on any route that is not such a link,
// outside the places PROJECT_ID_EXEMPT (web/src/lib/projectId.ts) names.
import { Fragment, type ReactNode } from "react";
import { cx } from "../lib/cx";
import { PROJECT_ID } from "../lib/projectId";
import { address } from "../lib/router";
import { useStore } from "../lib/store";
import { TextLink } from "./TextLink";

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

// An ID Strata writes, such as a scope: a P-code as a ProjectId link, anything else, such as a STEP
// reference, in Roboto Mono as it stands.
export function IdText({ id }: { id: string }) {
  return /^P\d{6}$/.test(id) ? <ProjectId pid={id} /> : <span className="font-mono">{id}</span>;
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
