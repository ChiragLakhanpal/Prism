// Project header (DESIGN.md section 5; the 21 brief, section 2.1): the h1's one line, "{name} · {ProjectId}
// · {country} · {status}", with the name in ink-heading and the rest in ink-muted at the same size, and the
// implementing agency line under it in body ink-muted. The status is lowercased from the copy file inside
// the line ("closed"); tables keep the projects API's own word. Each " · item" keeps together, so a dot
// never ends a line and an item never splits. The header is not sticky until ticket 37 gives it an action.
import { useId, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { copy } from "../copy";
import type { ProjectPage as Page } from "../lib/api";
import { Button } from "./Button";
import { Fill } from "./Fill";
import { ProjectId } from "./ProjectId";

const words = copy.projectPage;

// The agencies keep to two lines. When the names need more, "Show all agencies" follows them; it shows
// only while the two lines hide a name, measured again whenever the line's width changes. Two agency
// names hold commas, so the names are set apart with semicolons.
export function AgencyLine({ names }: { names: string[] }) {
  const id = useId();
  const line = useRef<HTMLParagraphElement>(null);
  const [open, setOpen] = useState(false);
  const [hides, setHides] = useState(false);
  useLayoutEffect(() => {
    const element = line.current;
    if (!element || open) return;
    const measure = () => setHides(element.scrollHeight > element.clientHeight + 1);
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => observer.disconnect();
  }, [open]);
  if (names.length === 0) return <p className="mt-2 max-w-prose text-body text-ink-muted">{words.noAgency}</p>;
  return (
    <div className="mt-2" data-agency-line>
      <p ref={line} id={id} className={open ? "max-w-prose text-body text-ink-muted" : "line-clamp-2 max-w-prose text-body text-ink-muted"}>
        <Fill template={names.length > 1 ? words.agenciesLine : words.agencyLine} slots={{ agencies: names.join(words.agencyJoin) }} />
      </p>
      {(hides || open) && (
        // The 44 px button centres its 20 px label line 12 px inside its top edge, so it rises 8 px and the
        // label's line sits 4 px under the agencies' last line, as a flush ghost button's label does beside
        // text (the 21 review, round 3, item 8). Its hover fill and focus ring then reach up over that gap. It
        // keeps 2 px under it, so the line stays as tall as the place the loading page holds for it (8 px up,
        // 2 px down; ProjectPage.tsx) and the section tabs never move when the project arrives.
        <div className="-mt-2 pb-0.5">
          <Button variant="ghost" flush onPage aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)}>
            {open ? words.fewerAgencies : words.allAgencies}
          </Button>
        </div>
      )}
    </div>
  );
}

// The h1's one line. Each " · item" keeps together, so a dot never ends a line and an item never splits:
// the line breaks only at the space before a dot, or inside the project's name.
export function ProjectHeaderLine({ project }: { project: Page["project"] }) {
  const status = project.status ? (words.statusInline[project.status] ?? project.status) : null;
  const item = (content: ReactNode) => (
    <>
      {" "}
      <span className="whitespace-nowrap text-ink-muted">
        {words.dot}
        {content}
      </span>
    </>
  );
  return (
    <>
      <span className="text-ink-heading">{project.display_name ?? project.project_name}</span>
      {item(<ProjectId pid={project.project_id} />)}
      {project.country && item(project.country)}
      {status && item(status)}
    </>
  );
}

