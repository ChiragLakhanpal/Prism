"""The deck's figures (ticket 47; the second draft's brief, sections 4 to 6): eleven diagram-design figures under the
strata-wb profile and the hairline-create figures, which the deck at /present shows.

Each diagram is drawn as HTML in web/figures/ and exported beside the registry, web/src/figures/<key>.svg, with the
skill's own exporter and --system-fonts, so the app's self-hosted Open Sans and Roboto Mono draw its text and it loads
nothing from the network. Each marks the parts a press brings in with the skill's step markup in its static "none"
mode, so the deck can show it a step at a time while the source stays whole. The hairline figures run on the skill's
kernel, vendored unchanged. The colours and fonts allowed here are DESIGN.md section 11's strata-wb light skin.
"""

import re
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DIAGRAM = ROOT / ".claude" / "skills" / "diagram-design" / "scripts"
HAIRLINE = ROOT / ".claude" / "skills" / "hairline-create"
SOURCES = ROOT / "web" / "figures"
EXPORTS = ROOT / "web" / "src" / "figures"
# The second draft's brief, section 4, and web/src/figures/order.ts: each figure's slot, drawn 1:1.
SLOTS = {"stage": (864, 352), "half": (420, 352)}
FIGURES = {"strata": "stage", "one-answer": "stage", "layers": "stage", "architecture": "stage", "pipeline": "stage", "reading": "stage",
           "knowledge-model": "stage", "retrieval": "stage", "estimate": "stage", "checks": "stage", "ladder": "half",
           "loops": "stage"}
# The skill's motion budget (references/animation.md): at most eight steps, twelve marked parts and two a step.
MOST_STEPS, MOST_ITEMS, MOST_A_STEP = 8, 12, 2
HAIRLINES = sorted(path.stem for path in (EXPORTS / "hairline").glob("*.js") if path.stem != "kernel")
# DESIGN.md section 11, light: paper, ink, muted, soft, accent and link, and white for a backend node's fill.
PALETTE = {"#f5f7f9", "#181f25", "#4b5e71", "#586e84", "#0071bc", "#01707e", "#ffffff"}
FONTS = {"'Open Sans', system-ui, sans-serif", "'Roboto Mono', ui-monospace, monospace"}


@pytest.mark.parametrize("slug", FIGURES)
def test_each_figure_is_its_html_source_exported_by_the_skill_with_system_fonts(slug, tmp_path):
    out = tmp_path / f"{slug}.svg"
    subprocess.run([sys.executable, "-I", str(DIAGRAM / "export_svg.py"), str(SOURCES / f"{slug}.html"), str(out),
                    "--system-fonts"], check=True, capture_output=True)
    assert out.read_text() == (EXPORTS / f"{slug}.svg").read_text(), (
        f"web/src/figures/{slug}.svg is not the export of web/figures/{slug}.html. Export it again with "
        ".claude/skills/diagram-design/scripts/export_svg.py and --system-fonts.")


def test_every_source_passes_the_skills_self_check_with_no_web_font():
    done = subprocess.run([sys.executable, "-I", str(DIAGRAM / "self_check.py"), "--offline",
                           *[str(SOURCES / f"{slug}.html") for slug in FIGURES]], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr


@pytest.mark.parametrize("slug", FIGURES)
def test_each_figure_is_drawn_in_its_slot_in_strata_wb_colours_and_type_and_names_itself(slug):
    svg = (EXPORTS / f"{slug}.svg").read_text()
    width, height = SLOTS[FIGURES[slug]]
    assert f'viewBox="0 0 {width} {height}"' in svg
    colours = set(re.findall(r'\b(?:fill|stroke)="([^"]+)"', svg)) - {"none"}
    assert colours <= PALETTE, f"{slug} uses {sorted(colours - PALETTE)}, outside the strata-wb profile"
    assert set(re.findall(r'font-family="([^"]+)"', svg)) <= FONTS
    # Labels are in sentence case, never tracked capitals (DESIGN.md sections 3 and 11).
    assert "letter-spacing" not in svg and "uppercase" not in svg, f"{slug} sets a tracked or capital label"
    assert "googleapis" not in svg and "@import" not in svg
    # The logo sits in each slide's header, never inside a drawing (DESIGN.md section 9).
    assert "<image" not in svg and "logo" not in svg.lower()
    assert f'role="img" aria-labelledby="{slug}-title {slug}-desc"' in svg
    assert re.search(rf'<svg[^>]*>\s*<title id="{slug}-title">', svg), "the title is the first child"


def test_the_hairline_kernel_is_the_skills_own_unchanged():
    assert (EXPORTS / "hairline" / "kernel.js").read_bytes() == (HAIRLINE / "kernel.js").read_bytes()


@pytest.mark.parametrize("slug", FIGURES)
def test_each_figure_marks_its_steps_within_the_skills_motion_budget_and_stays_static(slug):
    svg = (EXPORTS / f"{slug}.svg").read_text()
    root = re.search(r"<svg\b[^>]*>", svg).group(0)
    count = int(re.search(r'data-step-count="(\d+)"', root).group(1))
    assert 'data-motion-mode="none"' in root, "the source stays static; the deck steps it"
    items = re.findall(r"<[^>]*\bdata-motion-item\b[^>]*>", svg)
    steps = [int(re.search(r'data-step="(\d+)"', tag).group(1)) for tag in items]
    assert 1 <= count <= MOST_STEPS and len(steps) <= MOST_ITEMS
    assert sorted(set(steps)) == list(range(1, count + 1)), f"{slug}'s steps are not 1 to {count}"
    assert max(steps.count(step) for step in set(steps)) <= MOST_A_STEP
    assert "<script" not in svg


def test_the_deck_has_its_openers_beside_the_core_sample():
    assert "core-sample" in HAIRLINES
    assert len(HAIRLINES) >= 2, "the topic openers' hairline figures are missing"


@pytest.mark.parametrize("name", HAIRLINES)
def test_each_hairline_figure_passes_the_hairline_validator(name, tmp_path):
    page = tmp_path / f"hairline-{name}.html"
    subprocess.run(["node", str(HAIRLINE / "build.mjs"), str(EXPORTS / "hairline" / f"{name}.js"), str(page)],
                   check=True, capture_output=True)
    done = subprocess.run(["node", str(HAIRLINE / "validate.mjs"), str(page)], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
