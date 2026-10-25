// A project's Connections tab (ticket 22; the 22 brief, section 3), at /projects/:pid/connections: the project's
// one-hop neighbourhood, at most connections.max_nodes nodes with the project, as two columns joined by lines
// (DESIGN.md section 5, One-hop neighbourhood). The project node sits on top; the packages its plans hold are in
// the left column and the documents about it in the right. A dashed line joins a package to each paragraph chip
// on a document whose paragraph appeared together with one of the package's contracts. Solid lines join the
// project to the two columns. Line weight never shows a score: every link looks the same.
//
// The tool chooses, orders and counts the nodes (GET /api/projects/:pid/connections); the browser only draws. The
// diagram is two lists of links with an SVG drawn over them and hidden from screen readers, so it is a list by
// construction: below a 768 px page area it stops drawing lines and becomes the list, and from 768 px a "Show as
// a list" toggle swaps views, remembered for this browser tab. Each node and each chip is its own tab stop: they
// are links to pages, not marks of data. Hovering or focusing a node or a chip turns its lines primary and tints
// the nodes at their other ends. The lines are redrawn when the diagram's size changes, after the fonts load, and
// when the drawer opens or closes.
import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "../../components/Button";
import { EmptyState } from "../../components/Card";
import { Fill } from "../../components/Fill";
import { LoadError } from "../../components/LoadError";
import { Num } from "../../components/Num";
import { ProjectId } from "../../components/ProjectId";
import { Skeleton, SkeletonLine, SkeletonText } from "../../components/Skeleton";
import { Source } from "../../components/Source";
import { TextLink } from "../../components/TextLink";
import { copy } from "../../copy";
import { cx } from "../../lib/cx";
import { evidenceHref, evidenceIn, openEvidence, visited } from "../../lib/evidence";
import { formatCount, formatDate } from "../../lib/format";
import { useLoad } from "../../lib/load";
import { address } from "../../lib/router";
import { useStore } from "../../lib/store";
import type { Chip, DocumentNode, Neighbourhood, PackageNode } from "../../lib/trail";
import { withReadParams } from "../../lib/view";
import { dataReadinessHref, fill } from "../../routes";

const words = copy.connections;
const table = (iso: string | null) => (iso ? formatDate(iso, { style: "table" }) : "");
const LIST_KEY = "strata.connections.view";

function storedList(): boolean {
  try {
    return window.sessionStorage.getItem(LIST_KEY) === "list";
  } catch {
    return false;
  }
}

function storeList(list: boolean) {
  try {
    window.sessionStorage.setItem(LIST_KEY, list ? "list" : "diagram");
  } catch {
    // The choice lasts for this page only.
  }
}

// A document's short title: "PAD", "ISR 7", "ICR", "ICR Review", "Procurement Plan".
function docShort(node: DocumentNode): string {
  if (node.type === "isr" && node.sequence) return words.docShort.isr(String(node.sequence));
  if (node.type === "procurement_plan") return words.planShort;
  return node.short_name ?? node.document_type;
}

function chipLabel(chip: Chip): string {
  return chip.paragraph_numbered ? fill(words.chip, { para: chip.paragraph }) : fill(words.chipSection, { section: chip.section_path });
}

// A chip with its document's short name, as the list and the tooltips write it: "ICR ¶54", or "ISR 7, Results".
function chipWithDoc(doc: string, item: { paragraph: string; paragraph_numbered: boolean; section_path: string }): string {
  return item.paragraph_numbered
    ? fill(words.chipWithDoc, { doc, para: item.paragraph })
    : fill(words.chipWithDocSection, { doc, section: item.section_path });
}

// Where a chip's paragraph sits, as its name says it: "paragraph 54", or "section Results".
function chipPlace(chip: Chip): string {
  return chip.paragraph_numbered ? words.placeParagraph(chip.paragraph) : words.placeSection(chip.section_path);
}

