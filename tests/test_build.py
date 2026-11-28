import datetime as dt
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import helpers  # noqa: F401
from helpers import ROOT
import build
import manifest as mf

TODAY = dt.date(2026, 11, 23)
STARBOARD = pathlib.Path(os.environ.get("STARBOARD_SRC", "/nonexistent-set-STARBOARD_SRC"))
PLUGINS_CATALOGUE = pathlib.Path(os.environ.get("STARBOARD_PLUGINS_CATALOGUE", "/nonexistent"))


def scratch_root(ids, mutate=None):
    d = pathlib.Path(tempfile.mkdtemp())
    for sub in ("listings", "data/snapshots", "data/resources"):
        (d / sub).mkdir(parents=True)
    for i in ids:
        for sub in ("listings", "data/snapshots"):
            shutil.copy(ROOT / sub / f"{i}.json", d / sub / f"{i}.json")
        r = ROOT / "data" / "resources" / f"{i}.json"
        if r.exists():
            shutil.copy(r, d / "data" / "resources" / r.name)
    for f in ("starboard-releases.json", "starboard-screenshots.json"):
        shutil.copy(ROOT / "data" / f, d / "data" / f)
    shutil.copytree(ROOT / "assets", d / "assets")
    if mutate:
        mutate(d)
    return d


