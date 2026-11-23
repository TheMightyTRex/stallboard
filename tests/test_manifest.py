import json
import unittest

import helpers  # noqa: F401
from helpers import ROOT
import manifest as mf
import safefetch

GOOD = json.loads((ROOT / "data" / "snapshots" / "direct-play.json").read_text())
RAW = {
    "manifest_version": 1, "id": "example-plug-in", "name": "Example", "version": "1.0.0", "description": "Does one small thing.", "author": "Example Maker",
    "licence": "MIT", "homepage": "https://github.com/example/example", "support_url": "https://github.com/example/example/issues", "starboard_api": ">=1.14 <2.0",
    "permissions": ["system:read"], "containers": [{"name": "main", "image": "ghcr.io/example/example@sha256:" + "a" * 64, "port": 8080, "network": "default",
                                                     "volumes": ["data"], "start": "when_needed", "idle_stop_minutes": 10}],
    "resources": {"main": {"memory": 64, "cpus": 0.25}},
}


def fetcher(manifest, logo=None):
    def f(url, max_bytes=0, **kw):
        if url.endswith(".json"):
            return json.dumps(manifest).encode()
        if logo is None:
            raise safefetch.FetchError("no logo")
        return logo
    return f


class Checks(unittest.TestCase):
    def test_a_good_manifest_passes_starboards_own_check(self):
        self.assertEqual(mf.problems(RAW), [])

    def test_problems_are_reported_in_words(self):
        bad = dict(RAW, permissions=["root:everything"], unknown_field=1)
        bad["containers"] = [dict(RAW["containers"][0], image="ghcr.io/example/example:latest")]
        out = " ".join(mf.problems(bad))
        self.assertIn("Unknown field unknown_field", out)
        self.assertIn("permissions must be a list", out)
        self.assertIn("digest", out)

    def test_hostile_shapes_never_raise(self):
        for m in [[], "text", None, 5, {"containers": "x"}, {"containers": [5, None]}, {"permissions": {"a": 1}}, {"resources": [1]}, {"changes": "x"},
                  {"permissions": [["a"]], "containers": [{"image": 5}]}, {"logo": 5}, {"update": 5}]:
            self.assertTrue(mf.problems(m), m)
            if isinstance(m, dict):
                mf.trim(m)

    def test_a_huge_field_is_cut_and_fails_the_check(self):
        m = dict(RAW, description="x" * 5_000_000, name="n" * 10_000, author="a" * 10_000)
        t = mf.trim(m)
        self.assertLessEqual(len(t["description"]), 200)
        self.assertLessEqual(len(t["name"]), 40)
        self.assertTrue(any("description" in p for p in mf.problems(m)))

    def test_trim_keeps_only_what_the_site_needs(self):
        m = dict(RAW, settings=[{"key": "x"}], cards=[{"id": "y"}], jobs=[{"id": "j"}], changes=[{"version": "1.0.0", "date": "2026-11-23", "added": ["**Bold:** new\x07 thing"] + ["x"] * 50, "bogus": 1}])
        t = mf.trim(m)
        self.assertNotIn("settings", t)
        self.assertEqual(t["versions"][0]["groups"][0][1][0], "Bold: new thing")
        self.assertEqual(len(t["versions"][0]["groups"][0][1]), 12)

    def test_dates_and_numbers_are_checked(self):
        m = dict(RAW, changes=[{"version": "1.0.0", "date": "yesterday<script>"}], resources={"main": {"memory": -5, "cpus": "lots", "pids": float("nan")}})
        t = mf.trim(m)
        self.assertEqual(t["versions"][0]["date"], "")
        self.assertEqual(t["resources"]["main"], {"memory": None, "cpus": None, "pids": None})

    def test_whole_words_never_stops_mid_word(self):
        self.assertTrue(mf.whole_words("word " * 400, 600).endswith("…"))
        self.assertEqual(mf.whole_words("One. Two.", 600), "One. Two.")

    def test_kinds(self):
        self.assertEqual(mf.kind_for({"styles": [1]}), "Appearance")
        self.assertEqual(mf.kind_for({"permissions": ["network:port"]}), "Apps you can add")
        self.assertIn(mf.kind_for({"permissions": []}), mf.KINDS)


class Snapshots(unittest.TestCase):
    def test_make_snapshot_reads_data_only(self):
        s = mf.make_snapshot("https://example.com/x/starboard-plugin.json", fetch=fetcher(RAW))
        self.assertEqual(s["id"], "example-plug-in")
        self.assertEqual(s["problems"], [])
        self.assertEqual(len(s["sha256"]), 64)
        self.assertEqual(s["logo"], "")

    def test_not_json_and_not_an_object(self):
        for body in (b"<html>", b"[]", b"5", b"\xff\xfe", b"[" * 100000):
            with self.assertRaises(ValueError, msg=body[:10]):
                mf.make_snapshot("https://example.com/x.json", fetch=lambda url, max_bytes=0, **k: body)

    def test_a_logo_with_a_script_is_refused_and_the_snapshot_still_made(self):
        m = dict(RAW, logo={"file": "logo.svg", "alt": "A bad logo"})
        bad = b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><script>alert(1)</script><rect width="10" height="10"/></svg>'
        s = mf.make_snapshot("https://example.com/x/starboard-plugin.json", fetch=fetcher(m, bad))
        self.assertNotIn("script", s["logo"])
        import base64
        if s["logo"]:
            self.assertNotIn(b"script", base64.b64decode(s["logo"].split(",", 1)[1]))
        else:
            self.assertTrue(s["logo_note"])

    def test_a_logo_that_goes_up_a_folder_is_refused(self):
        m = dict(RAW, logo={"file": "../../etc/passwd.svg", "alt": "Bad"})
        s = mf.make_snapshot("https://example.com/x/starboard-plugin.json", fetch=fetcher(m, b"x"))
        self.assertEqual(s["logo"], "")
        self.assertTrue(s["problems"])

    def test_committed_snapshots_load(self):
        for p in sorted((ROOT / "data" / "snapshots").glob("*.json")):
            s = mf.load_snapshot(p)
            self.assertEqual(s["manifest_data"]["id"], p.stem)
            self.assertEqual(s["problems"], [], p.name)

    def test_load_snapshot_rejects_bad_shapes(self):
        import tempfile
        import pathlib
        with tempfile.TemporaryDirectory() as d:
            for body in ('[]', '{"manifest_data": {}, "fetched_at": "yesterday"}', '{"manifest_data": 5, "fetched_at": "2026-11-23T10:00Z"}'):
                p = pathlib.Path(d) / "x.json"
                p.write_text(body)
                with self.assertRaises(ValueError):
                    mf.load_snapshot(p)

    def test_vendored_starboard_is_the_pinned_release(self):
        import hashlib
        meta = json.loads((ROOT / "vendor" / "starboard" / "VENDORED.json").read_text())
        self.assertRegex(meta["release"], r"^v\d+\.\d+\.\d+$")
        for name, h in meta["sha256"].items():
            self.assertEqual(hashlib.sha256((ROOT / "vendor" / "starboard" / name).read_bytes()).hexdigest(), h, name + " was changed by hand")


if __name__ == "__main__":
    unittest.main()
