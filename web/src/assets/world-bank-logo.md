# The World Bank Group logo

`world-bank-logo.svg` is the World Bank Group logo that worldbank.org shows in its own dark footer: white artwork for dark backgrounds, kept unaltered (DESIGN.md section 9).

- Source: https://www.worldbank.org/ext/en/media_1540be393bca9ed1fbc89eaa862044ccb08019dd2.svg, the image in https://www.worldbank.org/ext/en/footer.plain.html.
- Downloaded: October 23, 2026, by ticket 06.
- SHA-256: c11d30bf69ad0f6f224b350e93ea976bbac438ff18c82786d1c11454a0317aff
- Size: 250 by 50, shown at 120 by 24 px in the navy bar, with clear space of at least half its height on every side and 24 px before the wordmark.
- Text alternative: "World Bank Group logo", because the artwork reads WORLD BANK GROUP.

The 06 design brief named the header file, https://www.worldbank.org/ext/en/media_1b9d836624bdfd028dfbe9f018f3f12e52326504c.svg, as white artwork. It is not: its globe is a blue gradient and its wordmark is `#002F54`, which disappears on the navy bar. worldbank.org uses it on its white header, so Strata uses the footer's white file instead.

The World Bank's terms say its logos need express written permission and must not imply an association. DESIGN.md section 9 records why the private demo shows it anyway, and the footer disclaimer stays on every screen. `web/tests/shell.spec.ts` checks that the file the app serves still matches the hash above.

# The World Bank logo for light backgrounds

`world-bank-logo-light.svg` is the header logo of data.worldbank.org: a gradient globe and `#002f54` lettering, the World Bank's own artwork for light backgrounds, kept unaltered (DESIGN.md section 9). The deck at /present (ticket 47) shows it on the title slide and in the credit row of each deck figure, 24 px tall (121 by 24), with clear space of half its height on every side. The navy bar keeps the white file above.

- Source: https://data.worldbank.org/assets/images/logo-wb-header-en.svg
- Downloaded: October 26, 2026, by ticket 47.
- SHA-256: 15a18185cbdc72239c7b052225e47d533c3128adc6df99e699ba3018ae3b6c9a
- Size: 172 by 34 (its viewBox), shown at 121 by 24 px.
- Text alternative: "World Bank Group logo", because, like the white file, its lettering reads WORLD BANK GROUP. The 47 brief asked for "World Bank logo"; the words that match the artwork win.
- It declares its gradient with the id `a`, so the app shows it only as an `<img>`, never inlined, where that id could clash with another drawing's. `web/tests/deck.spec.ts` checks that the file the deck serves still matches the hash above.