type Hot = { kind: "package"; key: string } | { kind: "chip"; key: string } | null;

function isLinked(hot: Hot, edge: { step_reference: string; evidence_id: string }): boolean {
  return Boolean(hot && ((hot.kind === "package" && hot.key === edge.step_reference) || (hot.kind === "chip" && hot.key === edge.evidence_id)));
}

function ChipLink({ chip, doc, hot, setHot, withDoc = false }: { chip: Chip; doc: string; hot: Hot; setHot: (hot: Hot) => void; withDoc?: boolean }) {
  const opened = useStore(visited).has(chip.evidence_id);
  const active = evidenceIn(useStore(address).search) === chip.evidence_id;
  const lit = hot?.kind === "package" && chip.packages.includes(hot.key);
  const name =
    chip.packages.length === 1 ? words.chipName(doc, chipPlace(chip), chip.packages[0]) : words.chipNameMany(doc, chipPlace(chip), formatCount(chip.packages.length));
  return (
    <a
      href={evidenceHref(chip.evidence_id)}
      data-chip={chip.evidence_id}
      data-focus-ring
      onClick={(event) => {
        if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey || event.button !== 0) return;
        event.preventDefault();
        openEvidence(chip.evidence_id, { serial: null, sentence: null, marker: event.currentTarget, runId: null });
      }}
      onMouseEnter={() => setHot({ kind: "chip", key: chip.evidence_id })}
      onMouseLeave={() => setHot(null)}
      onFocus={() => setHot({ kind: "chip", key: chip.evidence_id })}
      onBlur={() => setHot(null)}
      className={cx(
        "relative z-10 inline-flex h-8 items-center rounded-pill border px-3 text-small tabular-nums no-underline transition-paint duration-150 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus",
        active
          ? "border-line-strong bg-tint text-ink shadow-[inset_0_0_0_1px_var(--color-primary)]"
          : opened
            ? "border-line-strong bg-surface-2 text-ink-muted hover:bg-tint-hover"
            : lit
              ? "border-line-strong bg-tint text-ink"
              : "border-line-strong bg-surface text-ink hover:bg-tint-hover",
      )}
    >
      {/* The chip shows "¶54"; a screen reader hears its whole name, "ICR paragraph 54, appeared together with ...". */}
      <span aria-hidden="true">
        {withDoc ? chipWithDoc(doc, chip) : chipLabel(chip)}
      </span>
      <span className="clip-visually">{opened ? words.chipOpened(name) : name}</span>
    </a>
  );
}

function statusLine(node: PackageNode): ReactNode {
  if (node.contracts > 1 && node.first_signed_on)
    return <Fill template={words.pkgSignedMany(formatCount(node.contracts))} slots={{ date: table(node.first_signed_on) }} />;
  if (node.first_signed_on) return <Fill template={words.pkgSigned} slots={{ date: table(node.first_signed_on) }} />;
  return node.process_status ?? "";
}

function statusText(node: PackageNode): string {
  if (node.contracts > 1 && node.first_signed_on) return fill(words.pkgSignedMany(formatCount(node.contracts)), { date: table(node.first_signed_on) });
  if (node.first_signed_on) return fill(words.pkgSigned, { date: table(node.first_signed_on) });
  return node.process_status ?? "";
}

