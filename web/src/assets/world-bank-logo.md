# The World Bank Group logo

`world-bank-logo.svg` is the World Bank Group logo that worldbank.org shows in its own dark footer: white artwork for dark backgrounds, kept unaltered (DESIGN.md section 9).

- Source: https://www.worldbank.org/ext/en/media_1540be393bca9ed1fbc89eaa862044ccb08019dd2.svg, the image in https://www.worldbank.org/ext/en/footer.plain.html.
- Downloaded: October 23, 2026, by ticket 06.
- SHA-256: c11d30bf69ad0f6f224b350e93ea976bbac438ff18c82786d1c11454a0317aff
- Size: 250 by 50, shown at 120 by 24 px in the navy bar, with clear space of at least half its height on every side and 24 px before the wordmark.
- Text alternative: "World Bank Group logo", because the artwork reads WORLD BANK GROUP.

The 06 design brief named the header file, https://www.worldbank.org/ext/en/media_1b9d836624bdfd028dfbe9f018f3f12e52326504c.svg, as white artwork. It is not: its globe is a blue gradient and its wordmark is `#002F54`, which disappears on the navy bar. worldbank.org uses it on its white header, so Strata uses the footer's white file instead.

The World Bank's terms say its logos need express written permission and must not imply an association. DESIGN.md section 9 records why the private demo shows it anyway, and the footer disclaimer stays on every screen. `web/tests/shell.spec.ts` checks that the file the app serves still matches the hash above.
