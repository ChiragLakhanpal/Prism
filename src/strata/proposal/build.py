"""The proposal's build (ticket 46; the 46 brief, sections 3, 9, 15 and 20).

build() takes docs/proposal/source.md, the measures snapshot and the registries, and returns docs/proposal.md with
its figures. In the source:

- {r:key} is a measured result (docs/proposal/results.toml), and {r:key|field} one of its other values, such as
  {r:azure-spend|budget}. It becomes a link to the result's row in Annex 1, with a title that says what it counts and
  when it was measured. {r:key|against} follows a money result with brief 45's words for where it stands against its
  budget: " of the US$B budget", or ". That is US$O more than the US$B budget" once the query's over column is above 0.
- {s:key} is a setting or a count (docs/proposal/settings.toml), and {s:key|cap} the same with a capital, for the
  start of a sentence. It becomes a link to its row in Annex 2.
- {#slug} at the start of a paragraph names it, and {#slug} at the end of a heading names its section.
  {p:slug} becomes "paragraph N", {¶:slug} "¶N" and {sec:slug} the section's "¶N–M", each a link.
- {fig:slug} becomes "Figure N", a link. A block that starts with {figure:slug} is the figure: its title line, which
  says "Figure." for the build to number, the image, its source line and any note, and for a data chart its table.
- {when:designed} at the start of a paragraph keeps it only while something is designed but not built.
- {when:measured:key} at the start of a line, or after its {#slug}, keeps the line only while result key has a
  measured value, and {when:unmeasured:key} only while it has none, so a state such as "No cost data yet" has
  its own words instead of stopping the build.
- A block that is only {datasheet}, {rubric-map}, {framework}, {caps}, {drill}, {ladder}, {designed} or {annex:...}
  is replaced by the table that registry gives; {copy:key} is the app's own words (src/strata/proposal/copy.json).
- {model:role} is the deployment config/models.toml names for that role, in code, so swapping a model changes the
  next build (docs/PLAN.md section 15).

Paragraphs are numbered from the Summary to the end of "Designed, not built", as in a World Bank project document.
Titles (a block in bold), source and note lines, "Scored under" and "What you can open" lines, tables, lists and
figures have no number. The build stops with a plain sentence (BuildError) when a placeholder has no value, a link
has no target, a figure has no drawing, a URL is not set, or the finished text fails the number check.
"""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass, field
from html import escape
from pathlib import Path

from strata import config
from strata.dashboard import wording
from strata.proposal import figures as drawings
from strata.proposal import numbers
from strata.proposal.register import (DAY_ONE_FILE, MONTHS, REHEARSAL_KIND, Rehearsal, Result, Setting, Value,
                                     load_rehearsals, load_results, load_settings, value)

ROOT = Path(__file__).resolve().parents[3]
SOURCE_FILE = ROOT / "docs" / "proposal" / "source.md"
COPY_FILE = Path(__file__).with_name("copy.json")
WORDS = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine")
NUMBERED_FROM, NUMBERED_TO = "Summary", "Annex 1: Results register"
UNNUMBERED = ("#", "|", "<", "!", "- ", "* ", ">", "{figure:", "**Source:**", "**Note:**", "**What you can open.**",
              "Scored under")
PLACEHOLDER = re.compile(r"\{(r|s|p|¶|sec|fig|copy|url|model):([^{}]+)\}")
SLUG = re.compile(r"^\{#([a-z0-9-]+)\}\s*")
HEADING_SLUG = re.compile(r"\s*\{#([a-z0-9-]+)\}\s*$")
WHEN_MEASURED = re.compile(r"^(\{#[a-z0-9-]+\} )?\{when:(measured|unmeasured):([a-z0-9-]+)\} ")
TIERS = {"ieg": "IEG's ICR Review or PPAR", "icr": "the ICR", "isr": "the ISRs", "pad": "the PAD",
         "record": "a record made at that moment, such as a contract, a notice or a plan row"}
TIES = {"tieSpecific": "the more specific source", "tieRecent": "the more recent source"}
CHECK_NAMES = {1: "Numbers and dates match", 2: "Every source came back", 3: "Quotes are on the page",
               4: "It follows from its sources", 5: "Advice cites evidence", 6: "Both sides shown"}
WAITS_FOR_PILOT = ("weekly_users", "drafts_exported", "plan_rows_offered", "plan_accuracy")
WHERE_IT_STANDS = ("Met", "Not met", "No target", "Not measured yet", "Waits for the pilot")


class BuildError(Exception):
    """The proposal did not build, with the sentence that says why and what to do."""


# ── Words for numbers and dates ──────────────────────────────────────────

def _day(iso: str | None) -> dt.date | None:
    return dt.date.fromisoformat(str(iso)[:10]) if iso else None


def long_date(day: dt.date) -> str:
    return f"{MONTHS[day.month - 1]} {day.day}, {day.year}"


def short_date(day: dt.date) -> str:
    return f"{MONTHS[day.month - 1][:3]} {day.day}, {day.year}"


def numeral(number) -> str:
    if isinstance(number, float) and not number.is_integer():
        return f"{number:,}"
    return f"{int(number):,}"


def _money(amount) -> str:
    """US dollars as the dashboard's sentences write them: two decimals, half up, with commas."""
    return f"US${wording.money(amount)}"


def word(number) -> str:
    """One to nine in words (DESIGN.md section 7, rule 12), numerals from 10."""
    return WORDS[int(number)] if isinstance(number, int) and 0 < number < 10 else numeral(number)


