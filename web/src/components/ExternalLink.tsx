// External link (DESIGN.md section 5; the 14 and 18 briefs): a link that leaves Prism, such as the
// World Bank's PDF at a page or a notice's page on the World Bank's site. It is small, primary and
// underlined, with lucide's external-link icon at 16 px after its last word, tied to it by a word joiner
// so the two wrap together, and a visually hidden ", opens in a new tab" at the end of its name. It
// opens in a new tab with rel="noopener noreferrer", hovers to link-hover and keeps its underline.
//
// pdfPageHref is the one helper that builds an "Open at page" address. The evidence drawer and the
// Data readiness page's hardest documents both use it, so ticket 21 can point it at the in-app source
// view and change both links at once.
import type { ReactNode } from "react";
import { ExternalLink as ExternalIcon } from "lucide-react";
import { copy } from "../copy";
import { cx } from "../lib/cx";
import { WORD_JOINER } from "./CitationMarker";
import { TextLink } from "./TextLink";

// The World Bank's PDF of a document, opened at a page (ticket 21 repoints this at the source view).
export function pdfPageHref(pdfUrl: string, page: number): string {
  return `${pdfUrl.replace(/^http:\/\//, "https://")}#page=${page}`;
}

export function ExternalLink({
  href,
  children,
  name,
  label,
  className,
}: {
  href: string;
  children: ReactNode;
  // More of the link's name, read after its words on screen and before ", opens in a new tab", when
  // its words alone would be ambiguous on the page, as five "Open at page" links are in one table. The
  // name starts with the words on screen (WCAG 2.2 SC 2.5.3).
  name?: string;
  // The link's whole name, when its words on screen are too short to stand alone, such as "PDF" in a
  // documents table (ticket 21). It holds the words on screen and ends with "(opens in a new tab)".
  label?: string;
  className?: string;
}) {
  return (
    <TextLink href={href} target="_blank" rel="noopener noreferrer" aria-label={label} className={cx("text-small", className)}>
      {children}
      {!label && (
        <span className="sr-only">
          {name}
          {copy.document.newTab}
        </span>
      )}
      {/* The icon sits after the last word, tied to it by a word joiner, so the two wrap together; both
          are left out of the link's name. */}
      <span aria-hidden="true" className="whitespace-nowrap">
        {WORD_JOINER}
        <ExternalIcon aria-hidden="true" className="ml-1 inline-block size-4 align-[-2px]" />
      </span>
    </TextLink>
  );
}
