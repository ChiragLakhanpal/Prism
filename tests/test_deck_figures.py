"""The deck's figures (ticket 47; the 47 brief, section 4): seven diagram-design figures under the strata-wb profile and
one hairline-create figure, shared by the deck at /present and How Strata works.

Each diagram is drawn as HTML in web/figures/ and exported beside the registry, web/src/figures/<key>.svg, with the
skill's own exporter and --system-fonts, so the app's self-hosted Open Sans and Roboto Mono draw its text and it loads
nothing from the network. The hairline figure runs on the skill's kernel, vendored unchanged. The colours and fonts
allowed here are DESIGN.md section 11's strata-wb light skin.
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
# The 47 brief, section 3.4: each figure's slot, drawn 1:1.
SLOTS = {"wide": (864, 268), "narrow": (568, 268), "half": (420, 268)}
FIGURES = {"one-answer": "narrow", "pipeline": "wide", "reading": "narrow", "knowledge-model": "wide",
           "retrieval": "wide", "ladder": "half", "loops": "wide"}
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
    assert "googleapis" not in svg and "@import" not in svg
    # The logo sits in the deck's credit row, never inside a drawing (DESIGN.md section 9).
    assert "<image" not in svg and "logo" not in svg.lower()
    assert f'role="img" aria-labelledby="{slug}-title {slug}-desc"' in svg
    assert re.search(rf'<svg[^>]*>\s*<title id="{slug}-title">', svg), "the title is the first child"


def test_the_hairline_kernel_is_the_skills_own_unchanged():
    assert (EXPORTS / "hairline" / "kernel.js").read_bytes() == (HAIRLINE / "kernel.js").read_bytes()


def test_the_core_sample_figure_passes_the_hairline_validator(tmp_path):
    page = tmp_path / "hairline-core-sample.html"
    subprocess.run(["node", str(HAIRLINE / "build.mjs"), str(EXPORTS / "hairline" / "core-sample.js"), str(page)],
                   check=True, capture_output=True)
    done = subprocess.run(["node", str(HAIRLINE / "validate.mjs"), str(page)], capture_output=True, text=True)
    assert done.returncode == 0, done.stdout + done.stderr