def _title(text: str) -> str:
    return text.replace('"', "'")


# ── The parts the build reads ────────────────────────────────────────────

@dataclass
class Inputs:
    """Everything a build reads, so a test can give it a snapshot and registries of its own."""

    snapshot: dict
    commit: str
    results: dict[str, Result] = field(default_factory=load_results)
    settings: dict[str, Setting] = field(default_factory=load_settings)
    urls: config.Urls = field(default_factory=config.load_urls)
    rubric: config.Rubric = field(default_factory=config.load_rubric)
    designed: tuple[config.DesignedNotBuilt, ...] = field(default_factory=config.load_designed_not_built)
    drills: tuple[config.ChangeDrill, ...] = field(default_factory=config.load_change_drills)
    rehearsals: dict[str, Rehearsal] = field(default_factory=load_rehearsals)
    models: dict = field(default_factory=config.load_models)
    day_one: Path = DAY_ONE_FILE
    copy: dict = field(default_factory=lambda: json.loads(COPY_FILE.read_text()))


@dataclass
class Built:
    markdown: str
    figures: dict[str, str]


@dataclass
class _Block:
    text: str
    section: str  # the current h2's slug or name
    subsection: str | None
    number: int | None = None
    slug: str | None = None


class _Build:
    def __init__(self, inputs: Inputs):
        self.inputs = inputs
        self.results = inputs.snapshot["results"]
        self.cited_results: dict[str, list[tuple[str, str]]] = {}
        self.cited_settings: dict[str, list[tuple[str, str]]] = {}
        self.cited_drills: list[tuple[Rehearsal, tuple[str, str]]] = []
        self.values: dict[str, Value] = {}
        self.paragraphs: dict[str, int] = {}
        self.sections: dict[str, list[int]] = {}
        self.figure_numbers: dict[str, int] = {}
        self.headings: dict[str, str] = {}
        self.figures: dict[str, str] = {}
        self.where = ("the front matter", "#")

    # ── Values ──

    def result(self, key: str) -> tuple[Result, dict]:
        if key not in self.inputs.results:
            raise BuildError(f"The proposal did not build. {self.where[0]} cites the result {key}, which is not in "
                             "docs/proposal/results.toml.")
        defined, measured = self.inputs.results[key], self.results.get(key, {"measured": False})
        if not measured.get("measured"):
            raise BuildError(f"The proposal did not build. Result {key} has no measured value. Measure it with "
                             f"{defined.query_file}, or remove the sentence that cites it in {self.where[0]}.")
        self.cited_results.setdefault(key, [])
        if self.where not in self.cited_results[key]:
            self.cited_results[key].append(self.where)
        return defined, measured

    def result_title(self, defined: Result, measured: dict) -> str:
        day = short_date(_day(measured["measured_on"]))
        if defined.form == "ratio":
            counted = f"{numeral(measured['n'])} of {numeral(measured['d'])} {defined.noun}"
        elif defined.form in ("count", "days"):
            counted = f"{numeral(measured.get(defined.count_of) or 0)} {defined.noun}"
        else:
            counted = defined.name
        return _title(f"{counted}. {defined.kind}, measured {day}.")

    def result_text(self, defined: Result, measured: dict, part: str | None) -> str:
        if part == "on":
            return long_date(_day(measured["measured_on"]))
        if part:
            found = measured.get(part)
            if found is None:
                raise BuildError(f"The proposal did not build. Result {defined.key} has no {part}. Measure it with "
                                 f"{defined.query_file}, or remove the sentence that cites it in {self.where[0]}.")
            if part == "measured_on":
                return short_date(_day(found))
            if part in ("latest", "month") and re.fullmatch(r"\d{4}-\d{2}-\d{2}.*", str(found)):
                return long_date(_day(found))
            if part in ("budget", "d", "over") and defined.form == "money":
                return _money(found)
            return numeral(found) if isinstance(found, int | float) else str(found)
        form = defined.form
        if form == "ratio":
            return f"{numeral(measured['n'])} of {numeral(measured['d'])}"
        if form == "count":
            return word(measured[defined.count_of])
        if form == "money":
            return _money(measured["n"])
        if form == "score":
            return f"{measured['value']:.2f}"
        if form == "days":
            return f"{numeral(measured['n'])} days"
        if form == "rate":
            return f"{measured['value']:.1f}"
        if form == "interval":
            return f"{measured['low']} to {measured['high']} percent"
        if form == "text":
            return measured["text"]
        if form == "fact":
            return ", ".join(f"{name} {found}" for name, found in measured.items()
                             if name not in ("measured", "run_id", "measured_on", "document_id"))
        raise BuildError(f"The proposal did not build. Result {defined.key} is a {form}, which a sentence can't cite. "
                         "Cite it in its figure.")

    def against(self, key: str) -> str:
        """Where a money result stands against its budget, in the dashboard's two spend sentences (brief 45)."""
        defined, measured = self.result(key)
        if defined.form != "money" or measured.get("budget") is None:
            raise BuildError(f"The proposal did not build. {self.where[0]} says where result {key} stands against a "
                             "budget, but it is not money with a budget column.")
        if (measured.get("over") or 0) > 0:
            return f". That is {self.result_link(key, 'over')} more than the {self.result_link(key, 'budget')} budget"
        return f" of the {self.result_link(key, 'budget')} budget"

    def result_link(self, key: str, part: str | None = None, text: str | None = None) -> str:
        defined, measured = self.result(key)
        shown = text if text is not None else self.result_text(defined, measured, part)
        return f'[{shown}](#r-{key} "{self.result_title(defined, measured)}")'

    def setting(self, key: str) -> tuple[Setting, Value]:
        if key not in self.inputs.settings:
            raise BuildError(f"The proposal did not build. {self.where[0]} cites the setting {key}, which is not in "
                             "docs/proposal/settings.toml.")
        if key not in self.values:
            self.values[key] = value(self.inputs.settings[key], self.inputs.day_one)
        self.cited_settings.setdefault(key, [])
        if self.where not in self.cited_settings[key]:
            self.cited_settings[key].append(self.where)
        return self.inputs.settings[key], self.values[key]

    def setting_text(self, setting: Setting, found: Value) -> str:
        number = found.number
        if setting.form == "word":
            return word(number)
        if setting.form == "percent_band":
            return f"{round(number * 100)} to {round(found.second * 100)} percent"
        if setting.form == "money":
            return f"US${numeral(number)}"
        if setting.form == "tokens":
            unit = "enqueued tokens" if setting.read == "cap:batch" else "tokens per minute"
            return f"{numeral(number)} {unit}"
        if setting.form == "gigabytes":
            return f"{number} GB a day"
        return numeral(number)

    def setting_link(self, key: str, capital: bool = False, cite: bool = True) -> str:
        """The setting as a link to its row in Annex 2. cite=False links without counting the place as citing it,
        for an annex row that repeats a value its section already cited."""
        if cite:
            setting, found = self.setting(key)
        else:
            setting = self.inputs.settings[key]
            found = self.values.get(key) or value(setting, self.inputs.day_one)
        text = self.setting_text(setting, found)
        if capital:
            text = text[:1].upper() + text[1:]
        title = _title(f"{setting.name}. Set in {setting.where.split(',')[0]}.")
        return f'[{text}](#s-{key} "{title}")'

    # ── References ──

    def paragraph_ref(self, slug: str, form: str) -> str:
        if form == "sec":
            numbers_ = self.sections.get(slug)
            if not numbers_ and slug in self.headings:  # an annex: its paragraphs have no numbers
                return f"[{self.headings[slug].split(':')[0]}](#sec-{slug})"
            if not numbers_:
                raise BuildError(f"{self.where[0]} links to {slug}, which is not in the proposal.")
            first, last = min(numbers_), max(numbers_)
            shown = f"¶{first}" if first == last else f"¶{first}–{last}"
            return f"[{shown}](#p{first})"
        number = self.paragraphs.get(slug)
        if number is None:
            raise BuildError(f"{self.where[0]} links to {slug}, which is not in the proposal.")
        return f"[{'paragraph ' if form == 'p' else '¶'}{number}](#p{number})"

    def figure_ref(self, slug: str) -> str:
        number = self.figure_numbers.get(slug)
        if number is None:
            raise BuildError(f"{self.where[0]} links to {slug}, which is not in the proposal.")
        return f"[Figure {number}](#figure-{number})"

    def url(self, name: str) -> str:
        found = getattr(self.inputs.urls, name)
        if not found:
            raise BuildError(f"The data sheet can't link to {name}, because its URL isn't set in config/urls.toml.")
        return found

    def app(self, route: str) -> str:
        return self.url("app") + route

    def fill(self, text: str) -> str:
        def one(match: re.Match) -> str:
            kind, body = match.group(1), match.group(2).replace("\\|", "|")
            name, _, part = body.partition("|")
            if kind == "r":
                return self.against(name) if part == "against" else self.result_link(name, part or None)
            if kind == "s":
                return self.setting_link(name, capital=part == "cap")
            if kind in ("p", "¶", "sec"):
                return self.paragraph_ref(name, kind)
            if kind == "fig":
                return self.figure_ref(name)
            if kind == "copy":
                if name not in self.inputs.copy:
                    raise BuildError(f"The proposal did not build. {self.where[0]} quotes the app's words at {name}, "
                                     "which src/strata/proposal/copy.json does not hold.")
                return self.inputs.copy[name]
            if kind == "url":
                route = part or ""
                return self.app(route) if name == "app" else self.url(name)
            if kind == "model":
                if name not in self.inputs.models:
                    raise BuildError(f"The proposal did not build. {self.where[0]} names the model for {name}, which "
                                     "config/models.toml does not hold.")
                return f"`{self.inputs.models[name].deployment}`"
            raise BuildError(f"{self.where[0]} has a placeholder I don't know: {match.group(0)}.")

        return PLACEHOLDER.sub(one, text)


