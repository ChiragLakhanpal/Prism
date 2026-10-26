"""The proposal's number check (ticket 46; the 46 brief, sections 9.1 and 9.5): every number links to a measured
result (Annex 1) or a setting (Annex 2), unless it is a date, a year, a sequence number, an identifier or a fixed
name on the allow list. The check reads text, so the deck (ticket 47) runs it on its slides' HTML too.

Each expected outcome is worked out by hand from the brief's rules.
"""

from strata.proposal import numbers


def sentences(text, form="markdown"):
    return [problem.sentence() for problem in numbers.unsourced(text, form=form)]


def test_a_number_linked_to_its_register_row_passes():
    text = '<a id="p12"></a>**12.** [31 of 37](#r-backtest-coverage "31 of 37 test packages. Backtest, measured Oct 20, 2026.") test packages finished inside the 8-in-10 range.'
    assert sentences(text) == []


def test_a_setting_linked_to_annex_2_passes_and_so_do_its_words():
    text = '<a id="p3"></a>**3.** Strata gives no range from fewer than [20](#s-fewest-comparables) comparables, and it checks every sentence [six](#s-check-count) ways.'
    assert sentences(text) == []


def test_an_unlinked_number_fails_with_its_paragraph_and_an_excerpt():
    text = '<a id="p7"></a>**7.** Strata read 4,812 pages well.'
    assert sentences(text) == [
        'The number check failed. Paragraph 7 has a number with no source: "Strata read 4,812 pages well.". '
        "Link it to Annex 1 or Annex 2, or add it to the allow list with a reason."]


def test_a_number_word_from_two_to_nine_fails_but_one_does_not():
    assert [p.number for p in numbers.unsourced('<a id="p2"></a>**2.** One reviewer read seven reports.')] == ["seven"]


def test_dates_years_and_fiscal_years_are_excepted():
    text = ('<a id="p4"></a>**4.** On October 20, 2026, and again on Oct 23, 2026, in fiscal 2017 to 2019 (FY2017–19, '
            "FY01 to FY26), from 2021 to 2025 and in 2019–23, on 2026-10-09.")
    assert sentences(text) == []


def test_sequence_numbers_and_identifiers_are_excepted():
    text = ('<a id="p5"></a>**5.** ICR paragraph 78, on page 27, disagrees with ISR 7 about Components 2 and 3; see '
            "Module 1, Figure 3, Annex 2, section 5, ¶12–19 and paragraphs 3 to 5. Award notice OP00044090 for "
            "IN-RRSMP-7431-CW-RFB on P130164 uses `gpt-5.4-mini`, WCAG 2.2 and the 7th edition of the Regulations.")
    assert sentences(text) == []


def test_the_rubric_points_link_to_the_assessment():
    text = '| **System and knowledge architecture**, [30](assessment.md#5-evaluation--assessment-rubric) points |'
    assert sentences(text) == []


def test_fixed_names_on_the_allow_list_pass():
    assert sentences('<a id="p1"></a>**1.** Strata keeps the three strata apart, as the four modules ask, inside the 8-in-10 range.') == []


def test_link_urls_code_and_html_attributes_hold_no_numbers_the_check_counts():
    text = ('<a id="p9"></a>**9.** Open [Data readiness](https://strata-1.aws.databricksapps.com/data?x=12) or '
            '`config/thresholds.toml`, line 140, <span lang="fr">texte</span>.')
    assert [p.number for p in numbers.unsourced(text)] == ["140"]


def test_a_number_in_a_table_names_the_heading_above_it():
    text = "## Annex 2: Settings and counts\n\n| Setting | Value |\n|---|---:|\n| Fewest comparables | 20 |\n"
    assert sentences(text) == [
        'The number check failed. The block under "Annex 2: Settings and counts" has a number with no source: '
        '"| Fewest comparables | 20 |". Link it to Annex 1 or Annex 2, or add it to the allow list with a reason.']


def test_the_check_reads_html_where_a_sourced_number_carries_its_snapshot_key():
    html = ('<p>Strata caught <span data-source-key="caught">12</span> of <a href="#r-blamed">30</a> risks, '
            "and 5 more.</p>")
    assert [p.number for p in numbers.unsourced(html, form="html")] == ["5"]


def test_images_carry_no_links_so_their_alt_text_is_left_to_the_build():
    assert sentences("![Bars for 12 fiscal years](proposal/figures/02-award-gap.svg)") == []
