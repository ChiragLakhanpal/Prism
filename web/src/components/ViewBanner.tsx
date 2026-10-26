// View banner (ticket 40; the 40 brief, 3.4; DESIGN.md section 5, Alerts): the preview banner and the as-of banner at
// the top of the alert slot, after error alerts. Each is an info Alert in a labelled region that takes focus after a
// view or date change, with its way out as a link under its sentences ("Leave the preview", "Back to today"). It never
// closes or collapses, at any width, and it is not sticky.
import { forwardRef, type ReactNode } from "react";
import { Alert } from "./Alert";
import { TextLink } from "./TextLink";

export const ViewBanner = forwardRef<
  HTMLElement,
  { kind: "preview" | "asof"; region: string; href: string; link: string; children: ReactNode }
>(function ViewBanner({ kind, region, href, link, children }, ref) {
  return (
    <section
      ref={ref}
      aria-label={region}
      tabIndex={-1}
      data-view-banner={kind}
      className="rounded-r-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
    >
      <Alert
        state="info"
        action={
          <TextLink data-mode href={href} data-banner-link={kind}>
            {link}
          </TextLink>
        }
      >
        {children}
      </Alert>
    </section>
  );
});
