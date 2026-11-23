import copy
import datetime as dt
import json
import unittest

import helpers  # noqa: F401
from helpers import ROOT
import listing as lst
import manifest as mf

BASE = {"id": "example-plug-in", "name": "Example", "manifest": "https://raw.githubusercontent.com/example/example/0123456789abcdef0123456789abcdef01234567/starboard-plugin.json", "maker": "Example Maker",
        "listed_at": "2026-11-23", "reviewed": {"by": "TheMightyTRexUK", "at": "2026-11-23", "version": "1.0.0"}}


class Format(unittest.TestCase):
    def bad(self, **kw):
        d = copy.deepcopy(BASE)
        for k, v in kw.items():
            if v is KeyError:
                d.pop(k)
            else:
                d[k] = v
        with self.assertRaises(lst.ListingError, msg=str(kw)):
            lst.check(d)

    def test_a_good_listing(self):
        out = lst.check(BASE, "example-plug-in.json")
        self.assertEqual(out["reviewed"]["by"], "TheMightyTRexUK")
        self.assertFalse(lst.is_own(out))
        self.assertFalse(lst.is_own(out | {"maker": "TheMightyTRexUK"}))  # the name alone never gives the mark
        self.assertTrue(lst.is_own(lst.check(dict(BASE, own=True))))

    def test_refusals(self):
        self.bad(id="Bad Id")
        self.bad(id="x")
        self.bad(unknown=1)
        self.bad(name=KeyError)
        self.bad(manifest="http://example.com/x.json")
        self.bad(manifest="https://169.254.169.254/x.json")
        self.bad(manifest="https://raw.githubusercontent.com/example/example/main/starboard-plugin.json")
        self.bad(manifest="https://example.com/0123456789abcdef0123456789abcdef01234567/x.json")
        self.bad(own="yes")
        self.bad(maker="a" * 61)
        self.bad(maker="line\nbreak")
        self.bad(listed_at="23/11/2026")
        self.bad(reviewed={"by": "x", "at": "2026-11-23"})
        self.bad(reviewed={"by": "x", "at": "2026-11-23", "version": "latest"})
        self.bad(kind="Made up")
        self.bad(help="javascript:alert(1)")
        self.bad(recommended="yes")
        self.bad(notes="n" * 501)
        self.bad(pitch="p" * 111)
        self.bad(older_versions=[{"version": "1.0.0", "manifest": "http://x"}])
        with self.assertRaises(lst.ListingError):
            lst.check(BASE, "other.json")
        with self.assertRaises(lst.ListingError):
            lst.check([])

    def test_figures_from_a_maker_must_be_real_numbers(self):
        for fig in ({"memory_mib": -1}, {"memory_mib": 1e12}, {"memory_mib": "24"}, {"memory_mib": True}, {"memory_mib": float("nan")}, {"memory_mib": float("inf")},
                    {"memory_mib": 20, "cpu_percent": -3}, {"memory_mib": 20, "cpu_percent": 10 ** 9}, {"memory_mib": 20, "extra": 1}, {"memory_mib": "9" * 10000}, [], "20"):
            self.bad(maker_figures=fig)
        self.assertEqual(lst.check(dict(BASE, maker_figures={"memory_mib": 24, "cpu_percent": 0.1}))["maker_figures"], {"memory_mib": 24, "cpu_percent": 0.1})


class Committed(unittest.TestCase):
    def test_every_listing_is_valid_and_has_a_real_review(self):
        listings = lst.load_all(ROOT / "listings")
        self.assertGreaterEqual(len(listings), 33)
        for lid, l in listings.items():
            self.assertEqual(l["reviewed"]["by"], "TheMightyTRexUK")
            self.assertTrue(l["own"])
            self.assertEqual(l["reviewed"]["at"], l["listed_at"])
            self.assertLessEqual(dt.date.fromisoformat(l["listed_at"]), dt.date.today())
            self.assertTrue(l["help"].startswith("https://themightytrex.github.io/starboard-plugins/help/plugins/" + lid + "/"))
            snap = mf.load_snapshot(ROOT / "data" / "snapshots" / f"{lid}.json")
            self.assertEqual(snap["manifest"], l["manifest"])
            self.assertEqual(l["reviewed"]["version"], snap["manifest_data"]["version"])
            self.assertIn(l["kind"], mf.KINDS)


if __name__ == "__main__":
    unittest.main()
