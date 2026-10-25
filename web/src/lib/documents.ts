// The one helper that builds an "Open at page" address (the 18 and 21 briefs): the in-app source view at a
// page, with the paragraph to highlight, or the passage when it has no paragraph number. The evidence
// drawer's link and the Data readiness page's hardest documents both use it, so they land in the same
// place. :doc is the document's key in its project, such as icr-2019-10-10, or its documents API id, which
// the source view rewrites to the key.
export function sourcePageHref(pid: string, doc: string, page: number, at: { para?: string | null; passage?: string | null } = {}): string {
  const params = new URLSearchParams({ page: String(page) });
  if (at.para) params.set("para", at.para);
  else if (at.passage) params.set("passage", at.passage);
  return `/projects/${pid}/documents/${encodeURIComponent(doc)}?${params.toString()}`;
}