function PackageCard({ node, data, hot, setHot, list }: { node: PackageNode; data: Neighbourhood; hot: Hot; setHot: (hot: Hot) => void; list: boolean }) {
  const chips = data.documents.flatMap((doc) => doc.chips.filter((chip) => chip.packages.includes(node.step_reference)).map((chip) => ({ chip, doc })));
  const lit = hot?.kind === "chip" && chips.some(({ chip }) => chip.evidence_id === hot.key);
  const describe = `pkg-links-${node.step_reference}`;
  const items = chips.map(({ chip, doc }) => chipWithDoc(docShort(doc), chip));
  return (
    <li data-node="package" data-focus-ring data-package={node.step_reference} className={cx("relative min-h-11 rounded-md border border-line p-3 transition-paint duration-150 has-[a[data-node-link]:focus-visible]:outline-2 has-[a[data-node-link]:focus-visible]:outline-offset-2 has-[a[data-node-link]:focus-visible]:outline-focus has-[a[data-node-link]:hover]:bg-tint-hover", lit ? "bg-tint" : "bg-surface")}>
      <a
        href={node.href}
        data-node-link
        aria-label={words.pkgName(node.step_reference, node.description ?? "", statusText(node))}
        aria-describedby={chips.length ? describe : undefined}
        onMouseEnter={() => setHot({ kind: "package", key: node.step_reference })}
        onMouseLeave={() => setHot(null)}
        onFocus={() => setHot({ kind: "package", key: node.step_reference })}
        onBlur={() => setHot(null)}
        className="inline-flex min-h-6 items-center text-small font-mono font-medium wrap-anywhere text-primary underline outline-none after:absolute after:inset-0 after:content-['']"
      >
        {node.step_reference}
      </a>
      {node.description && <p className="mt-1 line-clamp-2 text-small text-ink">{node.description}</p>}
      <p className="mt-1 text-caption text-ink-muted">{statusLine(node)}</p>
      {chips.length > 0 && (
        <span id={describe} className="clip-visually">
          {words.pkgLinks(items.join(copy.list.comma))}
        </span>
      )}
      {chips.length > 0 && (
        <div className={cx("mt-2", list ? "block" : "block @md/page:hidden")}>
          <p className="text-caption text-ink-muted">{words.together}</p>
          <p className="mt-1 flex flex-wrap gap-2">
            {chips.map(({ chip, doc }) => (
              <ChipLink key={chip.evidence_id} chip={chip} doc={docShort(doc)} hot={hot} setHot={setHot} withDoc />
            ))}
          </p>
        </div>
      )}
    </li>
  );
}

