import json
import tempfile
import unittest
import pathlib

import helpers  # noqa: F401
from helpers import ROOT
import resources as rs

C = {"container": "plugin-x-main", "memory_mib_median": 24.5, "memory_mib_max": 24.6, "cpu_percent_median": 0.0, "memory_limit_mib": 192, "cpus_limit": 0.5, "pids_limit": 64, "image_size_mb": 25.0}
F = {"plugin": "x", "measured_at": "2026-11-23T16:41+00:00", "how": "docker stats", "containers": [C]}


class Clean(unittest.TestCase):
    def test_good(self):
        out = rs.clean(F)
        self.assertEqual(rs.measured_totals(out)["memory"], 24.5)

    def test_hostile_figures_are_dropped_not_repaired(self):
        for key, v in [("memory_mib_median", -5), ("memory_mib_median", "24"), ("memory_mib_median", float("nan")), ("memory_mib_median", float("inf")),
                       ("memory_mib_median", 10 ** 12), ("memory_mib_median", True), ("memory_mib_median", None), ("memory_mib_median", [1]), ("memory_mib_median", "9" * 100000)]:
            bad = dict(F, containers=[dict(C, **{key: v})])
            self.assertIsNone(rs.clean(bad), (key, v))
        out = rs.clean(dict(F, containers=[dict(C, cpu_percent_median=-1, image_size_mb="big", cpus_limit=10 ** 9)]))
        self.assertNotIn("cpu_percent_median", out["containers"][0])
        self.assertNotIn("image_size_mb", out["containers"][0])
        self.assertNotIn("cpus_limit", out["containers"][0])

    def test_hostile_text_and_shapes(self):
        out = rs.clean(dict(F, how="<script>alert(1)</script>" + "x" * 5000, plugin="p" * 500))
        self.assertLessEqual(len(out["how"]), 400)
        self.assertLessEqual(len(out["plugin"]), 40)
        for bad in (None, [], "x", {}, dict(F, measured_at="soon"), dict(F, containers="x"), dict(F, containers=[5]), dict(F, containers=[])):
            self.assertIsNone(rs.clean(bad))

    def test_a_partial_total_is_not_shown(self):
        two = rs.clean(dict(F, containers=[C, {"container": "b", "memory_mib_median": 3}]))
        t = rs.measured_totals(two)
        self.assertEqual(t["memory"], 27.5)
        self.assertIsNone(t["cpu"])
        self.assertIsNone(t["image"])

    def test_committed_measurements_are_clean(self):
        got = rs.load_all(ROOT / "data" / "resources")
        self.assertTrue({"direct-play", "tv-station", "remote-access", "picture-shrinker"} <= set(got))
        self.assertEqual(len(got["on-demand"]["containers"]), 2)
        for k, v in got.items():
            self.assertIn("docker stats", v["how"])


class Words(unittest.TestCase):
    def test_one_line(self):
        meas = rs.measured_totals(rs.clean(F))
        self.assertEqual(rs.short_line(meas, None), "About 24 MB of memory at rest")
        self.assertEqual(rs.short_line(None, {"memory_mib": 117, "cpu_percent": 0.2}), "Maker says about 117 MB of memory at rest")
        self.assertEqual(rs.short_line(None, None), "Memory use not measured yet")
        self.assertEqual(rs.rest_memory(meas, {"memory_mib": 9, "cpu_percent": 0}), (24.5, "measured"))
        self.assertEqual(rs.rest_memory(None, None), (None, None))

    def test_declared_uses_starboards_default_and_says_so(self):
        d = rs.declared({"containers": [{"name": "main"}], "resources": {}})
        self.assertEqual((d["memory_mb"], d["default_used"]), (128, True))
        d = rs.declared({"containers": [{"name": "main"}], "resources": {"main": {"memory": 512, "cpus": 1.0, "pids": 64}}})
        self.assertEqual((d["memory_mb"], d["cpus"], d["pids"], d["default_used"]), (512, 1.0, 64, False))
        self.assertIsNone(rs.declared({"containers": []})["memory_mb"])


if __name__ == "__main__":
    unittest.main()
