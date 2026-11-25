import datetime as dt
import json
import pathlib
import tempfile
import unittest

import helpers  # noqa: F401
from helpers import ROOT
import testbench as tb
import measure_plugins as mp

REC = {"plugin": "x", "measured_at": "2026-11-26T10:00+00:00", "environment": {"kind": "test server, made-up data", "starboard_version": "0.30.0", "machine": "Linux x86_64, 4 cores"},
       "containers": [{"container": "plugin-x-main", "memory_mib_start": 12.5, "memory_mib_used": 20.1, "cgroup_mib_start": 11.9, "cgroup_mib_used": 19.0, "cpu_percent_60s": 0.2, "image_size_mb": 90}]}


class Loader(unittest.TestCase):
    def test_good_and_totals(self):
        t = tb.clean(REC)
        x = tb.totals(t)
        self.assertEqual((x["memory_start"], x["memory_used"], x["count"]), (12.5, 20.1, 1))
        self.assertEqual(tb.sort_memory(t), 20.1)

    def test_no_container(self):
        t = tb.clean({"plugin": "styles", "measured_at": "2026-11-26", "no_container": True})
        self.assertTrue(t["no_container"])
        self.assertIsNone(tb.totals(t))
        self.assertEqual(tb.sort_memory(t), 0.0)

    def test_bad_figures_are_dropped(self):
        for k, v in [("memory_mib_start", -1), ("memory_mib_start", "9"), ("memory_mib_start", float("nan")), ("memory_mib_start", True), ("memory_mib_start", 10 ** 9)]:
            bad = dict(REC, containers=[{"container": "c", k: v}])
            self.assertIsNone(tb.clean(bad), (k, v))
        t = tb.clean(dict(REC, containers=[dict(REC["containers"][0], cpu_percent_60s="lots")]))
        self.assertNotIn("cpu_percent_60s", t["containers"][0])
        for bad in (None, [], {}, dict(REC, measured_at="soon"), dict(REC, containers=[])):
            self.assertIsNone(tb.clean(bad))

    def test_partial_sum_is_not_shown(self):
        t = tb.clean(dict(REC, containers=[REC["containers"][0], {"container": "b", "memory_mib_start": 3}]))
        self.assertIsNone(tb.totals(t)["memory_used"])
        self.assertEqual(tb.totals(t)["memory_start"], 15.5)

    def test_real_files_load(self):
        self.assertIn("styles", tb.load_all(ROOT / "data" / "resources-test"))


class FakeDocker:
    def __init__(self):
        self.calls = []

    def names(self):
        return ["plugin-direct-play-main", "plugin-jellystat-db", "other-thing"][:2]

    def stats(self, names):
        return {n: (10.0 if "direct" in n else 200.0, 0.5) for n in names}

    def inspect(self, n):
        return {"Id": "ab" * 32, "Image": "sha256:" + "c" * 64}

    def image_mb(self, i):
        return 73.5


class Measuring(unittest.TestCase):
    def test_two_phases_make_one_file(self):
        with tempfile.TemporaryDirectory() as d:
            now = dt.datetime(2026, 11, 26, tzinfo=dt.timezone.utc)
            sleeps = []
            mp.measure(FakeDocker(), ["direct-play", "jellystat"], "start", 5, 60, sleep=sleeps.append, folder=d, version="0.30.0", now=now)
            mp.measure(FakeDocker(), ["direct-play", "jellystat"], "used", 0, 0, sleep=sleeps.append, folder=d, version="0.30.0", now=now)
            rec = json.loads((pathlib.Path(d) / "direct-play.json").read_text())
            c = rec["containers"][0]
            self.assertEqual((c["memory_mib_start"], c["memory_mib_used"], c["image_size_mb"]), (10.0, 10.0, 73.5))
            self.assertIn("cpu_percent_60s", c)
            self.assertEqual(rec["environment"]["starboard_version"], "0.30.0")
            self.assertTrue(tb.clean(rec))
            self.assertEqual(sleeps[0], 5)

    def test_the_default_docker_is_refused(self):
        import os
        import subprocess
        import sys
        env = {k: v for k, v in os.environ.items() if k != "DOCKER_HOST"}
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "measure_plugins.py"), "--phase", "start"], capture_output=True, text=True, env=env)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("live server", r.stderr)

    def test_memory_parsing(self):
        self.assertEqual(mp.mib("24.5MiB / 1GiB"), 24.5)
        self.assertEqual(mp.mib("1.5GiB / 2GiB"), 1536.0)
        self.assertIsNone(mp.mib("garbage"))

    def test_table(self):
        t = mp.table()
        self.assertIn("| styles | no container |", t)
        self.assertIn("| kavita | not measured yet |", t)


class Rendering(unittest.TestCase):
    def test_pages(self):
        import build
        with tempfile.TemporaryDirectory() as d:
            root = pathlib.Path(d) / "r"
            import shutil
            shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(".git", "site", "reports", "docs"))
            (root / "data" / "resources-test" / "direct-play.json").write_text(json.dumps(REC | {"plugin": "direct-play"}))
            plugins, _, files = build.build(pathlib.Path(d) / "out", dt.date(2026, 11, 25), root=root)
            dp = files["plugins/direct-play.html"]
            self.assertIn("Measured on a test server with made-up data", dp)
            self.assertIn("About 12 MB", dp)
            self.assertIn("About 20 MB", dp)
            self.assertIn("Starboard 0.30.0", dp)
            self.assertIn("No container.", files["plugins/styles.html"])
            self.assertIn("Not measured on a test server yet", files["plugins/kavita.html"])
            self.assertIn('data-testmem="20.1"', files["category/jellyfin.html"])
            self.assertIn('value="testmem"', files["category/jellyfin.html"])
