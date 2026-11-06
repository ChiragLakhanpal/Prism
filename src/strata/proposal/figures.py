"""The proposal's nine figures (ticket 46; the 46 brief, section 10), drawn as SVG by code.

Diagrams (1, 3, 4, 6, 7 and 8) carry no numbers: their parts are names, and the parts the change drill can change
come from their registries (the sources from config/sources.toml, the checks from the verifier). Data charts (2, 5
and 9) are drawn from the snapshot at build time, so a number in an image is always a measured one, and each has a
table twin in the proposal (the 47 brief, section 4.4: a measured chart is drawn by code, never by hand).

Colors and type are DESIGN.md section 11's strata-wb light skin (PALETTE) and section 6's chart tokens (CHART): paper
background, never transparent, Open Sans with Roboto Mono for sublabels, and no World Bank logo, which DESIGN.md
section 9 keeps for the app's bar and the deck. Each drawing is 720 px wide, so labels of 12 px or more stay at least
11 px wide when GitHub shows a figure at 880 px and the PDF at 640 px. Titles, source lines and notes are text in the
proposal, never drawn into the image.
"""

from __future__ import annotations

from collections.abc import Callable
from html import escape

# DESIGN.md section 11, the strata-wb profile, light skin.
PALETTE = {"paper": "#f5f7f9", "paper-2": "#e7edf3", "ink": "#181f25", "ink-strong": "#111111", "muted": "#4b5e71",
           "soft": "#586e84", "rule-solid": "#bdccdb", "accent": "#0071bc", "link": "#01707e"}
# DESIGN.md section 6: chart text, greys, the reference line and the categorical text variants in order.
CHART = {"text": "#111111", "textSubtle": "#666666", "grey300": "#8a969f", "grey200": "#ced4de",
         "reference": "#8a969f", "cat1": "#106ca1", "cat2": "#b65f0c", "cat3": "#664ab6"}
FONTS = ("Open Sans", "Roboto Mono")
WIDTH = 720
SANS = "'Open Sans', Arial, sans-serif"
MONO = "'Roboto Mono', monospace"


class FigureError(ValueError):
    """A figure the build cannot draw, in a sentence that names the fix."""


def _svg(height: int, body: str, label: str) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" viewBox="0 0 {WIDTH} {height}" '
            f'role="img" aria-label="{escape(label)}">\n'
            f'<rect width="{WIDTH}" height="{height}" fill="{PALETTE["paper"]}"/>\n{body}</svg>\n')


def _text(x: float, y: float, words: str, size: int = 13, weight: int = 400, fill: str = PALETTE["ink"],
          anchor: str = "start", font: str = SANS) -> str:
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{escape(words)}</text>\n')


def _box(x: float, y: float, w: float, h: float, name: str, sub: str = "", accent: bool = False) -> str:
    stroke = PALETTE["accent"] if accent else PALETTE["rule-solid"]
    out = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="6" fill="#ffffff" stroke="{stroke}" '
           f'stroke-width="1.5"/>\n')
    out += _text(x + w / 2, y + (h / 2 + 4 if not sub else h / 2 - 2), name, 13, 600, PALETTE["ink"], "middle")
    if sub:
        out += _text(x + w / 2, y + h / 2 + 14, sub, 12, 400, PALETTE["soft"], "middle", MONO)
    return out


def _arrow(x1: float, y1: float, x2: float, y2: float, dashed: bool = False, color: str = PALETTE["muted"]) -> str:
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{color}" stroke-width="1.5"{dash} '
            f'marker-end="url(#arrow)"/>\n')


DEFS = (f'<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="{PALETTE["muted"]}"/></marker></defs>\n')


def _chain(names: list[tuple[str, str]], label: str, accent: int | None = None) -> str:
    """A left-to-right flow of boxes in rows of four."""
    per_row, w, h, gap_x, gap_y = 4, 150, 56, 30, 40
    rows = (len(names) + per_row - 1) // per_row
    body = DEFS
    for index, (name, sub) in enumerate(names):
        row, col = divmod(index, per_row)
        x, y = 24 + col * (w + gap_x), 24 + row * (h + gap_y)
        body += _box(x, y, w, h, name, sub, accent == index)
        if index + 1 < len(names):
            next_row, next_col = divmod(index + 1, per_row)
            if next_row == row:
                body += _arrow(x + w, y + h / 2, x + w + gap_x - 2, y + h / 2)
            else:
                body += _arrow(x + w / 2, y + h, 24 + next_col * (w + gap_x) + w / 2, y + h + gap_y - 2)
    return _svg(48 + rows * h + (rows - 1) * gap_y, body, label)