function DocumentCard({ node, pid, hot, setHot, list }: { node: DocumentNode; pid: string; hot: Hot; setHot: (hot: Hot) => void; list: boolean }) {
  const short = docShort(node);
  const full = node.document_type;
  const date = table(node.document_date);
  const lit = hot?.kind === "package" && node.chips.some((chip) => chip.packages.includes(hot.key));
  const packages = [...new Set(node.chips.flatMap((chip) => chip.packages))];
  return (
    <li data-node="document" data-focus-ring data-document={node.document_id} className={cx("relative min-h-11 rounded-md border border-line p-3 transition-paint duration-150 has-[a[data-node-link]:focus-visible]:outline-2 has-[a[data-node-link]:focus-visible]:outline-offset-2 has-[a[data-node-link]:focus-visible]:outline-focus has-[a[data-node-link]:hover]:bg-tint-hover", lit ? "bg-tint" : "bg-surface")}>
      <a
        href={node.href}
        data-node-link
        aria-label={words.docName(short, full, date)}
        className="inline-flex min-h-6 min-w-6 items-center text-small font-bold text-ink-heading underline outline-none after:absolute after:inset-0 after:content-['']"
      >
        {short}
      </a>
      <p className="mt-1 text-caption text-ink-muted">{short === full ? date : <Fill template={words.docCaption} slots={{ type: full, date }} />}</p>
      {node.chips.length > 0 && (
        <div className={cx("mt-2", list ? "hidden" : "hidden @md/page:block")}>
          <p className="flex flex-wrap gap-2">
            {node.chips.map((chip) => (
              <ChipLink key={chip.evidence_id} chip={chip} doc={short} hot={hot} setHot={setHot} />
            ))}
          </p>
          {node.more_chips > 0 && <p className="mt-1 text-caption text-ink-muted">{words.moreChips(node.more_chips, formatCount(node.more_chips))}</p>}
        </div>
      )}
      {packages.length > 0 && (
        <div className={cx("mt-2", list ? "block" : "block @md/page:hidden")}>
          <p className="text-caption text-ink-muted">{words.together}</p>
          <ul className="mt-1 flex flex-col gap-1">
            {packages.map((ref) => (
              <li key={ref} className="relative z-10 text-small">
                <TextLink href={`/projects/${pid}/packages/${encodeURIComponent(ref)}`} data-focus-ring className="inline-flex min-h-6 items-center font-mono font-medium wrap-anywhere">
                  {ref}
                </TextLink>{" "}
                <span className="text-caption text-ink-muted">
                  {node.chips.filter((chip) => chip.packages.includes(ref)).map(chipLabel).join(copy.list.comma)}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </li>
  );
}

type Path = { d: string; kind: "project" | "together"; lit: boolean };

export function NeighbourhoodDiagram({ data, list }: { data: Neighbourhood; list: boolean }) {
  const frame = useRef<HTMLDivElement>(null);
  const [hot, setHot] = useState<Hot>(null);
  const [paths, setPaths] = useState<Path[]>([]);
  const search = useStore(address).search;

  const draw = useCallback(() => {
    const root = frame.current;
    if (!root || list) return setPaths([]);
    const box = root.getBoundingClientRect();
    if (box.width === 0) return setPaths([]);
    const at = (element: Element | null) => {
      if (!element) return null;
      const rect = element.getBoundingClientRect();
      if (rect.width === 0) return null;
      return { left: rect.left - box.left, right: rect.right - box.left, top: rect.top - box.top, bottom: rect.bottom - box.top, mid: rect.top - box.top + rect.height / 2, center: rect.left - box.left + rect.width / 2 };
    };
    const found: Path[] = [];
    const project = at(root.querySelector("[data-node=project]"));
    for (const heading of root.querySelectorAll("[data-column-heading]")) {
      const end = at(heading);
      if (project && end) found.push({ d: `M ${project.center} ${project.bottom} C ${project.center} ${end.top - 12}, ${end.center} ${project.bottom + 12}, ${end.center} ${end.top}`, kind: "project", lit: false });
    }
    for (const edge of data.edges) {
      const from = at(root.querySelector(`[data-package="${CSS.escape(edge.step_reference)}"]`));
      const to = at(root.querySelector(`[data-node=document] [data-chip="${CSS.escape(edge.evidence_id)}"]`));
      if (!from || !to) continue;
      const bend = Math.max(24, (to.left - from.right) / 2);
      found.push({ d: `M ${from.right} ${from.mid} C ${from.right + bend} ${from.mid}, ${to.left - bend} ${to.mid}, ${to.left} ${to.mid}`, kind: "together", lit: isLinked(hot, edge) });
    }
    setPaths(found);
  }, [data, list, hot]);

  useLayoutEffect(() => {
    draw();
  }, [draw, search]);
  useEffect(() => {
    const root = frame.current;
    if (!root) return;
    const observer = new ResizeObserver(() => draw());
    observer.observe(root);
    void document.fonts?.ready.then(() => draw());
    return () => observer.disconnect();
  }, [draw]);

  const twoColumns = list ? "flex flex-col gap-6" : "flex flex-col gap-6 @md/page:grid @md/page:grid-cols-12 @md/page:gap-x-6";
  return (
    <section data-diagram={list ? "list" : "diagram"} aria-labelledby="connections-finding" className="relative" ref={frame}>
      <div className={cx(list ? "" : "@md/page:flex @md/page:justify-center")}>
        <div data-node="project" className={cx("relative rounded-md border-2 border-primary bg-surface p-3", list ? "" : "@md/page:w-1/3")}>
          <p className="text-small">
            <ProjectId pid={data.project.project_id} />
          </p>
          <TextLink
            href={`/projects/${data.project.project_id}`}
            aria-label={words.projectName(data.project.display_name ?? data.project.project_id, data.project.project_id)}
            className="mt-1 line-clamp-2 text-small font-semibold"
          >
            {data.project.display_name ?? data.project.project_id}
          </TextLink>
        </div>
      </div>
      <div className={cx("mt-6", twoColumns)}>
        <div className={cx(list ? "" : "@md/page:col-span-5 @lg/page:col-span-4")}>
          <h3 data-column-heading="packages" id="col-packages" className="text-small font-bold text-ink-heading">{words.col.packages}</h3>
          <ul aria-labelledby="col-packages" className="mt-3 flex flex-col gap-3">
            {data.packages.map((node) => (
              <PackageCard key={node.step_reference} node={node} data={data} hot={hot} setHot={setHot} list={list} />
            ))}
          </ul>
          <MoreRows data={data} side="packages" />
        </div>
        <div className={cx(list ? "" : "@md/page:col-span-5 @md/page:col-start-8 @lg/page:col-span-4 @lg/page:col-start-9")}>
          <h3 data-column-heading="documents" id="col-documents" className="text-small font-bold text-ink-heading">{words.col.documents}</h3>
          <ul aria-labelledby="col-documents" className="mt-3 flex flex-col gap-3">
            {data.documents.map((node) => (
              <DocumentCard key={node.document_id} node={node} pid={data.project.project_id} hot={hot} setHot={setHot} list={list} />
            ))}
          </ul>
          <MoreRows data={data} side="documents" />
        </div>
      </div>
      <svg aria-hidden="true" className={cx("pointer-events-none absolute inset-0 size-full overflow-visible", list ? "hidden" : "hidden @md/page:block")}>
        {paths.map((path, index) => (
          <path
            key={index}
            d={path.d}
            fill="none"
            className={cx("transition-paint duration-150", path.lit ? "stroke-primary" : "stroke-line-strong")}
            strokeWidth={path.kind === "project" ? 2 : path.lit ? 2 : 1.5}
            strokeDasharray={path.kind === "together" ? "4 4" : undefined}
          />
        ))}
      </svg>
    </section>
  );
}

function MoreRows({ data, side }: { data: Neighbourhood; side: "packages" | "documents" }) {
  const rows = data.more.filter((row) => (side === "packages") === (row.kind === "packages"));
  if (!rows.length) return null;
  const pid = data.project.project_id;
  return (
    <ul className="mt-3 flex flex-col gap-1">
      {rows.map((row) => (
        <li key={row.kind} className="text-small text-ink-muted">
          <TextLink href={row.kind === "packages" ? `/projects/${pid}/procurement` : `/projects/${pid}/documents`} className="inline-flex min-h-6 items-center">
            {words.more[row.kind](row.count, formatCount(row.count))}
          </TextLink>
        </li>
      ))}
    </ul>
  );
}

function Finding({ data }: { data: Neighbourhood }) {
  const f = data.finding;
  if (f.contracts === 0) return <>{words.findingNone}</>;
  const lines = (items: string[]) => (
    <ul className="flex flex-col gap-1">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
  const template = f.documents === 1 ? words.findingOneReport(f.contracts, f.paragraphs) : words.finding(f.contracts, f.paragraphs, f.documents);
  return (
    <Fill
      template={template}
      slots={{
        contracts: <Num count={f.contracts} check={{ tooltip: lines(f.contract_items) }} />,
        paragraphs: (
          <Num
            count={f.paragraphs}
            check={{ tooltip: lines(f.paragraph_items.map((item) => chipWithDoc(item.short_name ?? item.document_type, item))) }}
          />
        ),
        documents: <Num count={f.documents} check={{ tooltip: lines(f.document_items.map((item) => item.short_name ?? item.document_type)) }} />,
      }}
    />
  );
}

function ConnectionsSkeleton() {
  return (
    <div aria-hidden="true">
      <SkeletonText className="text-title" widths={["w-full max-w-[640px]", "w-3/5"]} />
      <SkeletonText className="mt-2 text-body" widths={["w-full max-w-[640px]", "w-2/5"]} />
      <SkeletonLine className="mt-4 text-caption" width="w-60" />
      <div className="mt-4 @md/page:flex @md/page:justify-center">
        <Skeleton className="h-16 w-full @md/page:w-1/3" radius="rounded-md" />
      </div>
      <div className="mt-6 flex flex-col gap-6 @md/page:grid @md/page:grid-cols-12 @md/page:gap-x-6">
        {["packages", "documents"].map((column) => (
          <div key={column} className={column === "packages" ? "@md/page:col-span-4" : "@md/page:col-span-4 @md/page:col-start-9"}>
            <div className="flex flex-col gap-3">
              {[0, 1, 2, 3, 4, 5].map((row) => (
                <Skeleton key={row} className="h-26 w-full" radius="rounded-md" />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ConnectionsTab({ pid }: { pid: string }) {
  const search = useStore(address).search;
  const [load, retry] = useLoad<Neighbourhood>(withReadParams(`/api/projects/${encodeURIComponent(pid)}/connections`, search));
  const [list, setList] = useState(storedList);
  const [said, setSaid] = useState("");
  const data = load.status === "ready" ? load.data : null;
  const empty = data && data.packages.length === 0 && data.documents.length === 0;
  const linked = data ? data.finding.contracts > 0 : false;
  const toggle = () => {
    const next = !list;
    setList(next);
    storeList(next);
    setSaid(next ? words.showingList : words.showingDiagram);
  };
  return (
    <div className="layout-grid" data-connections={load.status}>
      <div className="col-span-12">
        {load.status === "error" ? (
          <div className="@lg/page:w-2/3">
            <LoadError error={load.error} message={words.error} permission={words.permission} onRetry={retry} retrying={load.retrying} attempt={load.attempt} />
          </div>
        ) : !data ? (
          <ConnectionsSkeleton />
        ) : empty ? (
          <EmptyState
            className="@lg/page:w-2/3"
            title={<Fill template={words.emptyTitle} slots={{ pid: <span className="font-mono">{pid}</span> }} />}
            body={words.emptyBody}
            link={{ href: "/data", text: words.emptyLink }}
          />
        ) : (
          <>
            <div className="@lg/page:w-2/3">
              <h2 id="connections-finding" className="text-title text-ink-heading">
                <Finding data={data} />
              </h2>
              <p className="mt-2 max-w-prose text-body text-ink">{linked ? words.legend : words.legendNone}</p>
              {!linked && (
                <p className="mt-2 max-w-prose text-body text-ink">
                  <Fill template={words.noneDetail} slots={{ threshold: data.threshold }} />{" "}
                  <TextLink href={dataReadinessHref([data.coverage.source_key], "connections")}>
                    <Fill template={words.coverage} slots={{ read: String(data.coverage.read), total: String(data.coverage.total) }} />
                  </TextLink>
                </p>
              )}
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <p className="text-caption text-ink-muted">
                <Fill template={words.count} slots={{ shown: String(data.shown), total: String(data.total) }} />
              </p>
              {/* Offered only where the diagram can show: below a 768 px page area it is always the list. */}
              <span className="hidden @md/page:block">
                <Button variant="ghost" aria-pressed={list} onClick={toggle}>
                  {list ? words.toDiagram : words.toList}
                </Button>
              </span>
            </div>
            <div className="mt-4">
              <NeighbourhoodDiagram data={data} list={list} />
            </div>
            <Source className="mt-6">
              <Fill
                template={data.scored_date ? words.source : words.sourceUnscored}
                slots={{ data_through: formatDate(data.data_through ?? data.as_of), scored_date: data.scored_date ? formatDate(data.scored_date) : "" }}
              />
            </Source>
          </>
        )}
        <p role="status" className="sr-only">
          {load.status === "loading" ? (load.slow ? words.stillLoading : words.loading) : said}
        </p>
      </div>
    </div>
  );
}
