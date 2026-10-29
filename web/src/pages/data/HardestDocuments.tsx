// "The hardest documents I read" (the 18 design brief, sections 2 to 5): the stress shelf, after the
// Sources table and before the fixes. Five rows in the slice file's order, each a claim and its proof:
// the document, what makes it hard, how many of its pages went to the layout parser, what I recovered
// against what the document holds, and the page where you can compare the two. A badge shows only for
// Partial or Gap, which the server set. Below 768 px of page area each row is a card. Since ticket 104 the section is a
// closed row with its one sentence, which opens in place.
//
// Every number comes from data_readiness_for's rows and opens its window, which says what it was counted
// against, the parser that read it and the table it counted. The page computes nothing (CLAUDE.md rule 1).
// A row with no document to show spans one note across its last three cells, with no badge and no link.
import type { ReactNode } from "react";
import { ExternalLink, pdfPageHref } from "../../components/ExternalLink";
import { ProjectId } from "../../components/ProjectId";
import { TextLink } from "../../components/TextLink";
import { sourcePageHref } from "../../lib/documents";
import { formatCount } from "../../lib/format";
import { Num } from "../../components/Num";
import { MeasureNum } from "../../components/MeasureNum";
import { FromLine, settingsFrom } from "../../components/NumFrom";
import { ReadinessTable, type ReadinessColumn, type ReadinessRow } from "../../components/ReadinessTable";
import { Skeleton } from "../../components/Skeleton";
import { StatusBadge } from "../../components/StatusBadge";
import { Template } from "../../components/Template";
import { DefinitionWindow } from "../../components/Term";
import { copy } from "../../copy";
import type { Readiness, ShelfEntry } from "../../lib/dataPages";
import { latestMeasured, MeasureValue, type Measures, type Noun } from "./measures";

// One of my own settings in a row's note: what it is, and that the measured run used it (DESIGN.md section 5, Number
// tooltip). It opens nothing, so it has no action line.
function Setting({ value, what, measures }: { value: number; what: string; measures: Measures }) {
  const used = latestMeasured(measures);
  return (
    <MeasureNum
      value={{ value, options: { compact: false } }}
      tooltip={what}
      from={used ? <FromLine words={settingsFrom(used)} /> : undefined}
    />
  );
}

const words = copy.dataReadiness.shelf;
export const SHELF_ID = "hardest-documents";

const head = (label: string, definition?: string): ReactNode =>
  definition ? (
    <DefinitionWindow label={label} title={label}>
      {definition}
    </DefinitionWindow>
  ) : (
    label
  );

// The column widths: 22, 30, 14, 18 and 16 percent from 1280 px, and 24, 26, 14, 18 and 18 below.
export const SHELF_COLUMNS: ReadinessColumn[] = [
  { key: "hard", name: words.columns.hard.label, label: words.columns.hard.label, about: words.columns.hard.about, width: "w-[26%] @xl/page:w-[30%]" },
  {
    key: "parser",
    name: words.columns.parser.label,
    label: head(words.columns.parser.label, words.columns.parser.definition),
    about: words.columns.parser.about,
    numeric: true,
    width: "w-[14%]",
  },
  {
    key: "outcome",
    name: words.columns.outcome.label,
    label: head(words.columns.outcome.label, words.columns.outcome.definition),
    about: words.columns.outcome.about,
    numeric: true,
    width: "w-[18%]",
  },
  // In a card the link stands on its own line, so the Page label is left to screen readers (design review r2 P6).
  { key: "page", name: words.columns.page.label, label: words.columns.page.label, about: words.columns.page.about, width: "w-[18%] @xl/page:w-[16%]", cardLabel: "hidden" },
];
export const SHELF_HEAD = { label: words.columns.document.label, width: "w-[24%] @xl/page:w-[22%]" };

function Stack({ children }: { children: ReactNode }) {
  return <div className="flex flex-col items-start gap-0.5">{children}</div>;
}

function Qualifier({ children }: { children: ReactNode }) {
  return <span className="text-caption text-ink-muted">{children}</span>;
}