# ── Diagrams ─────────────────────────────────────────────────────────────

def pipeline(context: dict) -> str:
    """Figure 1: the sources from the registry, the medallion, the knowledge model, the tools, the agent and the app."""
    body = DEFS
    body += (f'<rect x="24" y="16" width="{WIDTH - 48}" height="0" rx="6" fill="#ffffff" '
             f'stroke="{PALETTE["rule-solid"]}" stroke-width="1.5"/>\n')
    body += _text(36, 38, "Sources, from the source registry", 13, 600)
    lines, line = [], ""
    for name in context["sources"]:
        joined = f"{line}, {name}" if line else name
        if len(joined) > 92:
            lines.append(line + ",")
            line = name
        else:
            line = joined
    lines.append(line)
    for index, words in enumerate(lines):
        body += _text(36, 60 + index * 18, words, 12, 400, PALETTE["ink"])
    box_bottom = 60 + len(lines) * 18
    body = body.replace('height="0"', f'height="{box_bottom - 16}"', 1)
    top = box_bottom + 40
    chain = [("Bronze", "as received"), ("Silver", "typed, cleaned"), ("Gold", "knowledge model"),
             ("Passage index", "hybrid search")]
    w, h, gap = 150, 56, 30
    for index, (name, sub) in enumerate(chain):
        x = 24 + index * (w + gap)
        body += _box(x, top, w, h, name, sub)
        if index + 1 < len(chain):
            body += _arrow(x + w, top + h / 2, x + w + gap - 2, top + h / 2)
    body += _arrow(99, box_bottom, 99, top - 2)
    lower = top + h + 40
    serving = [("The app", "runs each tool"), ("Foundry agent", "picks tools"), ("Tool registry", "as the viewer"),
               ("Verifier", "every sentence")]
    for index, (name, sub) in enumerate(serving):
        x = 24 + index * (w + gap)
        body += _box(x, lower, w, h, name, sub, accent=name == "Verifier")
        if index + 1 < len(serving):
            body += _arrow(x + w, lower + h / 2, x + w + gap - 2, lower + h / 2)
    body += _arrow(24 + 2 * (w + gap) + w / 2, top + h, 24 + 2 * (w + gap) + w / 2, lower - 2)
    ops = lower + h + 30
    body += _box(24, ops, WIDTH - 48, 44, "strata.ops", "runs, measures, evaluations, cost: beside every step")
    return _svg(ops + 64, body, "Architecture: the sources in the registry flow through bronze, silver and gold into "
                "the knowledge model and the passage index; the app, the Foundry agent, the tool registry and the "
                "verifier read them, with strata.ops beside every step.")


def knowledge_model(context: dict) -> str:
    """Figure 3: records and documents meet at the passage. Solid lines share a key; dashed lines appeared together."""
    body = DEFS
    nodes = {"Project": (300, 24), "Package": (80, 120), "Notice": (80, 230), "Contract": (300, 230),
             "Supplier": (520, 230), "Document": (520, 120), "Passage": (520, 340), "Assertion": (300, 340),
             "Lesson": (80, 340)}
    subs = {"Project": "project ID", "Package": "STEP reference", "Notice": "notice ID", "Contract": "STEP reference",
            "Supplier": "STEP supplier ID", "Document": "document ID", "Passage": "paragraph and page",
            "Assertion": "dated", "Lesson": "quoted, versioned"}
    w, h = 130, 52

    def mid(name):
        x, y = nodes[name]
        return x + w / 2, y + h / 2

    def line(a, b, dashed=False):
        (x1, y1), (x2, y2) = mid(a), mid(b)
        return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{PALETTE["muted"]}" '
                f'stroke-width="1.5"{" stroke-dasharray=\"6 4\"" if dashed else ""}/>\n')

    for a, b in (("Project", "Package"), ("Project", "Document"), ("Package", "Notice"), ("Package", "Contract"),
                 ("Contract", "Supplier"), ("Document", "Passage"), ("Passage", "Assertion"), ("Passage", "Lesson")):
        body += line(a, b)
    body += line("Contract", "Passage", dashed=True)
    for name, (x, y) in nodes.items():
        body += _box(x, y, w, h, name, subs[name], accent=name == "Passage")
    return _svg(420, body, "Entity relationship diagram: project, package, notice, contract, supplier, document, "
                "passage, assertion and lesson. Solid lines join records on a shared key; a dashed line joins a "
                "contract to a passage that appeared together with it.")