# ── Splitting and numbering ──────────────────────────────────────────────

def _measured_lines(source: str, results: dict) -> str:
    """The source with each {when:measured:key} line kept only while that result was measured, and each
    {when:unmeasured:key} line only while it was not."""
    kept = []
    for line in source.split("\n"):
        found = WHEN_MEASURED.match(line)
        if found:
            if bool(results.get(found.group(3), {}).get("measured")) != (found.group(2) == "measured"):
                continue
            line = (found.group(1) or "") + line[found.end():]
        kept.append(line)
    return "\n".join(kept)


WHEN_REHEARSED = re.compile(r"^\{when:(rehearsed|unrehearsed)\} ")


def _rehearsed_lines(source: str, every_drill_rehearsed: bool) -> str:
    """The source with each {when:unrehearsed} line kept only while a drill of the change drill has no rehearsal,
    such as the note that the times come later (the 46 brief, section 15, "Not rehearsed yet"), and each
    {when:rehearsed} line only once every drill has one."""
    kept = []
    for line in source.split("\n"):
        found = WHEN_REHEARSED.match(line)
        if found:
            if every_drill_rehearsed != (found.group(1) == "rehearsed"):
                continue
            line = line[found.end():]
        kept.append(line)
    return "\n".join(kept)


def _blocks(source: str) -> list[_Block]:
    blocks, section, subsection = [], "", None
    for chunk in re.split(r"\n\s*\n", source.strip()):
        chunk = chunk.strip("\n")
        heading = re.match(r"^(#{2,3})\s+(.*)$", chunk)
        if heading:
            slug = HEADING_SLUG.search(heading.group(2))
            name = HEADING_SLUG.sub("", heading.group(2))
            if heading.group(1) == "##":
                section, subsection = slug.group(1) if slug else name, None
            else:
                subsection = slug.group(1) if slug else name
        blocks.append(_Block(chunk, section, subsection))
    return blocks