const languageName = (entry: ShelfEntry) => copy.language.name[entry.document?.language ?? entry.language ?? ""] ?? "";
const fill = (text: string, entry: ShelfEntry, parts?: number | null) =>
  text
    .replace("{part}", copy.dataReadiness.server.shelfParts[entry.part ?? ""] ?? "")
    .replace("{languageName}", languageName(entry))
    // One to nine in words: "across three parts" (ticket 58; DESIGN.md section 7, rule 12).
    .replace("{parts}", parts == null ? "" : formatCount(parts));

// "{count} of {total}" in one Num, never a percentage: each row is one document, and its counts are small.
// The pair never wraps, so a narrow column wraps the words under it and never the number (critique r2).
const PAIR = "whitespace-nowrap";
function of(count: number, total: number) {
  return { share: { count, denominator: total, share_percent: null, share_bound: null, in_ten: null, in_ten_exact: null }, style: "table" as const };
}

function documentCell(entry: ShelfEntry, asOf: string): { header: ReactNode; caption: ReactNode; lang?: string } {
  const document = entry.document;
  if (!document) {
    // Before the reading, a rule's entry says when I choose its document; after a reading that found
    // none, it says nothing more, so no line contradicts the note beside it (design review r2 P5). Whether a rule
    // fills the entry is the slice file's to say (entry.rule; ticket 18's review round 3, P10).
    const rule = entry.rule !== null;
    return {
      header: words.entries[entry.kind],
      caption:
        rule && entry.state === "no_document" ? null : rule ? (
          words.chosenLater
        ) : entry.project_id ? (
          <ProjectId pid={entry.project_id} />
        ) : null,
    };
  }
  const project = (
    <Template
      text={words.project}
      values={{ project: <span className="wrap-anywhere">{document.project_name ?? document.project_id}</span>, pid: <ProjectId pid={document.project_id} /> }}
    />
  );
  const dated =
    document.document_date && document.pdf_pages !== null ? (
      <span className="tabular-nums">
        <Template text={words.dated} values={{ date: <Num date={document.document_date} style="table" today={asOf} />, pages: String(document.pdf_pages) }} />
      </span>
    ) : null;
  return {
    header: document.document_type,
    caption: (
      <>
        <span className="block">{project}</span>
        {dated && <span className="block">{dated}</span>}
      </>
    ),
  };
}

function windowWords(title: string, definition: string, entry: ShelfEntry, from?: ReactNode) {
  return {
    title,
    definition,
    rows: [
      ...(from ? [{ label: words.windowRows.from, value: from }] : []),
      ...(entry.parser ? [{ label: words.windowRows.parser, value: <span className="font-mono wrap-anywhere">{entry.parser}</span> }] : []),
    ],
  };
}

function parserCell(entry: ShelfEntry, measures: Measures): ReactNode {
  const row = entry.parser_row !== null ? measures.rows[entry.parser_row] : null;
  if (!row || row.count === null || row.denominator === null || entry.parser_row === null) return null;
  return (
    <Stack>
      <span className="font-semibold">
        <MeasureValue
          measures={measures}
          index={entry.parser_row}
          value={of(row.count, row.denominator)}
          noun={{ many: words.nouns.parser }}
          tooltipKind="ratio"
          className={PAIR}
          window={windowWords(words.windows.parser.title, words.windows.parser.definition, entry)}
        />
      </span>
      <Qualifier>{words.pages}</Qualifier>
    </Stack>
  );
}

