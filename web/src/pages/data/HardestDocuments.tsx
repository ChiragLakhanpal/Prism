// "The hardest documents I read" (the 18 design brief, sections 2 to 5): the stress shelf, after the
// Sources table and before the fixes. Five rows in the slice file's order, each a claim and its proof:
// the document, what makes it hard, how many of its pages went to the layout parser, what I recovered
// against what the document holds, and the page where you can compare the two. A badge shows only for
// Partial or Gap, which the server set. Below 768 px of page area each row is a card.
//
// Every number comes from data_readiness_for's rows and opens its window, which says what it was counted
// against, the parser that read it and the table it counted. The page computes nothing (CLAUDE.md rule 1).
// A row with no document to show spans one note across its last three cells, with no badge and no link.
import type { ReactNode } from "react";
import { ExternalLink, pdfPageHref } from "../../components/ExternalLink";
import { ProjectId } from "../../components/ProjectId";
import { TextLink } from "../../components/TextLink";
import { sourcePageHref } from "../../lib/documents";
import { Num } from "../../components/Num";
import { MeasureNum } from "../../components/MeasureNum";
import { ReadinessTable, type ReadinessColumn, type ReadinessRow } from "../../components/ReadinessTable";
import { StatusBadge } from "../../components/StatusBadge";
import { Template } from "../../components/Template";
import { DefinitionWindow } from "../../components/Term";
import { copy } from "../../copy";
import type { Readiness, ShelfEntry } from "../../lib/dataPages";
import { MeasureValue, type Measures, type Noun } from "./measures";

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
  { key: "hard", name: words.columns.hard.label, label: words.columns.hard.label, about: words.columns.hard.about, width: "w-[26%] xl:w-[30%]" },
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
  { key: "page", name: words.columns.page.label, label: words.columns.page.label, about: words.columns.page.about, width: "w-[18%] xl:w-[16%]", cardLabel: "hidden" },
];
export const SHELF_HEAD = { label: words.columns.document.label, width: "w-[24%] xl:w-[22%]" };

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
    .replace("{parts}", String(parts ?? ""));

// "{count} of {total}" in one Num, never a percentage: each row is one document, and its counts are small.
// The pair never wraps, so a narrow column wraps the words under it and never the number (critique r2).
const PAIR = "whitespace-nowrap";
function of(count: number, total: number) {
  return { share: { count, denominator: total, share_percent: null, share_bound: null, in_ten: null, in_ten_exact: null }, style: "table" as const };
}

// An entry that a rule fills at run time, rather than one that names its document.
const RULES = new Set(["longest_pad", "over_parser_limit"]);

function documentCell(entry: ShelfEntry, asOf: string): { header: ReactNode; caption: ReactNode; lang?: string } {
  const document = entry.document;
  if (!document) {
    // Before the reading, a rule's entry says when I choose its document; after a reading that found
    // none, it says nothing more, so no line contradicts the note beside it (design review r2 P5).
    const rule = RULES.has(entry.kind);
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
              limit: <MeasureNum value={{ value: entry.parser_limit_pages, options: { compact: false } }} tooltip={words.windows.limit} />,
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
            values={{ cap: <MeasureNum value={{ value: entry.daily_page_cap ?? 0, options: { compact: false } }} tooltip={words.windows.cap} /> }}
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

export function HardestDocuments({ result }: { result: Readiness }) {
  if (result.stress_shelf.length === 0) return null;
  return (
    <div className="mt-12">
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
      />
    </div>
  );
}

// While the measures load: the title, the caption and one skeleton row for each entry in the slice file.
export function HardestDocumentsLoading({ rows }: { rows: number }) {
  if (rows === 0) return null;
  return (
    <div className="mt-12">
      <ReadinessTable
        id="shelf"
        headingId={SHELF_ID}
        skeletonRows="shelf"
        title={words.title}
        lines={words.caption}
        head={SHELF_HEAD}
        columns={SHELF_COLUMNS}
        state={{ status: "loading", rows }}
      />
    </div>
  );
}
