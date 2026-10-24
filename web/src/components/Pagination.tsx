// Pagination (DESIGN.md section 5; the 21 brief, section 10): a named nav with "Previous page" and "Next
// page" links 44 px tall, and "Page {n} of {m}" in caption between them. They are links, because each
// changes the address (?page=), so Back steps through the pages. A missing link keeps its space, so the
// bar never shifts. Below 360 px the words shorten on screen to "Previous" and "Next", and the links'
// names stay whole. With one page there is nothing to page through, and the bar is not drawn.
import { ChevronLeft, ChevronRight } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { formatNumber } from "../lib/format";
import { TextLink } from "./TextLink";

const n = (value: number) => formatNumber(value, { compact: false });
const LINK = "inline-flex h-11 items-center gap-1 text-small";

export function Pagination({
  label,
  page,
  pages,
  href,
  className,
}: {
  label: string;
  page: number;
  pages: number;
  href: (page: number) => string;
  className?: string;
}) {
  if (pages <= 1) return null;
  const words = copy.pagination;
  return (
    <nav aria-label={label} data-pagination className={cx("flex items-center justify-between gap-4", className)}>
      <TextLink
        href={href(page - 1)}
        aria-label={words.previous}
        aria-hidden={page <= 1 || undefined}
        tabIndex={page <= 1 ? -1 : undefined}
        className={cx(LINK, page <= 1 && "invisible")}
      >
        <ChevronLeft aria-hidden="true" className="size-4 shrink-0" />
        <span className="xs:hidden">{words.previousShort}</span>
        <span className="hidden xs:inline">{words.previous}</span>
      </TextLink>
      <p className="text-caption text-ink-muted tabular-nums">{words.position(n(page), n(pages))}</p>
      <TextLink
        href={href(page + 1)}
        aria-label={words.next}
        aria-hidden={page >= pages || undefined}
        tabIndex={page >= pages ? -1 : undefined}
        className={cx(LINK, page >= pages && "invisible")}
      >
        <span className="xs:hidden">{words.nextShort}</span>
        <span className="hidden xs:inline">{words.next}</span>
        <ChevronRight aria-hidden="true" className="size-4 shrink-0" />
      </TextLink>
    </nav>
  );
}
