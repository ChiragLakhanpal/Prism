// Exports are files the person saves. Strata sends nothing itself: this builds the file in
// the browser and hands it to the browser's download, and nothing leaves the page.

type Cell = string | number | null | undefined;

// CSV with every field quoted when it holds a comma, a quote or a line break (RFC 4180),
// and CRLF line ends, which Excel and STEP's import both read.
export function toCsv(header: string[], rows: Cell[][]): string {
  const field = (cell: Cell) => {
    const text = cell === null || cell === undefined ? "" : String(cell);
    return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
  };
  return [header, ...rows].map((row) => row.map(field).join(",")).join("\r\n") + "\r\n";
}

export function saveFile(name: string, type: string, content: BlobPart): void {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 0);
}
