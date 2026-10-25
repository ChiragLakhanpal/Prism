// Pagination (DESIGN.md section 5; the 21 brief, section 10, built first by ticket 29): a named nav under a
// list, "Previous page   Page 1 of 2   Next page", on one row of three columns, the page count in the middle
// one and each link at its end. They are links 44 px tall, because each changes the address (?page=), so
// Back steps through the pages. A missing link leaves its place, so the others never move. Below 25rem the
// page count takes a row of its own above the two links, so neither link wraps. With one page there is
// nothing to page through, and the bar is not drawn.
import { ChevronLeft, ChevronRight } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { Fill } from "./Fill";
import { Num } from "./Num";
import { TextLink } from "./TextLink";

const LINK = "inline-flex h-11 items-center gap-1";

export function Pagination({
  label = copy.pagination.label,
  page,
  pages,
  href,
  className,
}: {
  // The nav's name, such as "Pages of the project list", when a page has more than one list.
  label?: string;
  page: number;
  pages: number;
  href: (page: number) => string;
  className?: string;
}) {
  if (pages <= 1) return null;
  const p = copy.pagination;
  return (
    <nav aria-label={label} data-pagination className={cx("@container/pager", className)}>
      <div className="grid grid-cols-2 items-center gap-x-4 text-small @min-[25rem]/pager:grid-cols-[1fr_auto_1fr]">
        <span className="row-start-2 @min-[25rem]/pager:row-start-1">
          {page > 1 && (
            <TextLink href={href(page - 1)} className={LINK}>
              <ChevronLeft aria-hidden="true" className="size-4 shrink-0" />
              {p.previous}
            </TextLink>
          )}
        </span>
        <span className="col-span-full row-start-1 justify-self-center text-ink-muted @min-[25rem]/pager:col-span-1" aria-current="page" data-page-count>
          <Fill template={p.page} slots={{ page: <Num value={page} options={{ compact: false }} />, pages: <Num value={pages} options={{ compact: false }} /> }} />
        </span>
        <span className="row-start-2 justify-self-end @min-[25rem]/pager:row-start-1">
          {page < pages && (
            <TextLink href={href(page + 1)} className={LINK}>
              {p.next}
              <ChevronRight aria-hidden="true" className="size-4 shrink-0" />
            </TextLink>
          )}
        </span>
      </div>
    </nav>
  );
}
