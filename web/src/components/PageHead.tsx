// Page head (DESIGN.md section 5, Page head; ticket 95): how every page starts, in the work's columns. It replaces the
// page header (PageHeader.tsx) as each page moves onto it.
//
// From the top: the alert slot, errors first, 24 px above the breadcrumb when it holds any; the breadcrumb, parents
// only, so an object's ID shows once in the head; 8 px under it the h1, 24/32 and 20/28 below 48rem, which takes focus
// when a route change moves to it and wraps in full however long; on an object's page its ID line, small mono
// ink-muted, 4 px under the h1, broken only at its spaces and never inside a part; the purpose, one or two sentences in
// body ink-muted, 12 px under what precedes it; and, on a workspace page below a frame of 1200 px, the facts line: the
// object's facts in one line of small and a flush ghost button that opens them in the evidence drawer (app.css hides it
// from that frame, where the side panel holds them). At most one primary action sits at the head's right when the page
// area allows (46rem), and under the purpose otherwise.
//
// Loading keeps the real breadcrumb and holds the h1's lines with static bars at the h1's height.
import { createElement, type ReactNode, type Ref } from "react";
import { cx } from "../lib/cx";
import { Breadcrumb, type Crumb } from "./Breadcrumb";
import { Button } from "./Button";
import { MonoWords } from "./MonoWords";
import { LoadingLabel, SkeletonLine, SkeletonText } from "./Skeleton";

export type FactsLine = {
  // The object's facts in one line, such as its method, market approach, amount and status.
  line: ReactNode;
  // The button's words, such as "Show the plan row".
  show: ReactNode;
  onShow: (button: HTMLElement) => void;
  // The facts show in the evidence drawer now.
  expanded?: boolean;
};

export function PageHead({
  level = 1,
  alert,
  trail,
  back,
  held = false,
  holdBack = false,
  title,
  titleRef,
  loading = false,
  narrowLines = 2,
  id,
  idAction,
  meta,
  purpose,
  facts,
  action,
}: {
  // Every page's title is its h1. The design gallery shows samples one level down, under its own h1.
  level?: 1 | 2;
  // The page's alerts, errors first. When the page's one request failed it holds the error alert with "Try again",
  // the title names the page, and nothing else draws.
  alert?: ReactNode;
  // The parents of this page, each a link.
  trail?: Crumb[];
  // The parent the link back goes to below 768 px, when it is not the last one.
  back?: Crumb;
  // The breadcrumb keeps its whole trail from a frame of 1200 px, as the work keeps its width beside the drawer.
  held?: boolean;
  // While the object loads, the link back holds two lines in a page column under 21rem, where the parent it will name
  // wraps, such as a package's project (ticket 101's design review, round 2).
  holdBack?: boolean;
  title: ReactNode;
  titleRef?: Ref<HTMLHeadingElement>;
  loading?: boolean;
  // How many h1 lines the skeleton holds below a 48rem page area, where a long title wraps more, such as a package's
  // Description (3; ticket 101's design review). From 48rem it holds two.
  narrowLines?: number;
  // An object's ID, such as its STEP reference.
  id?: string;
  // What follows the ID on its line, such as the copy key that copies it (ticket 112; the package page, ticket 101).
  idAction?: ReactNode;
  // An object with no ID yet: the line that stands in the ID line's place, such as a planned package's "No STEP
  // reference yet" and its saved stamp (ticket 101).
  meta?: ReactNode;
  purpose?: ReactNode;
  facts?: FactsLine;
  action?: ReactNode;
}) {
  return (
    <div data-page-head>
      {alert && (
        // A notice that draws nothing, such as the package page's notice of suggested PPSD rows with none, leaves no gap.
        <div data-head-alert className="mb-6 flex flex-col gap-2 empty:hidden">
          {alert}
        </div>
      )}
      {trail && trail.length > 0 && <Breadcrumb trail={trail} back={back} held={held} holdBack={holdBack} />}
      <div className={cx("flex flex-col gap-4 @head/page:flex-row @head/page:items-start @head/page:justify-between @head/page:gap-8", trail && trail.length > 0 && "mt-2")}>
        <div className="min-w-0 flex-1">
          {createElement(
            `h${level}`,
            {
              ref: titleRef,
              tabIndex: -1,
              "aria-busy": loading || undefined,
              className: "text-h1 wrap-break-word text-ink-heading focus:outline-none",
            },
            loading ? (
              <>
                {/* Below 48rem the title holds narrowLines lines, and from 28rem one fewer: with no purpose under it
                    since ticket 126, the zones under a two-line title showed the extra line as a jump. */}
                <span aria-hidden="true" className="flex flex-col text-h1 @md/page:hidden">
                  {Array.from({ length: narrowLines - 1 }, (_, index) => (
                    <SkeletonLine key={index} width="w-full" className={index > 0 ? "@[28rem]/page:hidden" : undefined} />
                  ))}
                  <SkeletonLine width="w-3/5" />
                </span>
                <SkeletonText className="hidden text-h1 @md/page:flex" widths={["w-full", "w-3/5"]} />
                <LoadingLabel />
              </>
            ) : (
              title
            ),
          )}
          {/* While the object loads, its ID line and its facts line keep their places (ticket 101). */}
          {id && loading && <SkeletonLine className="mt-1 text-small" width="w-48" />}
          {id && !loading && (
            <p data-id-line className="mt-1 text-small text-ink-muted">
              <MonoWords text={id} />
              {idAction}
            </p>
          )}
          {!id && meta != null && (
            <div data-id-line className="mt-1">
              {meta}
            </div>
          )}
          {purpose != null && <p className="mt-3 max-w-prose text-body text-pretty text-ink-muted">{purpose}</p>}
          {/* The facts line's place: below a 48rem page area its two lines (one from 34rem, ticket 126) over "Show the
              plan row"'s 44 px row, from 48rem one row (ticket 101's design review). */}
          {facts && loading && (
            <div data-facts-line aria-hidden="true" className="mt-3">
              <span aria-hidden="true" className="flex flex-col text-small @md/page:hidden">
                <SkeletonLine width="w-full" />
                <SkeletonLine width="w-2/5" className="@[34rem]/page:hidden" />
              </span>
              <div className="flex min-h-11 items-center">
                <SkeletonLine className="hidden text-small @md/page:flex" width="w-4/5" />
              </div>
            </div>
          )}
          {facts && !loading && (
            <div data-facts-line className="mt-3 flex flex-wrap items-center gap-x-3">
              <p className="text-small text-ink">{facts.line}</p>
              <Button variant="ghost" flush onPage aria-expanded={facts.expanded ?? false} onClick={(event) => facts.onShow(event.currentTarget)}>
                {facts.show}
              </Button>
            </div>
          )}
        </div>
        {action && <div className="flex shrink-0 flex-wrap items-center gap-3">{action}</div>}
      </div>
    </div>
  );
}
