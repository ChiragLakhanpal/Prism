// Ticket 35 moves this case into the export screen tests and deletes this file.
// Exports are files the person saves; a CSV must read back cell for cell in a spreadsheet or STEP.
import { expect, test } from "@playwright/test";
import { toCsv } from "../src/lib/export";

test("a row with a comma, a quote and a line break saves as CSV that reads back cell for cell", () => {
  const csv = toCsv(
    ["Activity Reference No.", "Description", "Estimated Amount (US$)", "Actual Amount (US$)"],
    [["KE-NWWDA-541055-CW-RFB", 'Works for "Lot 2", Nyeri\nand Kiganjo', 1230000, null]],
  );

  expect(csv).toBe(
    "Activity Reference No.,Description,Estimated Amount (US$),Actual Amount (US$)\r\n" +
      'KE-NWWDA-541055-CW-RFB,"Works for ""Lot 2"", Nyeri\nand Kiganjo",1230000,\r\n',
  );
});
