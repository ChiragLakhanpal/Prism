// Exports are files the person saves. Strata sends nothing itself: the server builds a draft's files and
// keeps them with the export record (src/strata/drafts/files.py, ticket 35), and this hands one to the
// browser's downloads, from Strata's own address. The evidence pack's CSV, with its quoting rules, is
// written on the server, and tests/test_draft_files.py reads it back cell for cell.

// Save a file from Strata's own server. The person's press of the button that called this is the gesture
// the browser needs, and the link's download attribute keeps it from opening in the page.
export function download(href: string, name: string): void {
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.append(link);
  link.click();
  link.remove();
}
