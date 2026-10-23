// How Strata writes numbers and dates (DESIGN.md section 6, Numbers, and section 7, rules 6,
// 11, 12, 13 and 15). Num renders what these functions return; nothing else formats a number.
// The words they use ("of", "in 10", "percent", month names aside) come from the copy file.
import { copy } from "../copy";

// DESIGN.md section 7, rules 6 and 15: no percentage or "in 10" from fewer than 20 cases,
// and under 50 cases the count stands beside "about N in 10".
export const FEWEST_FOR_A_FREQUENCY = 20;
export const FEWEST_FOR_A_PERCENTAGE = 50;

const grouped = (decimals: number) =>
  new Intl.NumberFormat("en-US", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });

// Section 6: two decimals below 1, one up to 100, none above. Whole numbers keep none.
function defaultDecimals(value: number): number {
  const size = Math.abs(value);
  if (Number.isInteger(value)) return 0;
  return size < 1 ? 2 : size < 100 ? 1 : 0;
}

const UNITS = [
  { size: 1e9, suffix: "B" },
  { size: 1e6, suffix: "M" },
  { size: 1e3, suffix: "K" },
];

// Section 6: K from 10,000, then M and B, with one decimal below 100 and none above.
// A trailing ".0" is dropped, so 10,000 reads "10K".
function compact(value: number): string | null {
  const size = Math.abs(value);
  if (size < 10_000) return null;
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
  // False writes the whole number with comma thousands, as for STEP amounts to the cent.
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

// Years have no comma.
export function formatYear(year: number): string {
  return String(year);
}

// Section 7, rule 12: one to nine in words, numerals from 10.
export function formatCount(count: number): string {
  if (Number.isInteger(count) && count >= 1 && count <= 9) return copy.num.words[count - 1];
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
      frequency = options.style === "table" ? copy.num.percentShort(percent) : copy.num.percent(percent);
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

export type DateStyle = "sentence" | "table" | "short";

// Section 7, rule 13: "March 4, 2024" in sentences and "Mar 4, 2024" in tables. "short" is the
// freshness stamp's form: "Oct 21" in the current year and "Dec 30, 2025" in any other.
// Dates arrive as ISO dates ("2024-03-04") and are read in UTC, so no time zone moves them.
export function formatDate(iso: string, options: { style?: DateStyle; today?: string } = {}): string {
  const style = options.style ?? "sentence";
  const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`);
  const today = options.today ? new Date(`${options.today}T00:00:00Z`) : new Date();
  const sameYear = date.getUTCFullYear() === today.getUTCFullYear();
  return new Intl.DateTimeFormat("en-US", {
    timeZone: "UTC",
    month: style === "sentence" ? "long" : "short",
    day: "numeric",
    year: style === "short" && sameYear ? undefined : "numeric",
  }).format(date);
}
