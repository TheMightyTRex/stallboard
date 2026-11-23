#!/usr/bin/env python3
"""Refreshes data/starboard-releases.json (each Starboard release and the plug-in API it has) and the Starboard page's
screenshots (assets/starboard/ and data/starboard-screenshots.json, from the pictures in Starboard's README).

python3 tools/refresh_releases.py            fetch what is new (releases never change, so each is read once)
Only https addresses on github.com's own hosts are read, as data, through tools/lib/safefetch.py."""
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))
import releases  # noqa: E402
import safefetch  # noqa: E402

REPO = "TheMightyTRex/starboard"
RAW = f"https://raw.githubusercontent.com/{REPO}/"
OUT = ROOT / "data" / "starboard-releases.json"
SHOTS = ROOT / "data" / "starboard-screenshots.json"
SHOT_WANTED = ["apps.png", "storage.png", "install-apps.png", "library-phone-dark.png"]


def get_json(url):
    return json.loads(safefetch.fetch(url, max_bytes=2 * 1024 * 1024).decode("utf-8"))


def main():
    have = {}
    if OUT.exists():
        have = {r["tag"]: r for r in json.loads(OUT.read_text()).get("releases", [])}
    dates = {}
    for r in get_json(f"https://api.github.com/repos/{REPO}/releases?per_page=100"):
        if isinstance(r, dict) and re.match(r"^v\d+\.\d+\.\d+$", str(r.get("tag_name"))):
            dates[r["tag_name"]] = str(r.get("published_at") or "")[:10]
    tags = [t["name"] for t in get_json(f"https://api.github.com/repos/{REPO}/tags?per_page=100")
            if re.match(r"^v\d+\.\d+\.\d+$", str(t.get("name")))]
    for tag in tags:
        if tag in have and have[tag].get("api"):
            have[tag]["date"] = dates.get(tag) or have[tag].get("date", "")
            continue
        try:
            src = safefetch.fetch(f"{RAW}{tag}/starboard/plugins.py", max_bytes=512 * 1024).decode("utf-8", "replace")
        except safefetch.FetchError:
            continue  # before plug-ins existed
        m = re.search(r'^API_VERSION = "(\d+\.\d+\.\d+)"', src, re.M)
        if m:
            have[tag] = {"version": tag[1:], "tag": tag, "date": dates.get(tag, ""), "api": m.group(1),
                         "url": f"https://github.com/{REPO}/releases/tag/{tag}"}
    rel = sorted(have.values(), key=lambda r: releases.ver(r["version"]))
    OUT.write_text(json.dumps({"source": f"https://github.com/{REPO}", "releases": rel}, indent=1) + "\n")
    print(len(rel), "releases with a plug-in API; newest", rel[-1]["version"] if rel else "none")
    latest = rel[-1]["tag"]
    readme = safefetch.fetch(f"{RAW}{latest}/README.md", max_bytes=512 * 1024).decode("utf-8", "replace")
    shots = []
    (ROOT / "assets" / "starboard").mkdir(parents=True, exist_ok=True)
    for alt, name in re.findall(r"!\[([^\]]{3,300})\]\(docs/screenshots/([A-Za-z0-9_.-]+\.(?:png|jpg))\)", readme):
        if name in SHOT_WANTED and name not in [s["file"] for s in shots]:
            data = safefetch.fetch(f"{RAW}{latest}/docs/screenshots/{name}", max_bytes=400 * 1024)
            (ROOT / "assets" / "starboard" / name).write_bytes(data)
            shots.append({"file": name, "alt": alt})
    SHOTS.write_text(json.dumps({"from": latest, "screenshots": shots}, indent=1) + "\n")
    print(len(shots), "screenshots from", latest)


if __name__ == "__main__":
    main()
