import unittest

import helpers  # noqa: F401
from helpers import ROOT
import releases as rl

REL = [{"version": "0.20.0", "api": "1.12.0"}, {"version": "0.22.0", "api": "1.14.0"}, {"version": "0.26.1", "api": "1.17.0"}, {"version": "0.29.0", "api": "1.17.0"}]


class Ranges(unittest.TestCase):
    def test_satisfies(self):
        self.assertTrue(rl.satisfies("1.14.0", ">=1.14 <2.0"))
        self.assertFalse(rl.satisfies("1.13.0", ">=1.14 <2.0"))
        self.assertFalse(rl.satisfies("2.0.0", ">=1.14 <2.0"))
        for bad in ("", "latest", ">=x", ">=1.2.3.4", None):
            self.assertFalse(rl.satisfies("1.14.0", bad))
        self.assertFalse(rl.satisfies("nonsense", ">=1.0"))

    def test_needs(self):
        self.assertEqual(rl.needs(">=1.14 <2.0", REL)["first"], "0.22")
        self.assertEqual(rl.needs(">=1.17 <2.0", REL)["first"], "0.26")
        self.assertFalse(rl.needs(">=1.14 <2.0", REL)["limited"])
        n = rl.needs(">=1.12 <1.15", REL)
        self.assertEqual((n["first"], n["newest"], n["limited"]), ("0.20", "0.22", True))
        self.assertIsNone(rl.needs(">=1.30", REL)["first"])
        self.assertIsNone(rl.needs("garbage", REL)["first"])

    def test_the_real_data(self):
        rels = rl.load(ROOT / "data" / "starboard-releases.json")
        self.assertGreater(len(rels), 5)
        self.assertEqual(rl.load(ROOT / "data" / "nothing.json"), [])
        self.assertTrue(all(rl.ver(r["version"]) for r in rels))


if __name__ == "__main__":
    unittest.main()
