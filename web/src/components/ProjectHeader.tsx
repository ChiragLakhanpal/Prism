// Project header (DESIGN.md section 5; the 21 brief, section 2.1; ticket 99): the h1's one line, "{name} · {ProjectId}
// · {country} · {status}", with the name in ink-heading at the h1's 700 and the rest in ink-muted at the same size and
// 400, and the implementing agency line under it in body ink-muted. The status is lowercased from the copy file inside
// the line ("closed"); tables keep the projects API's own word. Each item keeps together, and each dot keeps to the end
// of the word before it, so a wrapped line ends with a dot and never starts with one.
import { Fragment, useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import type { ProjectPage as Page } from "../lib/api";
import { cx } from "../lib/cx";
import { Button } from "./Button";
import { CopyKey } from "./CopyKey";
import { Fill } from "./Fill";
import { ProjectId } from "./ProjectId";

const words = copy.projectPage;

// The agencies keep to one line, with a ghost "Show all agencies" after them on that line when they need more; it shows
// only while the line hides a name, measured again whenever the line's width changes. Opened, the names wrap in full
// and "Show fewer agencies" follows them. Two agency names hold commas, so the names are set apart with semicolons.
export function AgencyLine({ names }: { names: string[] }) {
  const id = useId();
  const line = useRef<HTMLParagraphElement>(null);
  const [open, setOpen] = useState(false);
  const [hides, setHides] = useState(false);
  useLayoutEffect(() => {
    const element = line.current;
    if (!element || open) return;
    const measure = () => setHides(element.scrollWidth > element.clientWidth + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [open]);
  if (names.length === 0) return <p className="mt-2 max-w-prose text-body text-ink-muted">{words.noAgency}</p>;
  return (
    <div className={cx("mt-2 flex", open ? "flex-col items-start" : "items-center gap-x-3")} data-agency-line>
      <p ref={line} id={id} className={cx("min-w-0 text-body text-ink-muted", open ? "max-w-prose" : "truncate")}>
        <Fill template={names.length > 1 ? words.agenciesLine : words.agencyLine} slots={{ agencies: names.join(words.agencyJoin) }} />
      </p>
      {(hides || open) && (
        <span className="shrink-0">
          <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>
            {open ? words.fewerAgencies : words.allAgencies}
          </Button>
        </span>
      )}
    </div>
  );
}

// The h1's one line. The name wraps between its words; each item after it keeps together, with its dot tied to the end
// of what comes before it, so the line breaks only after a dot or inside the name.
export function ProjectHeaderLine({ project }: { project: Page["project"] }) {
  const status = project.status ? (words.statusInline[project.status] ?? project.status) : null;
  const items: [string, ReactNode][] = [
    [
      "pid",
      // The copy key after the P-code (ticket 112) sits in the P-code's item, which never wraps, so the two never part.
      <>
        <ProjectId pid={project.project_id} plain />
        <CopyKey text={project.project_id} what={copy.copyKey.projectId} joined={false} />
      </>,
    ],
    ...(project.country ? [["country", project.country] as [string, ReactNode]] : []),
    ...(status ? [["status", status] as [string, ReactNode]] : []),
  ];
  return (
    <>
      <span className="text-ink-heading" data-project-name>
        {project.display_name ?? project.project_name}
      </span>
      {items.map(([key, content]) => (
        <Fragment key={key}>
          <span className="font-normal text-ink-muted">{words.dot}</span>{" "}
          <span className="font-normal whitespace-nowrap text-ink-muted" data-project-item={key}>
            {content}
          </span>
        </Fragment>
      ))}
    </>
  );
}