def reading(context: dict) -> str:
    """Figure 4: a long report becomes numbered passages, each with its page."""
    return _chain([("A report's PDF", "documents API"), ("Page router", "per page"), ("Published text", "or layout parser"),
                   ("Numbered paragraphs", "and table rows"), ("Page kept", "with each passage"),
                   ("Embedding", context["embedding"]), ("Hybrid index", "words and vectors")],
                  "Flowchart: a report's PDF goes to the page router, then the published text or the layout parser, "
                  "then numbered paragraphs and table rows, each kept with its page, then embedding and the hybrid "
                  "index.", accent=1)


def retrieval(context: dict) -> str:
    """Figure 6: one answer, as a sequence across the person, the app, the agent, the tools and the verifier."""
    lanes = ["Person", "App", "Foundry agent", "Tools", "Verifier"]
    body = DEFS
    xs = [80 + index * 140 for index in range(len(lanes))]
    for x, name in zip(xs, lanes):
        body += _box(x - 60, 16, 120, 40, name)
        body += f'<line x1="{x}" y1="56" x2="{x}" y2="372" stroke="{PALETTE["rule-solid"]}" stroke-width="1"/>\n'
    steps = [(0, 1, "a question"), (1, 2, "the question, as the viewer"), (2, 1, "the tools to run"),
             (1, 3, "SQL through Genie, search, the graph"), (3, 1, "rows and passages, each with an id"),
             (1, 2, "the evidence pack"), (2, 1, "sentences that cite ids"), (1, 4, "every sentence"),
             (4, 1, "kept and removed"), (1, 0, "the answer and its check line")]
    for index, (a, b, words) in enumerate(steps):
        y = 82 + index * 30
        body += _arrow(xs[a], y, xs[b] + (-4 if b > a else 4), y, color=PALETTE["accent"] if b == 4 else PALETTE["muted"])
        body += _text((xs[a] + xs[b]) / 2, y - 6, words, 12, 400, PALETTE["soft"], "middle")
    return _svg(392, body, "Sequence diagram: the person asks the app; the agent picks tools; the app runs them as the "
                "person asking and builds the evidence pack; the verifier checks every sentence before the answer "
                "returns with its check line.")


def checks(context: dict) -> str:
    """Figure 7: one sentence through the verifier's checks, in its order. Removed goes to the removed box."""
    names = context["checks"]
    body = DEFS
    w, h = 104, 64
    gap = (WIDTH - 48 - len(names) * w) / max(len(names) - 1, 1)
    for index, name in enumerate(names):
        x = 24 + index * (w + gap)
        words = name.split(" ")
        half = (len(words) + 1) // 2
        body += (f'<rect x="{x:.1f}" y="40" width="{w}" height="{h}" rx="6" fill="#ffffff" '
                 f'stroke="{PALETTE["rule-solid"]}" stroke-width="1.5"/>\n')
        body += _text(x + w / 2, 66, " ".join(words[:half]), 12, 600, PALETTE["ink"], "middle")
        body += _text(x + w / 2, 82, " ".join(words[half:]), 12, 600, PALETTE["ink"], "middle")
        if index + 1 < len(names):
            body += _arrow(x + w, 72, x + w + gap - 2, 72)
        body += _arrow(x + w / 2, 40 + h, x + w / 2, 168)
    body += _text(12, 30, "kept", 12, 400, PALETTE["soft"])
    body += (f'<rect x="24" y="170" width="{WIDTH - 48}" height="44" rx="6" fill="{PALETTE["paper-2"]}" '
             f'stroke="{PALETTE["rule-solid"]}"/>\n')
    body += _text(WIDTH / 2, 197, "Removed, with its reason, shown under the answer", 13, 600, PALETTE["ink"], "middle")
    return _svg(232, body, "Flowchart: a sentence passes the verifier's checks in order: "
                + ", ".join(names) + ". A sentence that fails any check goes to the removed box with its reason.")


