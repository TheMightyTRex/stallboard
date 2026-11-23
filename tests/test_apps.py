import copy
import json
import pathlib
import re
import shutil
import tempfile
import unittest

import helpers  # noqa: F401
from helpers import ROOT
import apps
import build
from test_build import TODAY, scratch_root

GOOD = {"id": "example-app", "name": "Example", "tagline": "Does one thing.", "summary": "", "checked_at": "2026-11-23",
        "sections": [{"id": "what", "heading": "What it is", "paragraphs": ["One."], "list": ["a", "b"], "links": []}],
        "links": [{"label": "Repository", "url": "https://github.com/example/example", "what": "The code"}]}


class Format(unittest.TestCase):
    def bad(self, mutate):
        d = copy.deepcopy(GOOD)
        mutate(d)
        with self.assertRaises(apps.AppError):
            apps.check(d)

    def test_good_and_refusals(self):
        self.assertEqual(apps.check(GOOD, "example-app.json")["name"], "Example")
        self.bad(lambda d: d.update(extra=1))
        self.bad(lambda d: d.update(id="Bad Id"))
        self.bad(lambda d: d["links"][0].update(url="http://example.com"))
        self.bad(lambda d: d["links"][0].update(url="javascript:alert(1)"))
        self.bad(lambda d: d["sections"][0].update(paragraphs=["x" * 901]))
        self.bad(lambda d: d.update(sections=[]))
        self.bad(lambda d: d.update(checked_at="today"))
        self.bad(lambda d: d["sections"].append(copy.deepcopy(d["sections"][0])))
        with self.assertRaises(apps.AppError):
            apps.check(GOOD, "other.json")

    def test_the_reelix_file_is_good_and_every_address_is_https(self):
        got = apps.load_all(ROOT / "data" / "apps")
        self.assertIn("reelix", got)
        r = got["reelix"]
        urls = {l["url"] for l in r["links"]}
        self.assertIn("https://discord.gg/pFfUx9tyvc", urls)
        self.assertIn("https://github.com/demonzoned/Reelix", urls)
        self.assertIn("https://github.com/TheMightyTRex/Reelix/issues", urls)
        self.assertTrue(all(u.startswith("https://") for u in urls))
        text = json.dumps(r)
        self.assertNotRegex(text, r"GPL|MIT licen|Apache")  # no licence is claimed
        self.assertIn("not made by the Reelix project", text)
        self.assertIn("has not endorsed", text)


class Site(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out = pathlib.Path(tempfile.mkdtemp()) / "site"
        cls.plugins, cls.warnings, cls.files = build.build(cls.out, TODAY)

    def test_the_page_the_nav_the_home_card_and_the_sitemap(self):
        page = (self.out / "reelix.html").read_text()
        self.assertIn("<h1 ", page)
        self.assertIn("An app Starboard works with, not a plug-in", page)
        self.assertEqual(page.count('<table class="table">'), 1)
        self.assertIn('aria-current="page">Reelix', page)
        self.assertNotRegex(page, r"(?<![\w-])(See|Look)\b")
        home = (self.out / "index.html").read_text()
        self.assertIn("Works with Starboard: Reelix", home)
        self.assertIn('href="reelix.html"', home)
        self.assertIn("reelix.html", (self.out / "sitemap.xml").read_text())
        self.assertIn('href="../reelix.html"', (self.out / "plugins" / "kavita.html").read_text())

    def test_the_catalogue_lists_apps_apart_from_plugins(self):
        cat = json.loads((self.out / "catalogue.json").read_text())
        self.assertEqual([a["id"] for a in cat["apps"]], ["reelix"])
        self.assertEqual(cat["apps"][0]["kind"], "app")
        self.assertNotIn("reelix", [p["id"] for p in cat["plugins"]])
        self.assertEqual(len(cat["plugins"]), 33)

    def test_a_second_app_is_just_another_file(self):
        def mutate(d):
            (d / "data" / "apps").mkdir(parents=True)
            shutil.copy(ROOT / "data" / "apps" / "reelix.json", d / "data" / "apps" / "reelix.json")
            (d / "data" / "apps" / "example-app.json").write_text(json.dumps(GOOD))
        d = scratch_root(["direct-play"], mutate)
        build.build(d / "site", TODAY, root=d)
        self.assertTrue((d / "site" / "example-app.html").exists())
        self.assertIn("Works with Starboard: Example", (d / "site" / "index.html").read_text())
        shutil.rmtree(d)
        build.R.APP_NAV[:] = []

    def test_hostile_app_text_is_escaped(self):
        evil = copy.deepcopy(GOOD)
        evil["sections"][0]["paragraphs"] = ['"><script>alert(1)</script>']
        evil["name"] = "<img src=x onerror=alert(1)>"
        html = __import__("pages").app_page(apps.check(evil))
        self.assertNotIn("<script>alert", html)
        self.assertNotIn("<img src=x", html)


if __name__ == "__main__":
    unittest.main()