def _is_paragraph(text: str) -> bool:
    body = SLUG.sub("", text).removeprefix("{when:designed} ")
    if body.startswith(UNNUMBERED) or body.startswith("{") and body.endswith("}") and "\n" not in body:
        return False
    if re.match(r"^\d+\.\s", body):
        return False
    first_line = body.splitlines()[0]
    return not (first_line.startswith("**") and body.rstrip().endswith("**") and body.count("**") == 2)


def _number(build: _Build, blocks: list[_Block], designed: bool) -> list[_Block]:
    kept, counting, number, figure = [], False, 0, 0
    for block in blocks:
        heading = re.match(r"^(#{2,3})\s+(.*)$", block.text)
        if heading and HEADING_SLUG.search(heading.group(2)):
            build.headings[HEADING_SLUG.search(heading.group(2)).group(1)] = HEADING_SLUG.sub("", heading.group(2))
        if heading and heading.group(1) == "##":
            name = HEADING_SLUG.sub("", heading.group(2))
            counting = counting or name == NUMBERED_FROM
            if name == NUMBERED_TO:
                counting = False
        found = SLUG.match(block.text)
        if found:
            block.slug = found.group(1)
            block.text = SLUG.sub("", block.text)
        if block.text.startswith("{when:designed} "):
            if not designed:
                continue
            block.text = block.text.removeprefix("{when:designed} ")
        figured = re.match(r"^\{figure:([a-z0-9-]+)\}", block.text)
        if figured:
            figure += 1
            build.figure_numbers[figured.group(1)] = figure
        if counting and not heading and _is_paragraph(block.text):
            number += 1
            block.number = number
            if block.slug:
                build.paragraphs[block.slug] = number
            for scope in (block.section, block.subsection):
                if scope:
                    build.sections.setdefault(scope, []).append(number)
        elif block.slug:
            raise BuildError(f"The paragraph {block.slug} is outside the numbered body, so nothing can link to it.")
        kept.append(block)
    return kept


# ── Tables the registries give ───────────────────────────────────────────

def _anchor(slug: str) -> str:
    return f'<a id="sec-{slug}"></a>'


def _cell(text: str) -> str:
    return text.replace("|", "\\|")


def _datasheet(build: _Build) -> str:
    results = [found for found in build.results.values() if found.get("measured") and found.get("measured_on")]
    days = sorted(_day(found["measured_on"]) for found in results)
    pulled = _day(build.inputs.snapshot["pulled_on"])
    app, deck, repo, dashboard = (build.url(name) for name in ("app", "deck", "repo", "dashboard"))
    rows = [("Dated", long_date(pulled)),
            ("Results measured", f"{short_date(days[0])[:-6]} to {short_date(days[-1])}, at commit "
                                 f"<code>{escape(build.inputs.commit[:7])}</code>"),
            ("Strata", f'<a href="{app}">{app}</a><br>Open it with the account your invitation went to.'),
            ("The deck", f'<a href="{deck}">{deck}</a>'),
            ("The repo", f'<a href="{repo}">{repo}</a>'),
            ("The dashboard", f'<a href="{dashboard}">Strata operations</a>'),
            ("The assessment", '<a href="assessment.md">docs/assessment.md</a>')]
    body = "\n".join(f'<tr><th scope="row">{name}</th><td>{text}</td></tr>' for name, text in rows)
    return f"<table>\n<tbody>\n{body}\n</tbody>\n</table>"


def _open_link(build: _Build, link: config.OpenLink) -> str:
    if link.kind == "app":
        return f"[{link.label}]({build.app(link.target)})"
    if link.kind == "dashboard":
        return f"[{link.label}]({build.url('dashboard')})"
    return f"[`{link.label}`](../{link.target})"


def _answered(build: _Build, ref: str) -> str:
    kind, _, slug = ref.partition(":")
    return build.figure_ref(slug) if kind == "fig" else build.paragraph_ref(slug, "sec")


def _md_inline(text: str) -> str:
    """Markdown links as HTML, for a cell inside an HTML table, where GitHub does not read Markdown."""
    text = re.sub(r'\[`([^`\]]+)`\]\(([^)\s]+)\)', r'<a href="\2"><code>\1</code></a>', text)
    return re.sub(r'\[([^\]]+)\]\(([^)\s]+)(?: "([^"]*)")?\)',
                  lambda m: f'<a href="{m.group(2)}"' + (f' title="{m.group(3)}"' if m.group(3) else "")
                  + f">{m.group(1)}</a>", text)


