// Document: one numbered paragraph of a source, as a citation points to it. It shows the
// whole paragraph word for word with the matching words highlighted, then the source line
// (which says where the paragraph sits), and a link to the page in the World Bank's PDF. A passage in French,
// Spanish or Portuguese carries its lang attribute (DESIGN.md section 10).
//
// States: ready, loading (a skeleton sized to the passage), failed (with "Try again"), and
// missing (no source has this ID).
import type { ReactNode } from "react";
import { copy } from "../copy";
import { Alert } from "./Alert";
import { Button } from "./Button";
import { LoadingLabel, SkeletonLine, SkeletonText } from "./Skeleton";
import { TextLink } from "./TextLink";

// Matched words: the highlight fill, with the start and end said aloud, because most screen
// readers do not announce a <mark>.
export function Highlight({ children }: { children: ReactNode }) {
  return (
    <mark className="bg-highlight text-ink [box-decoration-break:clone]">
      <span className="sr-only">{copy.document.highlightStarts} </span>
      {children}
      <span className="sr-only"> {copy.document.highlightEnds}</span>
    </mark>
  );
}

// The paragraph with the given character ranges highlighted.
export function highlighted(text: string, ranges: [number, number][] = []): ReactNode[] {
  const parts: ReactNode[] = [];
  let at = 0;
  for (const [start, end] of [...ranges].sort((a, b) => a[0] - b[0])) {
    if (start > at) parts.push(text.slice(at, start));
    parts.push(<Highlight key={start}>{text.slice(Math.max(start, at), end)}</Highlight>);
    at = Math.max(at, end);
  }
  if (at < text.length) parts.push(text.slice(at));
  return parts;
}

export type Passage = {
  docType: string;
  pcode: string;
  // Already written by Num or formatDate, such as "June 30, 2021".
  date: string;
  para: number;
  page: number;
  text: string;
  highlights?: [number, number][];
  lang?: string;
  pdfHref: string;
};

export type DocumentState =
  | { status: "ready"; passage: Passage }
  | { status: "loading" }
  | { status: "failed"; onRetry: () => void }
  | { status: "missing" };

export function Document({ state }: { state: DocumentState }) {
  if (state.status === "loading") {
    return (
      <div data-document="loading" aria-busy="true" className="max-w-prose">
        <LoadingLabel />
        {/* The ready layout, line for line: the quoted paragraph, the source line and the link. */}
        <div className="border-l-2 border-line pl-4 text-body">
          <SkeletonText widths={["w-full", "w-full", "w-full", "w-3/5"]} />
        </div>
        <SkeletonText className="mt-3 text-caption" widths={["w-full", "w-2/5"]} />
        <SkeletonLine className="mt-2 text-small" width="w-1/2" />
      </div>
    );
  }
  if (state.status === "failed") {
    return (
      <Alert
        state="error"
        live="alert"
        action={
          <Button variant="secondary" onClick={state.onRetry}>
            {copy.answer.tryAgain}
          </Button>
        }
      >
        {copy.document.failed}
      </Alert>
    );
  }
  if (state.status === "missing") {
    return <Alert state="neutral">{copy.document.missing}</Alert>;
  }
  const { passage } = state;
  const page = String(passage.page);
  const source = copy.document.sourceLine(passage.docType, passage.date, String(passage.para), page);
  return (
    <article data-document="ready" className="max-w-prose">
      <blockquote lang={passage.lang} className="border-l-2 border-line-strong pl-4 text-body text-ink">
        <p>{highlighted(passage.text, passage.highlights)}</p>
      </blockquote>
      <p className="mt-3 text-caption text-ink-muted" data-numbers>
        <span className="font-bold">{copy.document.source}</span> {source.before}
        <span className="font-mono">{passage.pcode}</span>
        {source.after}
      </p>
      <p className="mt-2 text-small">
        <TextLink href={passage.pdfHref} target="_blank" rel="noreferrer">
          {copy.document.openAtPage(page)}
          <span className="sr-only">{copy.document.newTab}</span>
        </TextLink>
      </p>
    </article>
  );
}
