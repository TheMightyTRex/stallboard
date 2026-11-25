# Changelog

## Unreleased

- The daily refresh sends the workflow's read-only token to GitHub's API (and nowhere else), which fixes the 403 that stopped the Starboard releases refresh on 24 and 25 November 2026; it says the rate-limit figures when GitHub refuses; it can also be started by a `starboard-release` or `plugin-release` event; and it opens an issue when it fails.
- The first real Stallboard, built from design concept C: a static site generator (`tools/build.py`), 33 listings of the owner's own plug-ins, reviewed by TheMightyTRexUK on 23 November 2026, each with its real logo and help address.
- Start here: Starboard page, and "Needs Starboard X or later" on every plug-in, worked out from each release's plug-in API.
- What it uses on every plug-in: declared limits and measured figures kept apart; the first measurements, from a real server; a memory line on cards; sort by memory.
- Submissions by GitHub issue form with automatic checks (Starboard's own manifest check), a maintainer's approval and a pull request; daily snapshot refresh by pull request; deploy to GitHub Pages (not switched on).
- `catalogue.json` in the schema Starboard's catalogue sources read.
- Snaglist feedback on every page; privacy, accessibility and What Reviewed means pages.
- Tests, an HTML check and the accessibility checks (axe 4 at WCAG 2.2 AA plus best practice, keyboard, zoom, text size, forced colours, no JavaScript).