def _rubric_map(build: _Build) -> str:
    rubric = build.inputs.rubric
    points_link = f"assessment.md#{rubric.anchor}"
    head = ('<thead><tr><th scope="col">What the rubric looks for</th><th scope="col">Where this proposal answers it'
            '</th><th scope="col">What you can open</th></tr></thead>')
    groups = []
    for dimension in rubric.dimensions:
        summary = _md_inline(build.fill(dimension.summary))
        rows = [f'<tr><th scope="rowgroup" colspan="3"><a id="rubric-{dimension.key}"></a><strong>{dimension.name}</strong>, '
                f'<a href="{points_link}">{dimension.points}</a> points<br>{summary}</th></tr>']
        for criterion in dimension.criteria:
            answered = ", ".join(_md_inline(_answered(build, ref)) for ref in criterion.answered_in)
            opened = "; ".join(_md_inline(_open_link(build, link)) for link in criterion.open)
            rows.append(f'<tr><td data-quote="assessment">{criterion.says}</td><td>{answered}</td><td>{opened}</td></tr>')
        groups.append("<tbody>\n" + "\n".join(rows) + "\n</tbody>")
    foot = (f'<tfoot><tr><th scope="row" colspan="3">All four dimensions, <a href="{points_link}">{rubric.total}</a> '
            "points</th></tr></tfoot>")
    return "<table>\n" + head + "\n" + "\n".join(groups) + "\n" + foot + "\n</table>"


def _designed_list(build: _Build) -> str:
    items = build.inputs.designed
    if not items:
        return (f'Everything this proposal describes is built. Strata shows no "{build.inputs.copy["designedNotBuilt"]}" '
                "labels.")
    rows = ["| What | What exists now | Where Strata labels it |", "|---|---|---|"]
    for item in items:
        rows.append(f'| <a id="dnb-{item.key}"></a>{_cell(item.name)} | {_cell(item.exists_now)} | '
                    f"[{item.route}]({build.app(item.route)}) |")
    return "\n".join(rows)


def _ladder(build: _Build) -> str:
    ladder = config.load_ladder()
    lines = []
    for number, rule in enumerate(ladder.rules, 1):
        names = [TIERS.get(tier) for tier in (*rule.tiers, *rule.at_the_moment)]
        if None in names:
            raise BuildError("The proposal did not build. The evidence ladder names a tier the proposal has no words "
                             "for. Add it to TIERS in src/strata/proposal/build.py.")
        if rule.applies_to == "judgment":
            lines.append(f"{number}. For a judgment of how a project went, Strata leans on the later, more independent "
                         f"report, in this order: {', '.join(names[:-1])} and {names[-1]}.")
        else:
            lines.append(f"{number}. For something that happened at one moment, Strata leans on {names[0]}.")
    ties = [TIES.get(tie) for tie in ladder.ties]
    if None in ties:
        raise BuildError("The proposal did not build. The evidence ladder names a tie the proposal has no words for. "
                         "Add it to TIES in src/strata/proposal/build.py.")
    lines.append(f"{len(lines) + 1}. When sources rank the same, Strata leans on {' and then on '.join(ties)}.")
    return "\n".join(lines)


def _caps(build: _Build) -> str:
    rows = ["| Cap | Limit | What it stops |", "|---|---:|---|"]
    stops = {"cap-agent": "The agent's deployment answering faster than its cap",
             "cap-draft": "The drafting deployment answering faster than its cap",
             "cap-batch": "Bulk extraction queuing more than its cap",
             "cap-embed": "Embedding passages faster than its cap",
             "daily-page-cap": "The document reader reading more pages in a day",
             "cap-appinsights": "Traces stored past the day's cap",
             "replicas": "Hosting more copies of anything"}
    for key, stop in stops.items():
        setting = build.inputs.settings[key]
        rows.append(f"| {_cell(setting.name)} | {build.setting_link(key)} | {stop} |")
    return "\n".join(rows)


DRILL_TARGET = "drill-target"  # docs/proposal/settings.toml: the minutes a drill may take, PLAN.md section 15


def _drill_time(build: _Build, rehearsal: Rehearsal, linked: bool = True) -> str:
    """A rehearsal's minutes, as the change drill's table shows them (linked to the rehearsal's row in Annex 1) and
    as that row shows them, and under them the 46 brief's Missed target words when the drill took longer than the
    target (section 15), which are never left out. The target is cited, and so listed in Annex 2, only by a drill
    that missed it."""
    minutes = rehearsal.minutes
    unit = "minute" if minutes == 1 else "minutes"
    title = _title(f"{minutes} {unit}. {REHEARSAL_KIND}, measured {short_date(rehearsal.measured_on)}.")
    shown = f'[{numeral(minutes)}](#r-{rehearsal.key} "{title}")' if linked else numeral(minutes)
    if minutes > value(build.inputs.settings[DRILL_TARGET], build.inputs.day_one).number:
        shown += f"<br>Target: {build.setting_link(DRILL_TARGET, cite=linked)}. Not met."
    return shown


def _drill(build: _Build) -> str:
    rows = ["| Change | The one place it lives | Time, minutes | Proved by |", "|---|---|---:|---|"]
    for drill in build.inputs.drills:
        rehearsal = build.inputs.rehearsals.get(drill.change)
        if rehearsal is None:
            minutes = "Not rehearsed yet"
        else:
            minutes = _drill_time(build, rehearsal)
            build.cited_drills.append((rehearsal, build.where))
        rows.append(f"| {drill.change} | [`{drill.place}`](../{drill.place}) | {minutes} | "
                    f"[`{Path(drill.proved_by).name}`](../{drill.proved_by}) |")
    return "\n".join(rows)


