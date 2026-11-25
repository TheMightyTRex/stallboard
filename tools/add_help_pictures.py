#!/usr/bin/env python3
"""Adds a plug-in's own help pictures (made on a test Starboard with made-up data, with alt text in the plug-ins repo's
tools/help_screenshots/shots.json) to assets/shots/<id>/ and data/shots.json, in the order of that file.
    python3 tools/add_help_pictures.py <plug-ins repo> <id> <folder under help/images>"""
import json
import pathlib
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
repo, pid, folder = pathlib.Path(sys.argv[1]), sys.argv[2], sys.argv[3]
shots = json.loads((repo / "tools" / "help_screenshots" / "shots.json").read_text())["shots"]
data = json.loads((ROOT / "data" / "shots.json").read_text()) if (ROOT / "data" / "shots.json").exists() else {"plugins": {}}
out = ROOT / "assets" / "shots" / pid
out.mkdir(parents=True, exist_ok=True)
rows = []
for s in sorted(shots, key=lambda s: (["install", "settings", "dashboard-card"].index(s["topic"]) if s["topic"] in ("install", "settings", "dashboard-card") else 9, s["file"])):
    src = repo / "help" / "images" / folder / s["file"]
    if not src.exists():
        continue
    im = Image.open(src).convert("RGB")
    if im.width > 1100:
        im = im.resize((1100, round(im.height * 1100 / im.width)), Image.LANCZOS)
    name = "help-" + s["file"].rsplit(".", 1)[0] + ".webp"
    im.save(out / name, "WEBP", quality=78, method=6)
    cap = s["alt"].split(", with")[0].split(" (step")[0].rstrip(".") + "."
    rows.append({"file": name, "alt": s["alt"], "caption": cap, "w": im.width, "h": im.height, "kind": "help"})
keep = [x for x in data["plugins"].get(pid, []) if not x["file"].startswith("help-")]
data["plugins"][pid] = keep + rows
(ROOT / "data" / "shots.json").write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
print(f"{len(rows)} help pictures for {pid}")
