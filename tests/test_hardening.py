import base64
import json
import pathlib
import re
import shutil
import tempfile
import unittest

import helpers  # noqa: F401
from helpers import ROOT
import build
import manifest as mf
import refresh_snapshots as rf
import safefetch
from test_build import TODAY, scratch_root
from test_manifest import RAW, fetcher


def deep_svg(n):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10">' + "<g>" * n + '<rect width="1" height="1"/>' + "</g>" * n + "</svg>").encode()


class Logos(unittest.TestCase):
    def test_a_deeply_nested_logo_is_a_plain_refusal_never_a_crash(self):
        for n in (60, 5000, 200000):
            with self.assertRaises(ValueError):
                mf.clean_logo(deep_svg(n), "logo.svg")
        data, ctype = mf.clean_logo(deep_svg(3), "logo.svg")
        self.assertEqual(ctype, "image/svg+xml")

    def test_make_snapshot_survives_a_deep_logo_and_a_deep_manifest(self):
        m = dict(RAW, logo={"file": "logo.svg", "alt": "A logo"})
        s = mf.make_snapshot("https://example.com/x/starboard-plugin.json", fetch=fetcher(m, deep_svg(100000)))
        self.assertEqual(s["logo"], "")
        self.assertTrue(s["logo_note"])
        with self.assertRaises(ValueError):
            mf.make_snapshot("https://example.com/x.json", fetch=lambda url, **k: b'{"a":' * 200000 + b"1" + b"}" * 200000)

    def test_the_build_cleans_a_logo_again_before_writing_it(self):
        evil = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><script>alert(1)</script><rect width="10" height="10"/></svg>'

        def mutate(d):
            p = d / "data" / "snapshots" / "direct-play.json"
            s = json.loads(p.read_text())
            s["logo"] = "data:image/svg+xml;base64," + base64.b64encode(evil).decode()
            p.write_text(json.dumps(s))
        d = scratch_root(["direct-play", "kavita"], mutate)
        plugins, warnings, _ = build.build(d / "site", TODAY, root=d)
        self.assertEqual(len(plugins), 2)
        self.assertTrue(any("logo failed" in w for w in warnings))
        for f in (d / "site" / "assets" / "logos").iterdir():
            self.assertNotIn(b"script", f.read_bytes())
        entry = next(e for e in json.loads((d / "site" / "catalogue.json").read_text())["plugins"] if e["id"] == "direct-play")
        self.assertNotIn("logo", entry)
        shutil.rmtree(d)

    def test_a_broken_snapshot_leaves_that_listing_out_and_the_others_stay(self):
        d = scratch_root(["direct-play", "kavita"], lambda d: (d / "data" / "snapshots" / "direct-play.json").write_text("{not json"))
        plugins, warnings, _ = build.build(d / "site", TODAY, root=d)
        self.assertEqual([p["id"] for p in plugins], ["kavita"])
        self.assertTrue(any("broken" in w for w in warnings))
        shutil.rmtree(d)


class Refresh(unittest.TestCase):
    def test_the_report_cannot_carry_markup_links_or_mentions(self):
        hostile = "@everyone [x](https://evil.example.com) <script>alert(1)</script> www.evil.example.com ``` # 1"
        old = mf.trim(RAW)
        new = mf.trim(dict(RAW, version="2.0.0", permissions=["system:read"], starboard_api=">=1.14 <2.0"))
        new["permissions"] = ["system:read"]
        new["version"] = hostile
        new["containers"] = [dict(new["containers"][0], image=hostile)]
        text = "; ".join(rf.diff(old, new)) + rf.line(hostile)
        for bad in ("@everyone", "](https", "<script", "www.", "```"):
            self.assertNotIn(bad, text)

    def test_one_makers_failure_never_stops_the_others(self):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "data" / "snapshots").mkdir(parents=True)
        (d / "listings").mkdir()
        for i in ("direct-play", "kavita"):
            shutil.copy(ROOT / "listings" / f"{i}.json", d / "listings")
            shutil.copy(ROOT / "data" / "snapshots" / f"{i}.json", d / "data" / "snapshots")
        calls = []
        orig_root, orig_make = rf.ROOT, rf.mf.make_snapshot

        def make(url, **k):
            calls.append(url)
            if "direct-play" in url:
                raise RecursionError("hostile")
            raise safefetch.FetchError("The address answered with the error 500")
        rf.ROOT, rf.mf.make_snapshot = d, make
        try:
            rf.main(set())
        finally:
            rf.ROOT, rf.mf.make_snapshot = orig_root, orig_make
        self.assertEqual(len(calls), 2)
        report = (d / "data" / "refresh-report.md").read_text()
        self.assertIn("direct-play: not refreshed", report)
        self.assertIn("kavita: not refreshed", report)
        shutil.rmtree(d)

    def test_a_pull_request_only_when_the_file_changed_or_is_old(self):
        import datetime as dt
        d = pathlib.Path(tempfile.mkdtemp())
        shutil.copy(ROOT / "data" / "snapshots" / "kavita.json", d / "kavita.json")
        snap = mf.load_snapshot(d / "kavita.json")
        l = json.loads((ROOT / "listings" / "kavita.json").read_text())
        same = dict(snap, fetched_at="2026-11-23T10:00Z")
        orig = rf.mf.make_snapshot
        rf.mf.make_snapshot = lambda url, **k: same
        try:
            fresh = dt.date.fromisoformat(snap["fetched_at"][:10])
            self.assertIsNone(rf.one("kavita", l, d, fresh))  # same hash, read lately: nothing to review
            old = fresh + dt.timedelta(days=9)
            self.assertIn("date moved only", rf.one("kavita", l, d, old))
            changed = dict(snap, sha256="f" * 64)
            rf.mf.make_snapshot = lambda url, **k: changed
            self.assertIn("the file changed since it was reviewed", rf.one("kavita", l, d, fresh))
        finally:
            rf.mf.make_snapshot = orig
        shutil.rmtree(d)