class RealSite(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = pathlib.Path(tempfile.mkdtemp()) / "site"
        cls.plugins, cls.warnings, cls.files = build.build(cls.out, TODAY)

    def test_every_page_is_made(self):
        self.assertEqual(len(self.plugins), 34)
        for name in ("index.html", "starboard.html", "reelix.html", "submit.html", "what-reviewed-means.html", "accessibility.html", "privacy.html", "404.html",
                     "catalogue.json", "sitemap.xml", "robots.txt"):
            self.assertTrue((self.out / name).exists(), name)
        for p in self.plugins:
            self.assertTrue((self.out / "plugins" / f"{p['id']}.html").exists())
            self.assertTrue((self.out / p["logo_file"]).exists(), p["id"])
        self.assertEqual(len(list((self.out / "category").glob("*.html"))), 9)  # eight categories and the index
        self.assertIn("https://themightytrex.github.io/stallboard/plugins/direct-play.html", (self.out / "sitemap.xml").read_text())

    def test_ai_assistants_is_a_category_that_stays_hidden_while_it_is_empty(self):
        """DASH-626: the category exists, with an icon from the sprite, but nothing is listed in it yet, so (as for every empty category)
        it has no page, no card on the index and no place in the rail, and a first listing makes all three."""
        import copy
        import render as R
        self.assertIn("AI assistants", mf.KINDS)
        self.assertEqual(list(R.KINDS), mf.KINDS)
        slug, ic, line = R.KINDS["AI assistants"]
        self.assertEqual((slug, ic), ("ai-assistants", "bot"))
        self.assertIn('id="i-bot"', R.SPRITE)
        self.assertIn("AI assistants", R.KIND_ABOUT)
        self.assertIn("with your own model or key", line)
        self.assertIn(".kind-ai-assistants", (ROOT / "assets" / "store.css").read_text())
        self.assertFalse((self.out / "category" / "ai-assistants.html").exists())
        self.assertNotIn("AI assistants", (self.out / "category" / "index.html").read_text())
        self.assertNotIn("ai-assistants", (self.out / "index.html").read_text())
        self.assertEqual([p["id"] for p in self.plugins if p["kind"] == "AI assistants"], [])
        first = copy.deepcopy(self.plugins[0])
        first["kind"] = "AI assistants"
        both = self.plugins + [first]
        index = R.category_index(both)
        self.assertIn('href="ai-assistants.html"', index)
        self.assertIn("These let you ask an assistant about your server", index)
        self.assertIn('href="category/ai-assistants.html"', R.rail(both, [], "all", 0, False))
        page = R.category_page("AI assistants", both)
        self.assertIn("<h1 id=\"hero-h\">AI assistants</h1>", page)
        self.assertIn('id="cat-list"', page)

    def test_the_home_page_lists_everything_without_a_script(self):
        t = (self.out / "index.html").read_text()
        self.assertEqual(len(re.findall(r'<li class="tile ', t.split('id="all-list"', 1)[1])), 34)
        self.assertIn("Start here", t)
        self.assertNotIn("data:image", t)

    def test_nothing_is_loaded_from_outside(self):
        for f in self.out.rglob("*.html"):
            t = f.read_text()
            for m in re.finditer(r'\b(?:src|srcset|data)=["\']([^"\']+)', t):
                self.assertFalse(re.match(r"^(https?:)?//", m.group(1)), f"{f.name}: {m.group(1)}")
            for m in re.finditer(r'<link[^>]+href=["\']([^"\']+)', t):
                self.assertFalse(re.match(r"^(https?:)?//", m.group(1)) and 'rel="canonical"' not in m.group(0), f"{f.name}: {m.group(1)}")
            self.assertNotRegex(t, r"url\(\s*https?:")
        for css in (self.out / "assets").glob("*.css"):
            self.assertNotRegex(css.read_text(), r"@import\s+url\(\s*['\"]?https?:")

    def test_words_follow_the_house_rules(self):
        """No contractions, no em dashes, never See or Look at the start of interface text, in the pages we write."""
        for name in ("index.html", "starboard.html", "reelix.html", "submit.html", "what-reviewed-means.html", "accessibility.html", "privacy.html", "404.html"):
            t = (self.out / name).read_text()
            text = re.sub(r"<(script|style|svg)\b.*?</\1>", " ", t, flags=re.S)
            text = re.sub(r"<[^>]+>", " ", text)
            text = text.replace("&#x27;", "'").replace("&amp;", "&")
            self.assertNotIn("—", text, name)
            self.assertNotRegex(text, r"\b(can't|won't|don't|doesn't|isn't|aren't|it's|that's|you're|you'll|we'll|we're|they're|couldn't|wouldn't|shouldn't|hasn't|haven't|didn't|let's)\b", name)
            self.assertNotRegex(text, r"(?:^|[.!?>]\s+)(See|Look)\b", name)
            self.assertNotRegex(text, r"\b(?:See|Look) (?:here|below|above|at)\b", name)

    def test_british_english_sentence_case_headings(self):
        for name in ("starboard.html", "submit.html", "what-reviewed-means.html", "accessibility.html", "privacy.html"):
            for h in re.findall(r"<h[1-3][^>]*>(.*?)</h[1-3]>", (self.out / name).read_text(), re.S):
                words = re.sub(r"<[^>]+>", "", h).split()
                caps = [w for w in words[1:] if w[:1].isupper() and w not in ("Starboard", "Stallboard", "Reviewed", "Starboard's", "Jellyfin", "Plug-in", "API", "GitHub", "Snaglist", "Linux", "Mint", "Debian", "Ubuntu", "Server", "Raspberry", "Pi", "OS", "Declared", "Measured")]
                self.assertFalse(caps, f"{name}: {h}")

    def test_the_catalogue_has_starboards_schema(self):
        cat = json.loads((self.out / "catalogue.json").read_text())
        self.assertEqual((cat["catalogue_version"], cat["name"]), (1, "Stallboard"))
        self.assertEqual(len(cat["plugins"]), 34)
        ref = json.loads(PLUGINS_CATALOGUE.read_text()) if PLUGINS_CATALOGUE.exists() else None
        for e in cat["plugins"]:
            self.assertRegex(e["id"], r"^[a-z0-9][a-z0-9-]{1,38}[a-z0-9]$")
            self.assertTrue(e["manifest"].startswith("https://") and e["published"] is True)
            self.assertTrue(e["versions"] and e["versions"][0]["version"] == e["version"])
            self.assertTrue(e["logo"].startswith("data:image/") and len(e["logo_alt"]) >= 3)
            self.assertIn(e["kind"], mf.KINDS)
        if ref:
            keys = set().union(*[set(x) for x in ref["plugins"]])
            for e in cat["plugins"]:
                self.assertFalse(set(e) - keys - {"rest"}, (e["id"], set(e) - keys))
        dp = next(e for e in cat["plugins"] if e["id"] == "direct-play")
        self.assertEqual(dp["rest"]["memory_mb"], 9)  # measured on the owner's server, 8.6 MB

    @unittest.skipUnless((STARBOARD / "starboard" / "plugins_admin.py").exists(), "needs a checkout of Starboard (STARBOARD_SRC)")
    def test_starboards_own_reader_accepts_the_catalogue(self):
        """Runs Starboard's real fetch_catalogue on the built catalogue.json, in a separate process."""
        code = f"""
import json, sys
sys.path.insert(0, {str(STARBOARD)!r})
from starboard import plugins_admin as pa, outside
raw = open({str(self.out / 'catalogue.json')!r}, 'rb').read()
class R:
    def __enter__(s): return s
    def __exit__(s, *a): pass
    def read(s, n=-1): return raw[:n] if n and n > 0 else raw
class O:
    def open(s, req, timeout=0): return R()
outside.check_url = lambda u: None
got = pa.fetch_catalogue("https://themightytrex.github.io/stallboard/catalogue.json", O())
print(json.dumps({{"name": got["name"], "n": len(got["items"]), "logos": sum(1 for i in got["items"] if i["logo"]), "rest": sum(1 for i in got["items"] if i["rest"]),
                  "versions": all(i["versions"] for i in got["items"]), "perms": sum(len(i["permissions"]) for i in got["items"]), "kinds": sorted({{i["kind"] for i in got["items"]}}),
                  "size": len(raw)}}))
"""
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr[-800:])
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual((got["name"], got["n"], got["logos"]), ("Stallboard", 33, 33))  # the apps array and the starboard key are ignored, not installed as plug-ins
        self.assertTrue(got["versions"])
        self.assertLess(got["size"], 256 * 1024)

    @unittest.skipUnless((STARBOARD / "starboard" / "plugins_admin.py").exists(), "needs a checkout of Starboard (STARBOARD_SRC)")
    def test_starboard_refuses_a_file_that_differs_from_the_listed_hash(self):
        """Starboard's real fetch_manifest, given the catalogue's manifest_sha256: the same file is used, another is refused."""
        e = next(x for x in json.loads((self.out / "catalogue.json").read_text())["plugins"] if x["id"] == "direct-play")
        raw = json.dumps({"manifest_version": 1}).encode()
        code = f"""
import sys, hashlib
sys.path.insert(0, {str(STARBOARD)!r})
from starboard import plugins_admin as pa, outside
outside.check_url = lambda u: None
raw = {raw!r}
class R:
    def __enter__(s): return s
    def __exit__(s, *a): pass
    def read(s, n=-1): return raw
class O:
    def open(s, req, timeout=0): return R()
good = hashlib.sha256(raw).hexdigest()
pa.fetch_manifest({e["manifest"]!r}, O(), good)
try:
    pa.fetch_manifest({e["manifest"]!r}, O(), {e["versions"][0]["manifest_sha256"]!r})
    print("ACCEPTED")
except ValueError as err:
    print("REFUSED", err)
"""
        r = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True, timeout=60)
        self.assertIn("REFUSED The file changed since the catalogue listed it", r.stdout + r.stderr)

    def test_each_plugin_page_has_the_new_sections(self):
        t = (self.out / "plugins" / "direct-play.html").read_text()
        self.assertIn("What it uses", t)
        self.assertIn("Memory at rest", t)
        self.assertIn("About 8.6 MB", t)
        self.assertRegex(t, r"Needs Starboard 0\.\d+ or later")
        self.assertIn("../starboard.html#plugin-api", t)
        self.assertIn("Report a problem with this plug-in", t)
        self.assertIn("https://themightytrex.github.io/starboard-plugins/help/plugins/direct-play/index.html", t)
        t2 = (self.out / "plugins" / "kavita.html").read_text()
        self.assertIn("Not measured yet", t2)
        self.assertIn("Maker", t2)  # the figure from the maker, labelled as such
        self.assertIn("not measured by the reviewer", t2)

    def test_the_page_for_a_plugin_nobody_measured_invents_nothing(self):
        t = (self.out / "plugins" / "audio-description.html").read_text()
        self.assertIn("Not measured yet", t)
        self.assertIn("Memory use not measured yet", t)  # nothing from a real server
        self.assertIn("Measured on a test server with made-up data", t)  # the test-server figures are labelled as such

    def test_page_weight(self):
        import gzip
        t = (self.out / "index.html").read_bytes()
        self.assertLess(len(gzip.compress(t)), 30_000)
        self.assertNotIn(b"base64", t)


