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
        self.assertEqual(len(sf.load_all(ROOT / "data" / "storefront")), 33)

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
            for h in ("Who it is for", "What you will see", "System tags", "Category: Jellyfin"):
                self.assertIn(h, page)
            home = files["index.html"]
            self.assertIn('href="category/jellyfin.html"', home)
            self.assertEqual(len(re.findall(r'data-search="', home.split('id="all-list"', 1)[1])), 33)

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
            self.assertEqual(len(re.findall(r'class="chiprow media-chips"', home)), 33)
            self.assertIn('id="media"', files["index.html"])
            self.assertIn('id="media"', files["category/network.html"])
            cat = json.loads((pathlib.Path(d) / "catalogue.json").read_text())
            self.assertEqual(len(cat["media_servers"]), 33)
            self.assertEqual(cat["media_servers"]["direct-play"], ["jellyfin"])
