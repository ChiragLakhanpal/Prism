# 92: The sidebar and the rail replace the tabs in the bar

**What to build:** Paste block 2 of `design-md.md`. From 1024 px a `nav` named "Main" beside the page on `page` grey with a hairline edge: Home, then the applied view's sections in `SECTIONS` order (Packages, Projects, Lessons, Drafts), and at its foot Data and "Collapse the sidebar". 224 px open from 1440 px and a 64 px rail of icons from 1024 to 1439 px; a person's choice is kept in local storage. The width changes at once, never animated. Rail items show their label in a tooltip on hover and keyboard focus. The current item is `matchRoute`'s section, with `aria-current="page"` on the section's page and `"true"` on a page inside it. Add a slot for a section's own pages under its item, shown only while it is current (the tab tickets fill it), and hide the sections and sub-items the applied view hides (`config/roles.toml` lines 182 to 191). Below 1024 px the same content is the Menu sheet, a modal dialog from the left that slides in over 200 ms on `ease-drawer` and out over 120 ms. Add an inline script to `web/index.html` that reads the stored choice and the width before any script loads, and paint the sidebar's frame there, so nothing shifts when React mounts. The bar keeps the logo, the wordmark and the view switch, and the band keeps the box and the stamp; the next ticket moves them. New copy keys: `nav.home`, `nav.collapse`, `nav.expand`, `nav.menuClose`. Icons from lucide: `house`, `package`, `folder-open`, `book-open`, `file-pen-line`, `database`, `panel-left-close`, `panel-left-open`.

Read first: the plan's sections 7.2, 7.3 and 8.1; block 2 of `design-md.md`; the prototype at 1440, 1280 and 390 px, with its "Rail at rest" switch on By width, Labels and Icons, the Menu open at 390 px, and the View switch on Public; `web/src/components/TopNav.tsx` (`SECTIONS`, the Menu panel, the focus hand-offs at 466 to 479); `web/src/components/Frame.tsx`; `web/src/App.tsx` (`navMode.tabs`, `projectsHref`); `web/src/routes.ts`; `web/index.html` lines 8 to 25; `web/src/gallery/Gallery.tsx`; `web/tests/shell.spec.ts` (lines 61 to 83), `gallery-frame.spec.ts`, `routes.spec.ts`.

**Blocked by:** 90 (Tokens, fonts and lint for the redesigned shell)

**Status:** ready
**Area:** app
**Phase:** P4
**Design review:** yes

- [ ] From 1024 px the sections are a sidebar named "Main" beside the page, 224 px wide from 1440 px and 64 px from 1024 to 1439 px by default, Home first and each section of the applied view once, and the bar holds no section link; `shell.spec.ts` and `gallery-frame.spec.ts` prove the order, the widths and `aria-current` at 1440, 1280 and 1024 px.
- [ ] "Collapse the sidebar" turns it into the rail and "Expand the sidebar" back, the choice survives a reload, each rail item's tooltip shows its label on hover and on keyboard focus, and a test finds no transition on the sidebar's width.
- [ ] `web/index.html` paints the sidebar's frame at the stored or default width before any script runs, and `shell.spec.ts`'s first-paint test finds the painted and mounted sidebar, bar and band boxes equal at 1440, 1280, 800 and 390 px.
- [ ] Below 1024 px the labelled Menu button opens the Menu sheet as a modal dialog named "Menu" with the page and the bar inert; Escape, "Close the menu" and the scrim close it and return focus to the Menu button; when the window narrows past 1024 px, focus on a sidebar item moves to the Menu button.
- [ ] Every route still opens from its item and focuses its h1 (`routes.spec.ts`), the public view shows Home, Projects, Lessons and Data only and the officer's view no Following and no reviewer pages (`views.spec.ts`), and axe, reflow at 320 px and the target sizes pass on every route.

**Gate seconds added:** about -0.4 (+0.4 for the rail tooltip and width tests; -0.8 because the 22 `navigation--*` and `views--*` shots become about 16 states, each captured once per width).

## Comments

- October 27, 2026, design-lead: drafted from the shell redesign plan, round 3. The width no longer animates (plan 5.7: width is a layout property, and the motion adds wait without news). Settles in full ticket 58's Menu label at 320 px (line 129); in part ticket 60's wordmark touching the Menu button at 320 px (line 47), which the bar ticket finishes. Specs to update: shell.spec.ts, gallery-frame.spec.ts, routes.spec.ts, views.spec.ts, capture.spec.ts (and languages.spec.ts, sweep.spec.ts and gallery-a11y.spec.ts where they name the tabs). Gallery states: sidebar open, rail, rail tooltip, focus and hover on an item, the sheet open, a sheet row focused, 320 px, and the public view's sidebar. Ticket 57's two whitespace items in specs this ticket edits may ride along.

---