function outcomeCell(entry: ShelfEntry, measures: Measures, asOf: string): ReactNode {
  if (entry.outcome_row === null) return null;
  const row = measures.rows[entry.outcome_row];
  const noun: Noun = { many: words.nouns[entry.kind] };
  const counts = fill(words.counts[entry.kind], entry, entry.parts);
  const outcome = { title: words.windows.outcome.title, definition: words.windows.outcomeKinds[entry.kind] ?? words.windows.outcome.definition };
  const badge = entry.status && (
    <span className="mt-1">
      <StatusBadge kind={entry.status} />
    </span>
  );
  if (row.denominator === null) {
    // No hand count: the number alone, what it lacks to be checked against, and a Gap when nothing
    // came back.
    return (
      <Stack>
        <span className="font-semibold">
          <MeasureValue measures={measures} index={entry.outcome_row} value={{ value: row.count ?? 0, options: { compact: false } }} noun={noun} window={windowWords(outcome.title, outcome.definition, entry)} />
        </span>
        <Qualifier>{counts}</Qualifier>
        <Qualifier>{words.noHandCount}</Qualifier>
        {badge}
      </Stack>
    );
  }
  const from = entry.denominator_from ? (
    <Template
      text={words.denominators[entry.denominator_from]}
      values={{
        denominator: <Num value={row.denominator} options={{ compact: false }} />,
        date: entry.counted_on ? <Num date={entry.counted_on} style="table" today={asOf} /> : "",
      }}
    />
  ) : undefined;
  return (
    <Stack>
      <span className="font-semibold">
        <MeasureValue
          measures={measures}
          index={entry.outcome_row}
          value={of(row.count ?? 0, row.denominator)}
          noun={noun}
          tooltipKind="ratio"
          className={PAIR}
          window={windowWords(outcome.title, outcome.definition, entry, from)}
        />
      </span>
      <Qualifier>{counts}</Qualifier>
      {badge}
    </Stack>
  );
}

function pageCell(entry: ShelfEntry): ReactNode {
  const document = entry.document;
  if (!document || entry.hard_page === null) return null;
  const page = String(entry.hard_page);
  return (
    <Stack>
      <TextLink
        href={sourcePageHref(document.project_id, document.document_id, entry.hard_page)}
        aria-label={words.pageLinkName(page, document.document_type, document.project_id)}
        className="text-small"
      >
        <Template text={words.pageLink} values={{ page: <span className="tabular-nums">{page}</span> }} />
      </TextLink>
      <Qualifier>{fill(words.pageLines[entry.kind], entry)}</Qualifier>
      {/* The page's picture is in the World Bank's PDF, which the source view does not show (the 21 design
          review, round 2, F16); the line above sits between the two links, so their targets keep apart. */}
      {document.pdf_url && (
        <ExternalLink href={pdfPageHref(document.pdf_url, entry.hard_page)} name={words.pdfLinkName(document.document_type, document.project_id)}>
          <Template text={words.pdfLink} values={{ page: <span className="tabular-nums">{page}</span> }} />
        </ExternalLink>
      )}
    </Stack>
  );
}

// The note that spans the last three cells when there is no outcome to show, in the table's own small
// type, so a row that records a non-event never draws the eye before an outcome (design review r2 P3).
function spanningNote(entry: ShelfEntry, measures: Measures): ReactNode | null {
  if (entry.state === "not_read") return <span className="text-small text-ink-muted">{words.notRead}</span>;
  if (entry.state === "no_document") {
    if (entry.kind === "over_parser_limit" && entry.longest_row !== null && entry.parser_limit_pages !== null) {
      const longest = measures.rows[entry.longest_row];
      return (
        <span className="text-small">
          <Template
            text={words.noDocumentOver}
            values={{
              limit: <Setting value={entry.parser_limit_pages} what={words.windows.limit} measures={measures} />,
              maxPages: (
                <MeasureValue
                  measures={measures}
                  index={entry.longest_row}
                  value={{ value: longest.count ?? 0, options: { compact: false } }}
                  noun={{ many: words.nouns.longest }}
                  window={windowWords(words.windows.longest.title, words.windows.longest.definition, entry)}
                />
              ),
            }}
          />
        </span>
      );
    }
    return <span className="text-small">{words.noDocument.replace("{description}", fill(words.descriptions[entry.kind] ?? "", entry))}</span>;
  }
  if (entry.state === "stopped_at_cap" && entry.read_pages_row !== null) {
    const read = measures.rows[entry.read_pages_row];
    return (
      <span className="flex flex-col gap-0.5 text-small">
        <span>
          <Template
            text={words.stopped}
            values={{
              read: (
                <MeasureValue
                  measures={measures}
                  index={entry.read_pages_row}
                  value={of(read.count ?? 0, read.denominator ?? 0)}
                  noun={{ many: words.nouns.read }}
                  tooltipKind="ratio"
                  className={PAIR}
                  window={windowWords(words.windows.read.title, words.windows.read.definition, entry)}
                />
              ),
            }}
          />
        </span>
        <span className="text-ink-muted">
          <Template
            text={words.stoppedNote}
            values={{ cap: <Setting value={entry.daily_page_cap ?? 0} what={words.windows.cap} measures={measures} /> }}
          />
        </span>
      </span>
    );
  }
  return null;
}

