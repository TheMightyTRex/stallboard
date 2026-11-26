# Contributing

Thank you for helping. There are three ways.

## List a plug-in

Use the [Submit a plug-in form](https://github.com/TheMightyTRex/stallboard/issues/new?template=submit-a-plug-in.yml). Do not open a pull request that adds a listing yourself: a listing carries a review, and a maintainer's approval makes the pull request.

## Report a problem with Stallboard

Use the Send feedback button on the site, or open an issue. For a problem with one plug-in, use the "Report a problem with this plug-in" link on its page: it goes to the plug-in's maker.

## Change the code or the words

1. Fork, then branch from `main`.
2. Run `python3 -m unittest discover -s tests`, `python3 tools/build.py`, `python3 tools/check_html.py site` and `tools/run.sh check`. All must pass, with zero accessibility violations.
3. Open a pull request that says what changed and why.

House rules, which a test checks in part: British English, sentence case headings, no em dashes, no contractions, and never "See" or "Look" in interface text. Name the thing instead, such as "What Reviewed means". Use the standard library only for the Python in `tools/`. The pages must work without JavaScript. Nothing may load from another site. Never edit `assets/ds/` or `vendor/starboard/` by hand, because they are copies. The README says how each is refreshed.

Workflow files follow four rules. Every action is pinned to a full commit hash. Each job has the least permissions it needs. Nothing from an issue or a pull request goes into a shell line. `pull_request_target` is not used. A test checks these rules.

By contributing you agree your work is under the MIT licence. Please follow the [code of conduct](CODE_OF_CONDUCT.md).