def _framework(build: _Build) -> str:
    kpis = config.load_kpis()
    words = wording.words()["kpi"]
    by_kpi = {defined.params.get("kpi"): key for key, defined in build.inputs.results.items()
              if defined.query == "loop_indicator.sql"}
    groups = [("The assessment's examples", ["precision_recall", "blamed_covered", "weekly_users", "drafts_exported"]),
              ("Each loop", [kpi for kpi, found in kpis.items() if found.loop and kpi not in ("precision_recall",
                                                                                               "blamed_covered")]),
              ("Answer quality", ["benchmark_passed", "sentences_removed", "answers_held_back"])]
    measured_by = {"benchmark_passed": "benchmark-passed", "sentences_removed": "sentences-removed",
                   "answers_held_back": "answers-held-back"}
    # A target with a number is a setting, linked to Annex 2, in the words the dashboard's loop table gives it.
    targets = {"days_to_decision": ("lesson-decision-days", "Within {} business days"),
               "rolling_coverage": ("coverage-band", "{}")}
    rows = ["| Indicator | Target | Measured | Where it stands |", "|---|---|---:|---|"]
    for group, ids in groups:
        rows.append(f"| **{group}** | | | |")
        for kpi in ids:
            # The dashboard's name for the indicator, quoted. Its definition is on the dashboard: the definitions hold
            # numbers that define the measure ("my top 10 passages"), which no register row could source.
            indicator = f'"{_cell(words[kpi]["name"])}"'
            key = by_kpi.get(kpi) or measured_by.get(kpi)
            found = build.results.get(key, {"measured": False}) if key else {"measured": False}
            if kpi in targets:
                setting, words_ = targets[kpi]
                target = words_.format(build.setting_link(setting))
            elif found.get("target") and not re.search(r"\d", str(found["target"])):
                target = _cell(str(found["target"]))
            else:
                target = "None set"
            if kpi in WAITS_FOR_PILOT:
                rows.append(f"| {indicator} | {target} | Waits for the pilot | Waits for the pilot |")
                continue
            if not found.get("measured"):
                rows.append(f"| {indicator} | {target} | Not measured yet | Not measured yet |")
                continue
            rows.append(f"| {indicator} | {target} | {build.result_link(key)} | "
                        f"{_standing(str(found.get('against') or ''), target != 'None set')} |")
    return "\n".join(rows)


def _standing(against: str, has_target: bool) -> str:
    """Where an indicator stands, in words, from the dashboard's own comparison (DESIGN.md section 7, rule 44)."""
    within = re.fullmatch(r"([\d,]+) of ([\d,]+) within it", against)  # copy.dash.ai.cells.decisionsAgainst
    if against.startswith(("Inside", "Matched", "Met")) or (within and within.group(1) == within.group(2)):
        return "Met"
    if against.startswith(("Outside", "Lower", "Missed")) or within:
        return "Not met"
    return "Not measured yet" if has_target else "No target"


def _register(build: _Build) -> str:
    out = []
    for module in (1, 2, 3, 4):
        keys = [key for key, defined in build.inputs.results.items() if defined.module == module
                and key in build.cited_results]
        drills = build.cited_drills if module == DRILL_MODULE else []
        if not keys and not drills:
            continue
        days = sorted([_day(build.results[key]["measured_on"]) for key in keys]
                      + [rehearsal.measured_on for rehearsal, _ in drills])
        span = (f"Measured on {long_date(days[0])}." if days[0] == days[-1] else
                f"Measured from {long_date(days[0])} to {long_date(days[-1])}.")
        out.append(f"### Module {module} results\n\n{span}")
        rows = ["| Result | Value | Measured | Source | Cited in |", "|---|---:|---|---|---|"]
        for key in keys:
            defined, measured = build.inputs.results[key], build.results[key]
            shown = (_series_value(defined, measured) if defined.form == "series" else
                     build.result_text(defined, measured, None))
            if defined.form == "ratio" and measured.get("in_ten"):
                shown += f"; about {measured['in_ten']} in 10"
            if defined.target and defined.form == "ratio" and measured.get("percent") is not None:
                band = build.values.get(defined.target) or value(build.inputs.settings[defined.target])
                low, high = band.number, band.second
                if not low * 100 <= measured["percent"] <= high * 100:
                    shown += f"<br>Target: {build.setting_link(defined.target)}. Not met."
            source = (f"{defined.kind}; `{defined.table}`" + (f", run `{measured['run_id']}`" if measured.get("run_id")
                                                                else "")
                      + f"; [{Path(defined.query_file).name}](../{defined.query_file})")
            if defined.labels:
                source += f"<br>{_labels(defined, measured)}"
            cited = ", ".join(f"[{label}]({anchor})" for label, anchor in build.cited_results[key])
            rows.append(f'| <a id="r-{key}"></a>{_cell(defined.name)} | {_cell(shown)} | '
                        f"{short_date(_day(measured['measured_on']))} | {source} | {cited} |")
        rows += [_drill_row(build, rehearsal, where) for rehearsal, where in drills]
        out.append("\n".join(rows))
    return "\n\n".join(out)


DRILL_MODULE = 4  # the change drill's table is in Module 4, "Changing Strata in under ten minutes"
REHEARSALS_LINK = "[rehearsals.toml](../docs/proposal/rehearsals.toml)"


