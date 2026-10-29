// Ticket 59: a STEP reference, a date, "page N" or a "Not checked:" label never breaks inside itself. The browser
// tells where each character of a text sits; a match whose characters sit on more than one line was broken.
import type { Page } from "@playwright/test";

// The kinds of text that stay whole, as patterns over an element's text.
export const WHOLE = {
  // A STEP reference with no spaces, such as KE-NWWDA-541055-CW-RFB. Its method is named, since the text of the element
  // after it follows with no space between.
  reference: "[A-Z]{2}-[A-Z]+-\\d{5,6}-(?:CW|GO|CS|NC)-(?:INDV|QCBS|RFB|RFQ|RFP|CQS|DIR)",
  // A date as Strata writes one in a table or a sentence: "Sep 30, 2026", "October 9, 2026" or "Nov 2022".
  date: "(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\.?\\s(?:\\d{1,2},\\s)?\\d{4}",
  page: "[Pp]age\\s\\d+",
  notChecked: "Not\\schecked:",
};

// The matches of `pattern` in the shown elements that `selector` finds whose characters sit on more than one line,
// with how many matches were found in all, so a test can tell "none broke" from "none was there".
export async function brokenInside(page: Page, selector: string, pattern: string): Promise<{ found: number; broken: string[] }> {
  return page.evaluate(
    ({ selector, pattern }) => {
      let found = 0;
      const broken: string[] = [];
      for (const element of document.querySelectorAll(selector)) {
        if (element.getClientRects().length === 0) continue;
        // Every character of the element's text, with the node and offset it sits at.
        const chars: { node: Text; at: number }[] = [];
        let text = "";
        const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
        for (let node = walker.nextNode() as Text | null; node; node = walker.nextNode() as Text | null) {
          for (let at = 0; at < node.length; at++) chars.push({ node, at });
          text += node.data;
        }
        for (const match of text.matchAll(new RegExp(pattern, "g"))) {
          found += 1;
          const tops = new Set<number>();
          for (let index = match.index!; index < match.index! + match[0].length; index++) {
            const { node, at } = chars[index];
            // A plain space may end a line and take no room there; every other character is drawn on its line.
            if (node.data[at] === " ") continue;
            const range = document.createRange();
            range.setStart(node, at);
            range.setEnd(node, at + 1);
            const rect = range.getClientRects()[0];
            if (!rect || rect.width === 0) continue;
            if (![...tops].some((top) => Math.abs(top - rect.top) < 4)) tops.add(rect.top);
          }
          if (tops.size > 1) broken.push(match[0]);
        }
      }
      return { found, broken };
    },
    { selector, pattern },
  );
}
