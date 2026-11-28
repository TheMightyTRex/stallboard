import json
import pathlib
import re
import tempfile
import unittest

import helpers  # noqa: F401
import storefront as sf

ROOT = helpers.ROOT
GOOD = {"summary": "Does one thing well.", "does": ["It does a thing that people want, and it tells them when it is done."], "for": "People who want the thing.",
        "needs": "Nothing else.", "shows": "A card on the dashboard.", "tags": ["backups", "fire tv"], "media_servers": ["jellyfin"], "media_servers_basis": "api"}


class Rules(unittest.TestCase):
    def bad(self, **kw):
        with self.assertRaises(sf.StorefrontError):
            sf.check("x", {**GOOD, **kw})

    def test_good(self):
        self.assertEqual(sf.check("x", GOOD)["tags"], ["backups", "fire tv"])

    def test_the_writing_rules(self):
        self.bad(summary="It’s a dash — here.")
        self.bad(**{"for": "People who do not want to look at logs."})
        self.bad(shows="It doesn't hide.")
        self.bad(summary="x" * 141)
        self.bad(tags=["Upper"])
        self.bad(does=[])
        self.bad(media_servers=[])
        self.bad(media_servers=["kodi"])
        self.bad(media_servers_basis="guess")

    def test_shots_need_a_file_and_alt_text(self):
        with tempfile.TemporaryDirectory() as d:
            d = pathlib.Path(d)
            (d / "assets" / "p").mkdir(parents=True)
            (d / "assets" / "p" / "a.webp").write_bytes(b"x")
            (d / "shots.json").write_text(json.dumps({"plugins": {"p": [
                {"file": "a.webp", "alt": "A picture with a long enough description"}, {"file": "gone.webp", "alt": "A picture with a long enough description"},
                {"file": "a.webp", "alt": "short"}]}}))
            got = sf.load_shots(d / "shots.json", d / "assets")
            self.assertEqual([x["file"] for x in got["p"]], ["assets/shots/p/a.webp"])


class RealData(unittest.TestCase):
    def test_every_file_passes(self):
        self.assertEqual(len(sf.load_all(ROOT / "data" / "storefront")), 34)

    def test_site_has_category_pages_search_and_sections(self):
        import build
        import datetime as dt
        with tempfile.TemporaryDirectory() as d:
            plugins, _, files = build.build(d, dt.date(2026, 11, 25))
            idx = files["category/index.html"]
            self.assertEqual(idx.count('class="cat kind-'), 8)
            cat = files["category/jellyfin.html"]
            self.assertIn('role="search"', cat)
            self.assertIn('role="status"', cat)
            self.assertIn('aria-label="Breadcrumb"', cat)
            page = files["plugins/direct-play.html"]
            for h in ("Who it is for", "What you will see", "System tags", "At a glance", "More in Jellyfin"):
                self.assertIn(h, page)
            self.assertIn('href="../category/jellyfin.html"', page)
            home = files["index.html"]
            self.assertIn('href="category/jellyfin.html"', home)
            self.assertEqual(len(re.findall(r'data-search="', home.split('id="all-list"', 1)[1])), 34)

    def test_media_server_chips(self):
        import build
        import datetime as dt
        with tempfile.TemporaryDirectory() as d:
            plugins, _, files = build.build(d, dt.date(2026, 11, 25))
            by = {p["id"]: p for p in plugins}
            self.assertEqual(by["direct-play"]["media"], ["jellyfin"])
            self.assertEqual(by["styles"]["media"], ["jellyfin", "plex", "emby"])
            tdarr = files["plugins/tdarr.html"]
            self.assertIn('aria-label="Works with Jellyfin, Plex and Emby"', tdarr)
            self.assertIn('aria-label="Works with Jellyfin only"', files["plugins/direct-play.html"])
            home = files["index.html"].split('id="all-list"', 1)[1]
            self.assertEqual(len(re.findall(r'class="chiprow media-chips"', home)), 34)
            self.assertIn('name="media"', files["index.html"])
            self.assertIn('name="media"', files["category/network.html"])
            cat = json.loads((pathlib.Path(d) / "catalogue.json").read_text())
            self.assertEqual(len(cat["media_servers"]), 34)
            self.assertEqual(cat["media_servers"]["direct-play"], ["jellyfin"])


class Shelf(unittest.TestCase):
    """The Shelf design: poster cards of one shape, a rail with Works with first, a facts strip, a fallback for a missing logo."""

    @classmethod
    def setUpClass(cls):
        import build
        import datetime as dt
        cls.d = tempfile.TemporaryDirectory()
        cls.plugins, _, cls.files = build.build(cls.d.name, dt.date(2026, 11, 25))

    @classmethod
    def tearDownClass(cls):
        cls.d.cleanup()

    def test_every_card_has_the_same_parts_and_at_most_three_chips(self):
        cards = self.files["index.html"].split('id="all-list"', 1)[1].split('<li class="tile ')[1:]
        self.assertEqual(len(cards), 34)
        for c in cards:
            self.assertEqual(c.count('class="tile__art"'), 1)
            self.assertEqual(c.count('class="tile__pitch"'), 1)
            self.assertEqual(c.count('class="tile__need"'), 1)
            self.assertLessEqual(c.count('class="chip '), 3)

    def test_a_plugin_without_a_logo_gets_a_lettered_tile_not_a_broken_picture(self):
        import render
        p = dict(next(x for x in self.plugins if x["id"] == "styles"), logo_bytes=b"", logo_file="assets/logo/no-logo.svg")
        t = render.tile(p, 0)
        self.assertIn("plate--mono", t)
        self.assertNotIn("<img", t)

    def test_the_filters_put_works_with_first(self):
        f = self.files["index.html"].split('id="filters"', 1)[1]
        self.assertLess(f.index("Works with"), f.index("The Starboard you have"))
        self.assertLess(f.index("Works with"), f.index("Sort by"))
        self.assertIn('id="filters-open"', self.files["index.html"])
        self.assertIn('id="active"', self.files["category/jellyfin.html"])

    def test_the_plugin_page_has_a_facts_strip_and_more_in_the_category(self):
        page = self.files["plugins/direct-play.html"]
        strip = page.split('class="strip"', 1)[1].split("</dl>", 1)[0]
        for w in ("Reviewed", "Works with", "Starboard", "Memory use"):
            self.assertIn(f"<dt>{w}</dt>", strip)
        self.assertEqual(len(re.findall(r'<li class="tile ', page.split('id="more-h"', 1)[1])), 4)

    def test_the_spacing_tokens_are_defined(self):
        import helpers as h
        css = (h.ROOT / "assets" / "store.css").read_text()
        for i in range(1, 10):
            self.assertIn(f"--sp-{i}:", css)
