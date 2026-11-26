# Changelog

## Unreleased

- The Shelf design replaces the Gallery look. It has a slim banner, a rail of categories and filters, poster cards and a facts strip.
- The storefront text now holds facts settled from the plug-ins' code and READMEs and the owner's answers (DASH-576). `python3 tools/open_questions.py` lists what is still unclear.
- Each plug-in page now shows memory, processor and image size measured on a test Starboard with made-up data, and category pages can sort by memory.
- A page for each category and an index of categories, linked from the home page, the menu and every plug-in page, with breadcrumbs.
- Search on the home page and each category page needs every word in a plug-in's name, summary, category or tags. It announces the result count and sends nothing.
- Each plug-in page now says what it does, who it is for, what you will see and what it needs.
- A gallery of real screenshots (made-up data, from a test Starboard) on plug-in pages, with alt text.
- The menu of every page now has Display and accessibility settings, such as theme, text size to 175% and reduce motion. They stay in this browser only.
- The daily refresh now sends a read-only token to GitHub's API only. This fixes the 403 that stopped the Starboard releases refresh on 24 and 25 November 2026.
- The first real Stallboard is built by `tools/build.py` from design concept C. It lists 33 of the owner's own plug-ins, reviewed by TheMightyTRexUK on 23 November 2026.
- Start here: Starboard page, and "Needs Starboard X or later" on every plug-in, worked out from each release's plug-in API.
- Every plug-in page now has What it uses, with declared limits and measured figures kept apart, and cards show a memory line.
- Submissions come by GitHub issue form, with automatic checks, a maintainer's approval and a pull request. A daily refresh updates the snapshots by pull request.
- `catalogue.json` in the schema Starboard's catalogue sources read.
- Snaglist feedback on every page; privacy, accessibility and What Reviewed means pages.
- Tests, an HTML check and the accessibility checks (axe 4 at WCAG 2.2 AA plus best practice, keyboard, zoom, text size, forced colours, no JavaScript).
