# Security

## Report a vulnerability privately

Do not open a public issue. Use [a private security advisory](https://github.com/TheMightyTRex/stallboard/security/advisories/new) on this repository. Say what you found, where, and how to repeat it. We aim to answer within a week and to fix real problems quickly, and we will credit you if you wish.

In scope: the submission and approval workflows, the fetch code (`tools/lib/safefetch.py`), the build, the pages (for example script injection from a plug-in's text), and `catalogue.json`. A plug-in that is itself harmful: report it the same way, and it will be taken off.

## How a submission is kept safe

- **Data only.** The plug-in file the submitter points at is fetched as text and parsed as JSON. Nothing a submitter provides is run, imported, installed or unpacked, and no image or archive is opened beyond the logo, which Starboard's own logo code rebuilds from the few drawing elements it allows (no scripts, links, styles or images inside it).
- **The fetch.** https only; no user name in the address; port 443; the name is resolved once and every answer must be a public address (private, loopback, link-local, metadata, multicast and reserved addresses are refused, including IPv4 inside IPv6), and the connection is made to that address; redirects only to github.com, raw.githubusercontent.com, codeload.github.com and objects.githubusercontent.com; 256 KB and 10 seconds at most.
- **The issue is text.** Workflows read the issue from the event file with Python, never through a shell, an expression or a script string. Each field is checked against a strict pattern, and shown in comments only after markdown, links, mentions and issue references are removed.
- **Approval is decided by GitHub.** The workflow that opens a pull request runs only when the label `approved` is added, and only if GitHub's API says the person who added it has admin, maintain or write permission. It checks again, and refuses if the plug-in file changed since the checks that a person read. A different job, with no way to write, reads the stranger's file; the job that can write takes back only files it checks again.
- **Workflows.** `permissions: {}` by default and the least for each job; every action pinned to a full commit hash; no `pull_request_target`; no secrets; the pull request's code runs with a read-only token. The workflows are checked with actionlint and zizmor.
- **A person merges.** A listing, and every daily refresh, arrives as a pull request. Merging is a person's decision.

## What a review checks

The [REVIEWING.md](REVIEWING.md) checklist: what the plug-in asks for against what it says it does; its licence; that its image is pinned by digest and comes from the maker's own repository or registry; the maker's repository; that no secrets are in it; its help; and where to report a problem.

## Limits

Reviewed means a person looked at one version on one date. It is not an audit. Starboard asks the person installing a plug-in before it is added, and runs it in a container with few rights.