def loops(context: dict) -> str:
    """Figure 8: knowledge, retrieval and estimates around one dated store."""
    body = DEFS
    body += (f'<ellipse cx="360" cy="190" rx="110" ry="46" fill="{PALETTE["paper-2"]}" stroke="{PALETTE["accent"]}" '
             f'stroke-width="1.5"/>\n')
    body += _text(360, 186, "One dated store", 14, 600, PALETTE["ink"], "middle")
    body += _text(360, 204, "strata.ops", 12, 400, PALETTE["soft"], "middle", MONO)
    loops_ = [("Knowledge", "a new completion report", "a lead decides", 24, 24),
              ("Retrieval", "reports with a reason", "no loss on held-out set", 476, 24),
              ("Estimates", "signings and plan dates", "wins its backtest", 250, 290)]
    for name, trigger, gate, x, y in loops_:
        body += (f'<rect x="{x}" y="{y}" width="220" height="78" rx="6" fill="#ffffff" '
                 f'stroke="{PALETTE["rule-solid"]}" stroke-width="1.5"/>\n')
        body += _text(x + 110, y + 24, name, 14, 600, PALETTE["ink"], "middle")
        body += _text(x + 110, y + 44, f"trigger: {trigger}", 12, 400, PALETTE["soft"], "middle")
        body += _text(x + 110, y + 62, f"gate: {gate}", 12, 400, PALETTE["soft"], "middle")
        cx, cy = x + 110, y + 78 if y < 190 else y
        body += _arrow(cx, cy, 360 + (cx - 360) * 0.25, 190 + (-46 if cy < 190 else 46))
    return _svg(392, body, "Loop diagram: the knowledge, retrieval and estimates loops, each with its trigger and its "
                "gate, write to and read from one dated store, strata.ops.")


# ── Data charts ──────────────────────────────────────────────────────────

def _ticks(top: int) -> list[int]:
    """About five rounded ticks from 0 to at least top (DESIGN.md section 6)."""
    for step in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 2500, 5000, 10000, 20000, 50000):
        if top / step <= 5:
            return list(range(0, top + step if top % step else top + 1, step)) or [0, step]
    return [0, top]


def _number(value: float) -> str:
    return f"{value:,.0f}"


def award_gap(context: dict) -> str:
    """Figure 2: contract award rows per fiscal year, coloured by the dataset or the award notices they came from."""
    series = context["series"]
    groups = list(dict.fromkeys(row["dataset"] for row in series))
    colors = dict(zip(groups, (CHART["cat2"], CHART["cat3"], CHART["cat1"])))
    if len(groups) > 3:
        raise FigureError("Figure 2 draws at most three sources of award rows. Give the fourth a color from DESIGN.md "
                          "section 6's categorical text variants.")
    years = [row["fiscal_year"] for row in series]
    first, last = min(years), max(years)
    left, right, top, bottom = 64, WIDTH - 24, 56, 300
    ticks = _ticks(max(row["award_rows"] for row in series))
    scale = (bottom - top) / ticks[-1]
    slot = (right - left) / (last - first + 1)
    body = ""
    for tick in ticks:
        y = bottom - tick * scale
        body += (f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{CHART["grey200"]}" '
                 f'stroke-dasharray="4 4"/>\n') if tick else ""
        body += _text(left - 8, y + 4, _number(tick), 12, 400, CHART["textSubtle"], "end")
    body += f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{CHART["grey300"]}"/>\n'
    for row in series:
        x = left + (row["fiscal_year"] - first) * slot + slot * 0.15
        height = row["award_rows"] * scale
        body += (f'<rect x="{x:.1f}" y="{bottom - height:.1f}" width="{slot * 0.7:.1f}" height="{height:.1f}" '
                 f'fill="{colors[row["dataset"]]}"/>\n')
        if row["fiscal_year"] % 5 == 0 or row["fiscal_year"] in (first, last):
            body += _text(x + slot * 0.35, bottom + 18, f"FY{row['fiscal_year'] % 100:02d}", 12, 400,
                          CHART["textSubtle"], "middle")
    for index, group in enumerate(groups):
        body += f'<rect x="{left + index * 220}" y="16" width="12" height="12" fill="{colors[group]}"/>\n'
        body += _text(left + index * 220 + 18, 27, group, 12, 600, colors[group])
    return _svg(330, body, context["alt"])