class Catalogue(unittest.TestCase):
    def test_every_entry_carries_the_hash_of_the_file_that_was_reviewed(self):
        plugins, _, _ = build.build(pathlib.Path(tempfile.mkdtemp()) / "s", TODAY)
        cat = build.catalogue(plugins, {"latest": None}, TODAY)
        by = {p["id"]: p for p in plugins}
        for e in cat["plugins"]:
            self.assertEqual(e["versions"][0]["manifest_sha256"], by[e["id"]]["sha256"])
            self.assertRegex(e["versions"][0]["manifest_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(e["manifest"], r"/[0-9a-f]{40}/")

    def test_the_snapshot_hash_is_the_hash_of_the_bytes_fetched(self):
        import hashlib
        s = mf.make_snapshot("https://example.com/x.json", fetch=fetcher(RAW))
        self.assertEqual(s["sha256"], hashlib.sha256(json.dumps(RAW).encode()).hexdigest())


class OwnMark(unittest.TestCase):
    def test_the_mark_comes_from_the_listing_field_not_the_maker_name(self):
        def mutate(d):
            p = d / "listings" / "kavita.json"
            l = json.loads(p.read_text())
            l["own"] = False  # the maker string still says TheMightyTRexUK
            p.write_text(json.dumps(l))
        d = scratch_root(["direct-play", "kavita"], mutate)
        build.build(d / "site", TODAY, root=d)
        self.assertIn("Starboard's own", (d / "site" / "plugins" / "direct-play.html").read_text().replace("&#x27;", "'"))
        self.assertNotIn("Starboard's own", (d / "site" / "plugins" / "kavita.html").read_text().replace("&#x27;", "'"))
        shutil.rmtree(d)


class Pages(unittest.TestCase):
    def test_every_page_has_a_content_security_policy_and_no_style_attributes(self):
        d = pathlib.Path(tempfile.mkdtemp()) / "s"
        build.build(d, TODAY)
        for f in d.rglob("*.html"):
            if "assets" in f.relative_to(d).parts:
                continue
            t = f.read_text()
            m = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', t)
            self.assertTrue(m, f.name)
            for part in ("default-src 'self'", "img-src 'self' data:", "style-src 'self'", "script-src 'self'"):
                self.assertIn(part, m.group(1))
            self.assertNotIn("unsafe-inline", m.group(1))
            self.assertIsNone(re.search(r"<[a-z]+[^>]*\sstyle=", t), f.name)
            self.assertNotRegex(t, r"<script(?![^>]*\ssrc=)[^>]*>")  # no inline script

    def test_the_repository_names_no_server_and_no_local_path(self):
        words = ["T-Rex-" + "Server", "/mnt/" + "pool", "/home/" + "davidtrex"]
        for p in ROOT.rglob("*"):
            if not p.is_file() or any(x in p.parts for x in (".git", "site", "reports", "__pycache__")) or p.suffix in (".png", ".jpg", ".woff2") or p.name == "snaglist.js":
                continue
            try:
                t = p.read_text()
            except UnicodeDecodeError:
                continue
            for w in words:
                self.assertNotIn(w, t, f"{p.relative_to(ROOT)} names {w}")


if __name__ == "__main__":
    unittest.main()
