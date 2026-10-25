// A sentence the server wrote from copy templates and tool values (ticket 23's timeline finding and alt text, as
// ticket 16's headline does): its text as it came, and each count, year or date through Num, so the page writes
// every number and date one way and computes none. plain gives the same words as one string, for an svg's name.
// check makes each count explain itself, as the timeline's title count opens its table.
import { Fragment } from "react";
import { formatCount, formatDate, formatYear } from "../lib/format";
import type { Segment } from "../lib/timeline";
import { Num, type NumCheck } from "./Num";

export function segmentsText(segments: Segment[]): string {
  return segments
    .map((segment) =>
      "text" in segment
        ? segment.text
        : "year" in segment
          ? formatYear(segment.year)
          : "date" in segment
            ? formatDate(segment.date)
            : formatCount(segment.number, { capital: segment.capital }),
    )
    .join("");
}

export function SegmentText({ segments, plain = false, check }: { segments: Segment[]; plain?: boolean; check?: NumCheck }) {
  if (plain) return <>{segmentsText(segments)}</>;
  return (
    <>
      {segments.map((segment, index) => (
        <Fragment key={index}>
          {"text" in segment ? (
            segment.text
          ) : "year" in segment ? (
            <Num year={segment.year} />
          ) : "date" in segment ? (
            <Num date={segment.date} />
          ) : (
            <Num count={segment.number} capital={segment.capital} check={check} />
          )}
        </Fragment>
      ))}
    </>
  );
}
