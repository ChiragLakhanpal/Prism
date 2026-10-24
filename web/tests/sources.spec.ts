// The evidence card's excerpt rule (DESIGN.md section 5, Evidence card), checked on made-up paragraphs:
// the sentences the match is in, whole, then the sentence before and after while the excerpt stays within
// 280 characters. Only text whose matched sentences are longer, such as an ISR's table text, is cut
// between words, and never inside the match.
import { expect, test } from "@playwright/test";
import { excerpt } from "../src/lib/sources";

const range = (text: string, words: string): [number, number] => {
  const start = text.indexOf(words);
  expect(start).toBeGreaterThanOrEqual(0);
  return [start, start + words.length];
};

const SHORT = [
  "54. The road works started late.",
  "Land was not ready in two districts.",
  "Contracts were advertised again after the first bids came in high.",
  "The unit then used market rates.",
  "Later bids were close to the estimates.",
].join(" ");

test("a short paragraph shows the matched sentence whole, with the sentence before and after it, and no cut", () => {
  const quoted = "Contracts were advertised again after the first bids came in high.";
  const shown = excerpt(SHORT, range(SHORT, "advertised again"));

  expect(shown.text).toBe("Land was not ready in two districts. " + quoted + " The unit then used market rates.");
  expect(shown.text.slice(...shown.range!)).toBe("advertised again");
  expect([shown.cutBefore, shown.cutAfter]).toEqual([false, false]);
});

test("a paragraph's own number is left out, and with no match the excerpt starts at its first sentence", () => {
  const shown = excerpt(SHORT, null);

  expect(shown.text).toBe("The road works started late. Land was not ready in two districts.");
  expect(shown.range).toBeNull();
  expect([shown.cutBefore, shown.cutAfter]).toEqual([false, false]);
});

const LONG_SENTENCE =
  "The procurement unit found that the works contract estimates had been prepared from schedules of rates " +
  "that were several years old, so most bids came in well above them and many contracts had to be advertised " +
  "again after a long delay.";
const PROSE = `12. The road works on the state highways started late in most of the districts. ${LONG_SENTENCE} The unit then used market rates for later estimates.`;

test("a long sentence quoted whole is the excerpt by itself, highlighted end to end, when no neighbour fits beside it", () => {
  expect(LONG_SENTENCE.length).toBeGreaterThan(200);
  const shown = excerpt(PROSE, range(PROSE, LONG_SENTENCE));

  expect(shown.text).toBe(LONG_SENTENCE);
  expect(shown.range).toEqual([0, LONG_SENTENCE.length]);
  expect([shown.cutBefore, shown.cutAfter]).toEqual([false, false]);
});

// Table text as an ISR's section holds it: words and numbers with no sentence end.
const TABLE = Array.from(
  { length: 30 },
  (_, row) => `Indicator ${row + 1} Number Value ${row}.00 ${row + 2}.00 ${row + 5}.00 Date 01-Sep-2013`,
).join(" ");

test("table text with no sentence end is cut between words on both sides of the match, within 290 characters", () => {
  const words = "Indicator 15 Number Value 14.00 16.00 19.00";
  const shown = excerpt(TABLE, range(TABLE, words));

  expect(shown.text.length).toBeLessThanOrEqual(290);
  expect([shown.cutBefore, shown.cutAfter]).toEqual([true, true]);
  expect(shown.text.slice(...shown.range!)).toBe(words);
  // Each cut falls at a space, so no word or number is cut short.
  const at = TABLE.indexOf(shown.text);
  expect(TABLE[at - 1]).toBe(" ");
  expect(TABLE[at + shown.text.length]).toBe(" ");
});

test("a long match in table text stays whole and highlighted, and the excerpt still keeps within 290 characters", () => {
  const start = TABLE.indexOf("Indicator 10 ");
  const end = TABLE.indexOf(" Indicator 14 ");
  const words = TABLE.slice(start, end);
  expect(words.length).toBeGreaterThan(200);
  expect(words.length).toBeLessThanOrEqual(280);
  const shown = excerpt(TABLE, [start, end]);

  expect(shown.text.length).toBeLessThanOrEqual(290);
  expect(shown.text.slice(...shown.range!)).toBe(words);
});

test("a match longer than 280 characters is shown whole, with nothing around it", () => {
  const start = TABLE.indexOf("Indicator 10 ");
  const end = TABLE.indexOf(" Indicator 16 ");
  const words = TABLE.slice(start, end);
  expect(words.length).toBeGreaterThan(280);
  const shown = excerpt(TABLE, [start, end]);

  expect(shown.text).toBe(words);
  expect(shown.range).toEqual([0, words.length]);
  expect([shown.cutBefore, shown.cutAfter]).toEqual([true, true]);
});

test("a number with a decimal point is never taken for a sentence end", () => {
  const text = "The end target was 80.00 percent. The baseline was 67.00 percent. Data came from the survey.";
  const shown = excerpt(text, range(text, "80.00"));

  expect(shown.text).toBe("The end target was 80.00 percent. The baseline was 67.00 percent.");
});
