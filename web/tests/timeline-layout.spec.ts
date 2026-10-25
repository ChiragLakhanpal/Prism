// The timeline chart's layout rules (ticket 23; the 23 brief, sections 4.4 to 4.6), checked on P130164's recorded
// timeline at the three chart widths the screen draws: 1246 px (1440 px viewport), 830 px and 524 px (beside the
// drawer at 1024 px). The page places what the payload holds; these rules decide where.
import { expect, test } from "@playwright/test";
import { axisFor, bandLabelFits, lineFor, markY, scaleFor, type DisagreementItem, type MarkItem, type Timeline } from "../src/lib/timeline";
import { recorded } from "./mocked";

const WIDTHS = [524, 830, 1246];
const CHIP = 150;

test("a disagreement's dashed line keeps clear of every mark that is not one of its two reports", async () => {
  const data: Timeline = JSON.parse(await recorded("timeline-p130164.json"));
  const marks = data.items.filter((item): item is MarkItem => item.kind !== "band" && item.kind !== "disagreement");
  const lines = data.items.filter((item): item is DisagreementItem => item.kind === "disagreement");
  expect(lines).toHaveLength(2);
  for (const width of WIDTHS) {
    const x = scaleFor(axisFor(data.items, null), width);
    for (const item of lines) {
      const line = lineFor(item, x, CHIP, [], width, []);
      const sides = new Set(item.sides.map((side) => side.item_id));
      for (const mark of marks.filter((one) => !sides.has(one.id))) {
        const centre = { x: x(mark.date), y: markY(mark.lane) };
        const nearest = Math.min(...line.points.map((point) => Math.hypot(point.x - centre.x, point.y - centre.y)));
        // A mark's white ring reaches 8 px from its centre; the line stays 4 px outside it.
        expect(nearest, `${item.id} passes ${mark.id} at ${width} px`).toBeGreaterThanOrEqual(12);
      }
    }
  }
});

test("a narrow band names its rating by its code with 4 px a side, and a longer label keeps 8 px a side", () => {
  expect(bandLabelFits("MU", 22, 36)).toBe(true);
  expect(bandLabelFits("MU", 22, 29)).toBe(false);
  expect(bandLabelFits("MU, ISRs 12–13", 90, 100)).toBe(false);
  expect(bandLabelFits("MU, ISRs 12–13", 90, 106)).toBe(true);
});