def backtest(context: dict) -> str:
    """Figure 5: per test year, the share signed within the 8-in-10 point, one dot a year, a reference line at 8 in 10.
    A year with fewer packages than a percentage needs shows its count and no dot."""
    years = context["series"]
    left, right, top, bottom = 64, WIDTH - 24, 32, 260
    body = ""
    for tick in (0, 20, 40, 60, 80, 100):
        y = bottom - tick / 100 * (bottom - top)
        if tick:
            body += (f'<line x1="{left}" y1="{y:.1f}" x2="{right}" y2="{y:.1f}" stroke="{CHART["grey200"]}" '
                     f'stroke-dasharray="4 4"/>\n')
        body += _text(left - 8, y + 4, f"{tick}%", 12, 400, CHART["textSubtle"], "end")
    reference = bottom - 0.8 * (bottom - top)
    body += (f'<line x1="{left}" y1="{reference:.1f}" x2="{right}" y2="{reference:.1f}" stroke="{CHART["reference"]}" '
             f'stroke-width="3"/>\n')
    body += _text(right, reference - 8, "8 IN 10", 12, 600, CHART["textSubtle"], "end")
    body += f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" stroke="{CHART["grey300"]}"/>\n'
    slot = (right - left) / len(years)
    for index, year in enumerate(years):
        x = left + slot * (index + 0.5)
        body += _text(x, bottom + 20, year["label"], 12, 400, CHART["textSubtle"], "middle")
        if year.get("percent") is None:
            body += _text(x, bottom - 12, f"{year['n']} of {year['d']}", 12, 600, CHART["text"], "middle")
            continue
        y = bottom - year["percent"] / 100 * (bottom - top)
        body += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="6" fill="{CHART["cat1"]}" stroke="#ffffff" stroke-width="2"/>\n'
        body += _text(x + 10, y + 4, f"{year['percent']}%", 12, 600, CHART["cat1"])
    return _svg(290, body, context["alt"])


def hindsight(context: dict) -> str:
    """Figure 9: Prism's risk tables against the checklist, each a dot for the share caught, with Prism's interval
    as a line when there are enough blamed risks for one."""
    rows = context["rows"]
    left, right = 180, WIDTH - 40
    body = ""
    for tick in (0, 25, 50, 75, 100):
        x = left + tick / 100 * (right - left)
        body += (f'<line x1="{x:.1f}" y1="24" x2="{x:.1f}" y2="150" stroke="{CHART["grey200"]}" '
                 f'stroke-dasharray="4 4"/>\n')
        body += _text(x, 170, f"{tick}%", 12, 400, CHART["textSubtle"], "middle")
    for index, row in enumerate(rows):
        y = 56 + index * 60
        body += _text(left - 16, y + 4, row["name"], 13, 600, CHART["text"], "end")
        if row.get("low") is not None:
            x1, x2 = (left + bound / 100 * (right - left) for bound in (row["low"], row["high"]))
            body += f'<line x1="{x1:.1f}" y1="{y}" x2="{x2:.1f}" y2="{y}" stroke="{CHART["cat1"]}" stroke-width="3"/>\n'
        x = left + row["n"] / row["d"] * (right - left)
        color = CHART["cat1"] if index == 0 else CHART["cat2"]
        body += f'<circle cx="{x:.1f}" cy="{y}" r="7" fill="{color}" stroke="#ffffff" stroke-width="2"/>\n'
        body += _text(x, y - 14, f"{row['n']} of {row['d']}", 12, 600, color, "middle")
    return _svg(190, body, context["alt"])


DRAWINGS: dict[str, Callable[[dict], str]] = {
    "pipeline": pipeline, "award-gap": award_gap, "knowledge-model": knowledge_model, "reading": reading,
    "backtest": backtest, "retrieval": retrieval, "checks": checks, "loops": loops, "hindsight": hindsight,
}
DATA_CHARTS = ("award-gap", "backtest", "hindsight")