class Hostile(unittest.TestCase):
    def test_hostile_text_is_escaped_on_every_page(self):
        xss = '"><script>alert(1)</script><img src=x onerror=alert(2)>'

        def mutate(d):
            p = d / "data" / "snapshots" / "direct-play.json"
            s = json.loads(p.read_text())
            m = s["manifest_data"]
            m["name"] = xss[:40]
            m["description"] = xss
            m["author"] = xss
            m["homepage"] = "javascript:alert(1)"
            m["support_url"] = 'https://example.com/"onmouseover="alert(3)'
            m["versions"] = [{"version": xss[:30], "date": "2026-11-23", "groups": [["Added", [xss]]]}]
            s["manifest_data"] = m
            p.write_text(json.dumps(s))
            lp = d / "listings" / "direct-play.json"
            lj = json.loads(lp.read_text())
            lj["notes"] = xss[:500]
            lj["help"] = "https://example.com/" + "a" * 50
            lp.write_text(json.dumps(lj))
        d = scratch_root(["direct-play", "kavita"], mutate)
        out = d / "site"
        build.build(out, TODAY, root=d)
        for f in out.rglob("*.html"):
            t = f.read_text()
            self.assertNotIn("<script>alert", t, f.name)
            self.assertNotIn("<img src=x", t, f.name)
            self.assertNotIn('onmouseover="alert', t, f.name)
            self.assertNotIn('href="javascript:', t, f.name)
        shutil.rmtree(d)

    def test_a_stale_snapshot_is_left_out_and_said(self):
        d = scratch_root(["direct-play", "kavita"])
        plugins, warnings, files = build.build(d / "site", TODAY + dt.timedelta(days=20), root=d)
        self.assertEqual(plugins, [])
        self.assertTrue(any("LEFT OUT" in w and "20 days old" in w for w in warnings))
        _, warnings, _ = build.build(d / "site", TODAY + dt.timedelta(days=10), root=d)
        self.assertEqual([w for w in warnings if "LEFT OUT" in w], [])
        shutil.rmtree(d)

    def test_a_listing_with_no_snapshot_or_a_failing_manifest_is_left_out(self):
        def mutate(d):
            (d / "data" / "snapshots" / "kavita.json").unlink()
            p = d / "data" / "snapshots" / "direct-play.json"
            s = json.loads(p.read_text())
            s["problems"] = ["Missing field licence"]
            p.write_text(json.dumps(s))
        d = scratch_root(["direct-play", "kavita"], mutate)
        plugins, warnings, _ = build.build(d / "site", TODAY, root=d)
        self.assertEqual(plugins, [])
        self.assertEqual(len([w for w in warnings if "left out" in w.lower()]), 2)
        shutil.rmtree(d)

    def test_a_broken_listing_stops_the_build_and_says_which(self):
        d = scratch_root(["direct-play"], lambda d: (d / "listings" / "direct-play.json").write_text('{"id": "direct-play"}'))
        with self.assertRaises(Exception) as cm:
            build.build(d / "site", TODAY, root=d)
        self.assertIn("direct-play.json", str(cm.exception))
        shutil.rmtree(d)

    def test_warnings_cannot_start_a_workflow_command(self):
        self.assertNotIn("::", build.safe_line("::set-output name=x::y\n::error::bad"))
        self.assertNotIn("\n", build.safe_line("a\nb\r\nc"))

    def test_the_build_makes_no_requests(self):
        import socket
        orig = socket.socket.connect

        def no(*a, **k):
            raise AssertionError("the build tried to use the network")
        socket.socket.connect = no
        try:
            d = scratch_root(["direct-play"])
            build.build(d / "site", TODAY, root=d)
            shutil.rmtree(d)
        finally:
            socket.socket.connect = orig


if __name__ == "__main__":
    unittest.main()