export function shelfRows(result: Readiness): ReadinessRow[] {
  const measures: Measures = { rows: result.rows, asOf: result.as_of };
  return result.stress_shelf.map((entry): ReadinessRow => {
    const { header, caption } = documentCell(entry, result.as_of);
    // After a reading that found no document, what I looked for; before any reading, a rule's entry in
    // words that don't say I read it (design review r2 P5, critique r2).
    const hard =
      entry.state === "no_document" && words.lookedFor[entry.kind] ? (
        words.lookedFor[entry.kind]
      ) : entry.state === "not_read" && words.hardBefore[entry.kind] ? (
        words.hardBefore[entry.kind]
      ) : (
        fill(words.hard[entry.kind], entry)
      );
    const note = spanningNote(entry, measures);
    // The documents API names every project in English, so no row header needs another language's lang.
    if (note !== null) return { id: entry.key, header, caption, cells: { hard }, span: note, spanFrom: "parser" };
    return {
      id: entry.key,
      header,
      caption,
      cells: { hard, parser: parserCell(entry, measures), outcome: outcomeCell(entry, measures, result.as_of), page: pageCell(entry) },
    };
  });
}

function sourceLine(result: Readiness): ReactNode {
  const measured = result.stress_shelf.find((entry) => entry.measured_on)?.measured_on;
  if (!measured) return null;
  return <Template text={words.sourceLine} values={{ date: <Num date={measured} style="table" today={result.as_of} className="whitespace-nowrap" /> }} />;
}

// Whether the section is open, and the press that opens or closes it: it starts as a closed row (ticket 104), since
// most readers skip it, and a link to #hardest-documents opens it.
export type ShelfToggle = { open: boolean; onToggle: () => void };

const closedRow = ({ open, onToggle }: ShelfToggle, more?: ReactNode) => ({
  summary: more ? (
    <>
      {words.summary} {more}
    </>
  ) : (
    words.summary
  ),
  toggle: { open, onToggle, show: words.show, hide: words.hide },
});

// The hardest documents and the plan pages the layout parser couldn't read are one section (ticket 58; the 16 and 18
// critiques found two sections about the parser back to back): the row's sentence says how the parser did with the
// plans, and the pages it couldn't read, when there are any, follow the table.
export function HardestDocuments({ result, failures, ...toggle }: { result: Readiness; failures?: { sentence: ReactNode; list: ReactNode } } & ShelfToggle) {
  if (result.stress_shelf.length === 0) return null;
  return (
    <ReadinessTable
      id="shelf"
      headingId={SHELF_ID}
      skeletonRows="shelf"
      title={words.title}
      lines={words.caption}
      head={SHELF_HEAD}
      columns={SHELF_COLUMNS}
      state={{ status: "ready", rows: shelfRows(result) }}
      source={sourceLine(result)}
      spanName={words.spanName}
      closed={closedRow(toggle, failures?.sentence)}
      after={failures?.list}
    />
  );
}

// While the measures load: the closed row with its sentence, and once opened the caption and one skeleton row for each
// entry in the slice file. When the plans' row is in view, the sentence on the plan pages waits for the measures, so a
// bar about its length holds its place after the row's own sentence (ticket 58).
export function HardestDocumentsLoading({ rows, failures = false, ...toggle }: { rows: number; failures?: boolean } & ShelfToggle) {
  if (rows === 0) return null;
  return (
    <ReadinessTable
      id="shelf"
      headingId={SHELF_ID}
      skeletonRows="shelf"
      title={words.title}
      lines={words.caption}
      head={SHELF_HEAD}
      columns={SHELF_COLUMNS}
      state={{ status: "loading", rows }}
      closed={closedRow(toggle, failures ? <Skeleton className="inline-block h-[1em] w-[55ch] max-w-full align-[-0.125em]" /> : undefined)}
    />
  );
}