def _drill_row(build: _Build, rehearsal: Rehearsal, where: tuple[str, str]) -> str:
    """A rehearsal's row in Annex 1: what it timed, its minutes, the day, and the branch, commit and gate run that
    measured it."""
    change = rehearsal.change[:1].lower() + rehearsal.change[1:]
    name = f"Minutes to {change}, from making the drill's branch to the commit the gate passed on it"
    source = (f"{REHEARSAL_KIND}; branch `{rehearsal.branch}`, commit `{rehearsal.commit[:7]}`; the gate passed in "
              f"{numeral(rehearsal.gate_seconds)} seconds; {REHEARSALS_LINK}")
    label, anchor = where
    return (f'| <a id="r-{rehearsal.key}"></a>{_cell(name)} | {_drill_time(build, rehearsal, linked=False)} | '
            f"{short_date(rehearsal.measured_on)} | {source} | [{label}]({anchor}) |")


def _labels(defined: Result, measured: dict) -> str:
    """The line that says how a result's labels were made, with each {column} filled from the measured row."""
    def filled(match: re.Match) -> str:
        if measured.get(match.group(1)) is None:
            raise BuildError(f"The proposal did not build. The labels line of result {defined.key} counts "
                             f"{match.group(1)}, which its measured row does not hold. Name that column in the "
                             f"entry's columns in docs/proposal/results.toml, and pull the snapshot again.")
        return numeral(measured[match.group(1)])

    return re.sub(r"\{(\w+)\}", filled, defined.labels)


def _series_value(defined: Result, measured: dict) -> str:
    rows = measured["series"]
    labels = [str(row.get("fiscal_year_label") or row.get("label")) for row in rows]
    return f"{labels[0]} to {labels[-1]}, in the figure's table"


def _settings_annex(build: _Build) -> str:
    rows = ["| Setting | Value | Where it is set | What enforces it | Cited in |", "|---|---:|---|---|---|"]
    for key, setting in build.inputs.settings.items():
        if key not in build.cited_settings:
            continue
        found = build.values[key]
        file = setting.where.split(",")[0].split(" ")[0]
        where = f"[`{file}`](../{file})" + (f", {setting.where.split(',', 1)[1].strip()}" if "," in setting.where else "")
        if setting.planning_choice:
            where = setting.where
        if found.read_back:
            where = f"Read back from Azure on {short_date(found.read_back)}; set in {where}"
        elif found.not_read_back:
            where = f"Set in {where}. Not read back from Azure: {found.not_read_back}."
        if setting.read.startswith("count:"):
            where = f"Counted from {where}"
        enforced = ("A planning choice, not enforced by code." if setting.planning_choice else
                    f"{setting.enforces}: [`{Path(setting.enforced_by).name}`](../{setting.enforced_by})")
        cited = ", ".join(f"[{label}]({anchor})" for label, anchor in build.cited_settings[key])
        rows.append(f'| <a id="s-{key}"></a>{_cell(setting.name)} | {build.setting_text(setting, found)} | {where} | '
                    f"{enforced} | {cited} |")
    return "\n".join(rows)


def _sources_annex(build: _Build) -> str:
    from strata.tools.data_readiness_for import registry_page

    words = build.inputs.copy
    page = registry_page()
    lines = [words["attribution"].format(dataset=row["dataset_name"], source=row["data_source"], license=row["license"])
             for row in page["datasets"]]
    lines += [words["terms"], words["changes"], words["caveat"], words["authorizes"]]
    return "\n\n".join(lines)


# ── Figures ──────────────────────────────────────────────────────────────

def _figure(build: _Build, block: _Block) -> str:
    slug = re.match(r"^\{figure:([a-z0-9-]+)\}", block.text).group(1)
    number = build.figure_numbers[slug]
    file = f"proposal/figures/{number:02d}-{slug}.svg"
    if slug not in drawings.DRAWINGS:
        raise BuildError(f"Figure {number} is missing: {file}. Draw it in src/strata/proposal/figures.py, under the "
                         "strata-wb profile.")
    build.where = (f"Figure {number}", f"#figure-{number}")
    lines = block.text.splitlines()[1:]
    title = lines[0].replace("**Figure.", f"**Figure {number}.")
    context, twin = _figure_data(build, slug)
    build.figures[file] = drawings.DRAWINGS[slug](context)
    alt = context.get("alt") or re.search(r'aria-label="([^"]*)"', build.figures[file]).group(1)
    parts = [build.fill(title), f'<a id="figure-{number}"></a>', f"![{alt}]({file})",
             *(build.fill(line) for line in lines[1:])]
    if twin:
        parts.append(f"<details><summary>Show the table</summary>\n\n{twin}\n\n</details>")
    return "\n\n".join(parts)


