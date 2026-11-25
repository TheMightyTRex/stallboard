# Changelog

## Unreleased

- The Shelf design (compact banner), replacing the Gallery look: a slim banner with search, a left rail of categories, Works with, the Starboard you have and sort, poster cards that are all one height with at most three chips, and a facts strip (Reviewed, Works with, Starboard, Memory use) on each plug-in page with more plug-ins from the same category. Every card gets the same picture treatment, the logo on a tint of its category colour, or a lettered tile when there is no logo. On a phone, Search and a Filters button sit together; Filters opens a bottom sheet with Works with first, and the filters that are on show as removable chips. One accent colour, an 8 px spacing scale, a calmer Display palette in light, dark, high contrast and forced colours. The Made for you demo, the picture collage and the New and updated strip are gone from the home page.
- Facts settled in the storefront text (DASH-576), from the plug-ins' current code and READMEs and the owner's answers: Styles (17 of 22 change every part), Uptime and status (written from version 2.1.0), VPN check, Direct play, Library clean-up, Download summary, Notifications, Line speed, Tdarr, Checkrr, Audio description and Audio description tracks, Seerr, Wizarr, Backups watch and Philips Hue. Themearr now shows Jellyfin only. What is still unclear is in `python3 tools/open_questions.py`.
- A page for each category and an index of categories, linked from the home page, the menu and every plug-in page, with breadcrumbs.
- Search on the home page and on each category page: every word must be in a plug-in's name, summary, category or tags; the result count is announced; nothing is sent.
- Better plug-in pages: What it does, Who it is for, What you will see, What it needs and its system tags, written for every plug-in from its own README and help pages; the summary on each card comes from the same text.
- A gallery of real screenshots (made-up data, from a test Starboard) on plug-in pages, with alt text.
- Display and accessibility in the menu of every page: theme, text size to 175%, reduce motion, high contrast, underline links, wider text spacing and remove drop shadows, kept in this browser only. It replaces the Dark colours button (a saved choice from that button is still read).
- The daily refresh sends the workflow's read-only token to GitHub's API (and nowhere else), which fixes the 403 that stopped the Starboard releases refresh on 24 and 25 November 2026; it says the rate-limit figures when GitHub refuses; it can also be started by a `starboard-release` or `plugin-release` event; and it opens an issue when it fails.
- The first real Stallboard, built from design concept C: a static site generator (`tools/build.py`), 33 listings of the owner's own plug-ins, reviewed by TheMightyTRexUK on 23 November 2026, each with its real logo and help address.
- Start here: Starboard page, and "Needs Starboard X or later" on every plug-in, worked out from each release's plug-in API.
- What it uses on every plug-in: declared limits and measured figures kept apart; the first measurements, from a real server; a memory line on cards; sort by memory.
- Submissions by GitHub issue form with automatic checks (Starboard's own manifest check), a maintainer's approval and a pull request; daily snapshot refresh by pull request; deploy to GitHub Pages (not switched on).
- `catalogue.json` in the schema Starboard's catalogue sources read.
- Snaglist feedback on every page; privacy, accessibility and What Reviewed means pages.
- Tests, an HTML check and the accessibility checks (axe 4 at WCAG 2.2 AA plus best practice, keyboard, zoom, text size, forced colours, no JavaScript).
