// How Strata writes numbers and dates (DESIGN.md section 6, Numbers, and section 7, rules 6,
// 11, 12, 13 and 15). Num renders what these functions return; nothing else formats a number.
// The words they use ("of", "in 10", "percent", month names aside) come from the copy file.
import { copy } from "../copy";

// DESIGN.md section 7, rules 6 and 15: no percentage or "in 10" from fewer than 20 cases,
// and under 50 cases the count stands beside "about N in 10". Ticket 12 put the 20 in
// config/thresholds.toml as past_range.min_comparables: find_comparables abstains below it and
// returns it, and the package workspace uses the tool's value. This file still writes both numbers
// here, because the Node test runner that checks it cannot read the thresholds file the way the
// bundler can; tests/test_find_comparables.py fails when the 20 here and the file's differ.
export const FEWEST_FOR_A_FREQUENCY = 20;
export const FEWEST_FOR_A_PERCENTAGE = 50;

const grouped = (decimals: number) =>
  new Intl.NumberFormat("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

// Section 6: two decimals below 1, one up to 100, none above. Whole numbers keep none. The
// size is read again after rounding, so a number rounded over a boundary takes the next
// size's rule: 99.95 reads 100, not 100.0, and 0.995 reads 1.0, not 1.00.
const decimalsBySize = (size: number) => (size < 1 ? 2 : size < 100 ? 1 : 0);
const rounded = (value: number, decimals: number) => Number(grouped(decimals).format(value).replaceAll(",", ""));

function defaultDecimals(value: number): number {
  if (Number.isInteger(value)) return 0;
  const first = decimalsBySize(Math.abs(value));
  return decimalsBySize(Math.abs(rounded(value, first)));
}

const UNITS = [
  { size: 1e9, suffix: "B" },
  { size: 1e6, suffix: "M" },
  { size: 1e3, suffix: "K" },
];

// Section 6: K from 10,000, then M and B, with one decimal below 100 and none above.
// A trailing ".0" is dropped, so 10,000 reads "10K". A number that rounds to 10,000, such as
// 9999.6, reads "10K" too.
function compact(value: number): string | null {
  const size = Math.abs(value);
  if (Math.abs(rounded(value, defaultDecimals(value))) < 10_000) return null;
  let unit = UNITS.findIndex((candidate) => size >= candidate.size);
  for (;;) {
    const mantissa = size / UNITS[unit].size;
    let text = grouped(mantissa < 100 ? 1 : 0).format(mantissa);
    if (Number(text) >= 100) text = grouped(0).format(mantissa);
    if (Number(text.replaceAll(",", "")) >= 1000 && unit > 0) {
      unit -= 1;
      continue;
    }
    const sign = value < 0 ? "-" : "";
    return `${sign}${text.replace(/\.0$/, "")}${UNITS[unit].suffix}`;
  }
}

export type NumberOptions = {
  // The tool's own rounding. Strata states a number at the rounding the tool returned.
  decimals?: number;
  // False writes the number in full with comma thousands. A STEP amount also passes
  // decimals: 2, so it shows its cents as STEP does.
  compact?: boolean;
};

export function formatNumber(value: number, options: NumberOptions = {}): string {
  const { decimals, compact: shorten = true } = options;
  if (shorten && decimals === undefined) {
    const short = compact(value);
    if (short) return short;
  }
  return grouped(decimals ?? defaultDecimals(value)).format(value);
}

// Section 7, rule 11: in a sentence a large amount reads "12.5 million" or "2 billion" (the
// sentence writes the "US$" before it), with one decimal below 100 and a trailing ".0" dropped.
// Below a million it is written in full. A STEP amount a reader looks up in STEP keeps its cents
// instead (formatNumber with decimals: 2).
export function formatAmountText(value: number): string {
  const size = Math.abs(value);
  // It rounds before it chooses: from 999.5 million an amount reads "1,000 million" rounded, so it
  // takes billions' rule and reads "1 billion".
  const unit = size >= 999_500_000 ? { size: 1e9, words: copy.num.billion } : size >= 1e6 ? { size: 1e6, words: copy.num.million } : null;
  if (!unit) return formatNumber(value, { compact: false });
  const mantissa = value / unit.size;
  return unit.words(grouped(Math.abs(mantissa) < 100 ? 1 : 0).format(mantissa).replace(/\.0$/, ""));
}

// A package's own difference from its cost estimate (ticket 31): a measurement of one package, not a share of a
// group, so DESIGN.md section 7's rule 6 does not stop it under 20 cases (rule 11). The tool rounded it (one
// decimal up to 100, none above); this writes it with a plus sign above zero and a true minus sign (U+2212)
// below: "+21.4%" in charts and tables, or "21.4 percent above" in sentences.
export function formatSignedPercent(value: number, options: { style?: "short" | "words" } = {}): string {
  const text = grouped(Number.isInteger(value) ? 0 : 1).format(Math.abs(value));
  if (options.style === "words") {
    return value > 0 ? copy.num.percentAbove(text) : value < 0 ? copy.num.percentBelow(text) : copy.num.percentAtZero;
  }
  return copy.num.signedPercent(value > 0 ? copy.num.plus : value < 0 ? copy.num.minus : "", text);
}

// Years have no comma.
export function formatYear(year: number): string {
  return String(year);
}

// A moment's clock time in the reader's own time zone, "2:26 p.m." (ticket 58), and whether it falls on the reader's
// today. Dates elsewhere are UTC days; a time is read on the reader's clock, so it is the reader's.
export function formatTime(iso: string): string {
  const parts = new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", hour12: true }).formatToParts(new Date(iso));
  const part = (type: string) => parts.find((one) => one.type === type)?.value ?? "";
  return copy.time.clock(part("hour"), part("minute"), part("dayPeriod").toUpperCase() === "AM" ? copy.time.am : copy.time.pm);
}

export function isToday(iso: string, now: Date = new Date()): boolean {
  return new Date(iso).toDateString() === now.toDateString();
}

// A moment's day in the reader's own time zone, as YYYY-MM-DD, so a row from yesterday evening never shows today's UTC
// date (the 58 design review, follow-up 19). A plain date is its own day.
export function localDay(iso: string): string {
  if (iso.length <= 10) return iso;
  const day = new Date(iso);
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${day.getFullYear()}-${pad(day.getMonth() + 1)}-${pad(day.getDate())}`;
}

// Section 7, rule 12: one to nine in words, numerals from 10. A word that starts a sentence takes
// a capital ("One needs a look").
export function formatCount(count: number, options: { capital?: boolean } = {}): string {
  if (Number.isInteger(count) && count >= 1 && count <= 9) {
    const word = copy.num.words[count - 1];
    return options.capital ? word.charAt(0).toUpperCase() + word.slice(1) : word;
  }
  return grouped(defaultDecimals(count)).format(count);
}

export type Ratio = {
  // What a sentence shows: the count, and beside it the frequency when there are enough cases.
  text: string;
  count: string;
  frequency: string | null;
};

// Section 7, rules 6 and 15. "6 of 12" under 20 cases; "31 of 37, about 8 in 10" from 20 to
// 49; "42 of 50, 84 percent" from 50, with "%" in tables and charts (rule 11).
export function formatRatio(part: number, whole: number, options: { style?: "sentence" | "table" } = {}): Ratio {
  const count = copy.num.of(formatNumber(part, { compact: false }), formatNumber(whole, { compact: false }));
  let frequency: string | null = null;
  if (whole >= FEWEST_FOR_A_FREQUENCY && part > 0 && part < whole) {
    if (whole >= FEWEST_FOR_A_PERCENTAGE) {
      const percent = Math.round((part / whole) * 100);
      const table = options.style === "table";
      // part is above 0 and below whole here, so 0 and 100 would overstate how close it is.
      frequency =
        percent === 0
          ? table ? copy.num.underOnePercentShort : copy.num.underOnePercent
          : percent === 100
            ? table ? copy.num.overNinetyNinePercentShort : copy.num.overNinetyNinePercent
            : table ? copy.num.percentShort(percent) : copy.num.percent(percent);
    } else {
      const tenths = (part / whole) * 10;
      const inTen = Math.round(tenths);
      frequency =
        inTen === 0
          ? copy.num.fewerThanOneInTen
          : inTen === 10
            ? copy.num.moreThanNineInTen
            : tenths === inTen
              ? copy.num.inTen(inTen)
              : copy.num.aboutInTen(inTen);
    }
  }
  return { text: frequency ? copy.num.countWithFrequency(count, frequency) : count, count, frequency };
}

// A share a tool worked out (CLAUDE.md rule 1): its count and denominator, and the frequency the
// tool rounded by the same rules as formatRatio, so the browser divides nothing. src/strata/tools/
// data_readiness_for.py's share() gives these columns: share_percent from 50 cases, in_ten from 20,
// and share_bound when a part rounds to an end of its scale.
export type ToolShare = {
  count: number;
  denominator: number;
  share_percent: number | null;
  share_bound: "under" | "over" | null;
  in_ten: number | null;
  in_ten_exact: boolean | null;
};

export function formatToolShare(share: ToolShare, options: { style?: "sentence" | "table" } = {}): Ratio {
  const count = copy.num.of(formatNumber(share.count, { compact: false }), formatNumber(share.denominator, { compact: false }));
  const table = options.style === "table";
  let frequency: string | null = null;
  if (share.share_percent !== null) {
    frequency =
      share.share_bound === "under"
        ? table ? copy.num.underOnePercentShort : copy.num.underOnePercent
        : share.share_bound === "over"
          ? table ? copy.num.overNinetyNinePercentShort : copy.num.overNinetyNinePercent
          : table ? copy.num.percentShort(share.share_percent) : copy.num.percent(share.share_percent);
  } else if (share.in_ten !== null) {
    frequency =
      share.share_bound === "under"
        ? copy.num.fewerThanOneInTen
        : share.share_bound === "over"
          ? copy.num.moreThanNineInTen
          : share.in_ten_exact
            ? copy.num.inTen(share.in_ten)
            : copy.num.aboutInTen(share.in_ten);
  }
  return { text: frequency ? copy.num.countWithFrequency(count, frequency) : count, count, frequency };
}

export type DateStyle = "sentence" | "table" | "short" | "month";

// Section 7, rule 13: "March 4, 2024" in sentences and "Mar 4, 2024" in tables. "short" is the
// freshness stamp's form: "Oct 21" in the current year and "Dec 30, 2025" in any other. "month" is
// a frozen source's on the Data readiness page: "Jun 2016".
// Dates arrive as ISO dates ("2024-03-04") and are read in UTC, so no time zone moves them.
// Home's date line (ticket 41): the weekday and the day, "Wednesday, October 28", with the year only when it is not
// this year's, or always when asked, as an as-of date is.
export function formatDayLine(iso: string, options: { today?: string; withYear?: boolean } = {}): string {
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  const today = options.today ? new Date(`${options.today}T00:00:00Z`) : new Date();
  const year = options.withYear || date.getUTCFullYear() !== today.getUTCFullYear();
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    weekday: "long",
    month: "long",
    day: "numeric",
    year: year ? "numeric" : undefined,
  }).format(date);
}

export function formatDate(iso: string, options: { style?: DateStyle; today?: string } = {}): string {
  const style = options.style ?? "sentence";
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  const today = options.today ? new Date(`${options.today}T00:00:00Z`) : new Date();
  const sameYear = date.getUTCFullYear() === today.getUTCFullYear();
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    month: style === "sentence" ? "long" : "short",
    day: style === "month" ? undefined : "numeric",
    year: style === "short" && sameYear ? undefined : "numeric",
  }).format(date);
}