def _figure_data(build: _Build, slug: str) -> tuple[dict, str | None]:
    if slug == "pipeline":
        labels = [source.readiness[0].label if source.readiness else key for key, source in config.load_sources().items()]
        return {"sources": list(dict.fromkeys(labels))}, None
    if slug == "reading":
        return {"embedding": build.inputs.models["embed"].deployment}, None
    if slug == "checks":
        from strata.agent.verifier import ALL_CHECKS

        missing = [check for check in ALL_CHECKS if check not in CHECK_NAMES]
        if missing:
            raise BuildError("The proposal did not build. The verifier runs a check Figure 7 has no name for. Add it "
                             "to CHECK_NAMES in src/strata/proposal/build.py.")
        return {"checks": [CHECK_NAMES[check] for check in ALL_CHECKS]}, None
    if slug == "award-gap":
        defined, measured = build.result("award-rows-by-year")
        series = measured["series"]
        alt = ("Bar chart of contract award rows per fiscal year, from "
               f"{series[0]['fiscal_year_label']} to {series[-1]['fiscal_year_label']}, coloured by the dataset or the "
               "award notices they came from.")
        rows = ["| Fiscal year | Contract award rows | From |", "|---|---:|---|"]
        rows += [f"| {row['fiscal_year_label']} | {build.result_link(defined.key, text=numeral(row['award_rows']))} | "
                 f"{row['dataset']} |" for row in series]
        return {"series": series, "alt": alt}, "\n".join(rows)
    if slug == "backtest":
        defined, measured = build.result("backtest-years")
        years = [row for row in measured["series"] if row.get("d")]
        alt = ("Dot chart of test years, the share of packages signed within the 8-in-10 point each year: "
               + "; ".join(f"{row['label']}, {row['percent']} percent" if row.get("percent") is not None
                           else f"{row['label']}, {row['n']} of {row['d']}, too few for a percentage" for row in years)
               + ". A reference line marks 8 in 10.")
        rows = ["| Test year | Signed within the 8-in-10 point | Share |", "|---|---:|---:|"]
        rows += [f"| {row['label']} | {build.result_link(defined.key, text=f'{numeral(row['n'])} of {numeral(row['d'])}')} "
                 f"| {build.result_link(defined.key, text=f'{row['percent']}%') if row.get('percent') is not None else 'Too few for a percentage'} |"
                 for row in years]
        return {"series": years, "alt": alt}, "\n".join(rows)
    if slug == "hindsight":
        _, caught = build.result("hindsight-caught")
        _, checklist = build.result("hindsight-checklist")
        interval = build.results.get("hindsight-interval", {})
        strata_row = {"name": "Strata's risk tables", "n": caught["n"], "d": caught["d"]}
        if interval.get("measured"):
            build.result("hindsight-interval")
            strata_row |= {"low": interval["low"], "high": interval["high"]}
        rows_ = [strata_row, {"name": "The sector checklist", "n": checklist["n"], "d": checklist["d"]}]
        alt = (f"Dot chart: Strata's risk tables showed {caught['n']} of {caught['d']} blamed risks; the sector "
               f"checklist named {checklist['n']} of {checklist['d']}.")
        table = ["| Who | Blamed risks caught |", "|---|---:|",
                 f"| Strata's risk tables | {build.result_link('hindsight-caught')} |",
                 f"| The sector checklist | {build.result_link('hindsight-checklist')} |"]
        if interval.get("measured"):
            table.append(f"| Strata's interval | {build.result_link('hindsight-interval')} |")
        return {"rows": rows_, "alt": alt}, "\n".join(table)
    return {}, None


# ── The build ────────────────────────────────────────────────────────────

DIRECTIVES = {"{rubric-map}": _rubric_map, "{framework}": _framework, "{caps}": _caps, "{drill}": _drill,
              "{ladder}": _ladder, "{designed}": _designed_list, "{annex:sources}": _sources_annex}
LATE = {"{annex:results}": _register, "{annex:settings}": _settings_annex}


def build(source: str, inputs: Inputs) -> Built:
    """docs/proposal.md and its figures, from the source, the snapshot and the registries."""
    work = _Build(inputs)
    rehearsed = all(drill.change in inputs.rehearsals for drill in inputs.drills)
    source = _rehearsed_lines(_measured_lines(source, work.results), rehearsed)
    blocks = _number(work, _blocks(source), designed=bool(inputs.designed))
    out: list[str] = []
    late: list[tuple[int, str]] = []
    for block in blocks:
        text = block.text
        if block.number:
            work.where = (f"Paragraph {block.number}", f"#p{block.number}")
        elif not text.startswith("{figure:"):
            scope = block.subsection or block.section
            work.where = (f"The section \"{work.headings.get(scope, scope or 'Strata: a technical proposal')}\"",
                          f"#sec-{scope}" if scope else "#")
        if text.strip() == "{datasheet}":
            out.append(_datasheet(work))
        elif text.strip() in DIRECTIVES:
            out.append(DIRECTIVES[text.strip()](work))
        elif text.strip() in LATE:
            late.append((len(out), text.strip()))
            out.append("")
        elif text.startswith("{figure:"):
            out.append(_figure(work, block))
        else:
            heading = re.match(r"^(#{1,3})\s+(.*)$", text)
            if heading:
                slug = HEADING_SLUG.search(heading.group(2))
                name = HEADING_SLUG.sub("", heading.group(2))
                text = (f"{_anchor(slug.group(1))}\n\n" if slug else "") + f"{heading.group(1)} {name}"
                out.append(work.fill(text))
            elif block.number:
                body = " ".join(line.strip() for line in text.splitlines())
                out.append(f'<a id="p{block.number}"></a>**{block.number}.** {work.fill(body)}')
            else:
                out.append(work.fill(text))
    for position, directive in late:
        out[position] = LATE[directive](work)
    markdown = "\n\n".join(part for part in out if part) + "\n"
    problems = numbers.unsourced(markdown)
    if problems:
        raise BuildError("\n".join(problem.sentence() for problem in problems))
    return Built(markdown, work.figures)


def write(built: Built, proposal: Path) -> None:
    """The proposal and its figures, beside each other as the links expect."""
    proposal.write_text(built.markdown)
    for file, svg in built.figures.items():
        target = proposal.parent / file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(svg)
