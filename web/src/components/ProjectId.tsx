// ProjectId (the 21 brief, section 9; DESIGN.md section 5): every P-code in Prism is a link to its
// project page, in Roboto Mono 500 at the size of the text around it, primary and underlined. A link to
// the page you are on carries aria-current="page", as the h1's P-code does on a project's Summary.
//
// linkProjectIds is the one helper for text Prism does not write itself, such as a passage, an answer
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

export function ProjectId({ pid, className, current: shown, plain = false }: {
  pid: string;
  className?: string;
  // The gallery shows the current state on a page that is not the project's.
  current?: boolean;
  // In 400 rather than 500, as in a project's h1, whose ID, country and status take 400 beside the name (ticket 99).
  plain?: boolean;
}) {
  const here = useStore(address);
  const current = shown ?? here.pathname === projectHref(pid);
  return (
    // In small type the link's own box can fall under 24 px, so an ::after 2 px over it above and below pads
    // its hit area to WCAG 2.5.8's 24 px without changing the line, as the citation marker's does.
    <TextLink
      href={projectHref(pid)}
      aria-current={current ? "page" : undefined}
      data-project-id={pid}
      className={cx("relative font-mono whitespace-nowrap after:absolute after:inset-x-0 after:-inset-y-0.5 after:content-['']", plain ? "font-normal" : "font-medium", className)}
    >
      {pid}
    </TextLink>
  );
}

// A P-code as plain Roboto Mono 500, where it is not a link: inside a link already, such as a crumb that
// links to its project, or on a page that has no project to link to (DESIGN.md section 5, ProjectId).
export function ProjectIdText({ pid }: { pid: string }) {
  return <span className="font-mono font-medium">{pid}</span>;
}

// An ID Prism writes, such as a scope: a P-code as a ProjectId link, anything else, such as a STEP
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
