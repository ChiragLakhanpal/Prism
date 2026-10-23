// The number rules Num enforces (DESIGN.md sections 6 and 7), checked against literal
// strings. Num renders exactly what these functions return.
import { expect, test } from "@playwright/test";
import { formatCount, formatDate, formatNumber, formatRatio, formatYear } from "../src/lib/format";

test("a ratio under 20 cases is a count and never a percentage", () => {
  expect(formatRatio(6, 12)).toEqual({ text: "6 of 12", count: "6 of 12", frequency: null });
  expect(formatRatio(19, 19).text).toBe("19 of 19");
  expect(formatRatio(0, 12).text).toBe("0 of 12");
});

test("a ratio from 20 to 49 cases shows the count beside about N in 10", () => {
  expect(formatRatio(31, 37)).toEqual({ text: "31 of 37, about 8 in 10", count: "31 of 37", frequency: "about 8 in 10" });
  expect(formatRatio(24, 30).text).toBe("24 of 30, 8 in 10");
  expect(formatRatio(1, 40).text).toBe("1 of 40, fewer than 1 in 10");
  expect(formatRatio(39, 40).text).toBe("39 of 40, more than 9 in 10");
  expect(formatRatio(37, 37).text).toBe("37 of 37");
  expect(formatRatio(0, 37).text).toBe("0 of 37");
});

test("a ratio from 50 cases shows the count beside a whole percentage", () => {
  expect(formatRatio(42, 50).text).toBe("42 of 50, 84 percent");
  expect(formatRatio(37, 52).text).toBe("37 of 52, 71 percent");
  expect(formatRatio(93, 118, { style: "table" }).text).toBe("93 of 118, 79%");
});

test("numbers have comma thousands, then K from 10,000, then M and B", () => {
  expect(formatNumber(7)).toBe("7");
  expect(formatNumber(1234)).toBe("1,234");
  expect(formatNumber(9999)).toBe("9,999");
  expect(formatNumber(10000)).toBe("10K");
  expect(formatNumber(12500)).toBe("12.5K");
  expect(formatNumber(99950)).toBe("100K");
  expect(formatNumber(295689)).toBe("296K");
  expect(formatNumber(999999)).toBe("1M");
  expect(formatNumber(1250000)).toBe("1.3M");
  expect(formatNumber(45678901)).toBe("45.7M");
  expect(formatNumber(2500000000)).toBe("2.5B");
  expect(formatNumber(-12500)).toBe("-12.5K");
});

test("decimals: two below 1, one up to 100, none above, unless the tool's rounding is given", () => {
  expect(formatNumber(0.456)).toBe("0.46");
  expect(formatNumber(0.5)).toBe("0.50");
  expect(formatNumber(45.67)).toBe("45.7");
  expect(formatNumber(456.7)).toBe("457");
  expect(formatNumber(4567.8)).toBe("4,568");
  expect(formatNumber(6, { decimals: 1 })).toBe("6.0");
  expect(formatNumber(1245092.76, { decimals: 2, compact: false })).toBe("1,245,092.76");
});

test("years have no comma", () => {
  expect(formatYear(2024)).toBe("2024");
});

test("a count standing alone is a word from one to nine and a numeral from 10", () => {
  expect(formatCount(1)).toBe("one");
  expect(formatCount(7)).toBe("seven");
  expect(formatCount(9)).toBe("nine");
  expect(formatCount(10)).toBe("10");
  expect(formatCount(14)).toBe("14");
  expect(formatCount(12500)).toBe("12,500");
});

test("dates read March 4, 2024 in sentences and Mar 4, 2024 in tables", () => {
  expect(formatDate("2024-03-04")).toBe("March 4, 2024");
  expect(formatDate("2024-03-04", { style: "table" })).toBe("Mar 4, 2024");
  expect(formatDate("2026-10-21", { style: "short", today: "2026-10-23" })).toBe("Oct 21");
  expect(formatDate("2025-12-30", { style: "short", today: "2026-10-23" })).toBe("Dec 30, 2025");
});
