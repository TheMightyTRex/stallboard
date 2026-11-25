#!/usr/bin/env python3
"""Turns the pictures from tools/plugin-shots.sh (a folder of catalogue-<id>.png and install-<id>.png) into small WebP files in
assets/shots/<id>/ and writes their alt text into data/shots.json. Also adds a plug-in's own help pictures when a folder of them
is given:  python3 tools/make_shots.py <folder> [--help-images <starboard-plugins>/help/images/<id> --id <id>]
Needs Pillow (the only tool here that does)."""
import argparse
import json
import pathlib
import re
import sys

from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "shots.json"
CAPS = {
    "catalogue": ("In the Catalogue", "The Catalogue in Starboard, showing the {name} row with its logo, a one-line description, its version and {action}. The data is made up."),
    "install": ("Before it is added", "The panel Starboard opens before it adds {name}: what the plug-in may read and change, and a password box to confirm. The data is made up."),
}
MAX_W = 1100


def convert(src, dest):
    im = Image.open(src).convert("RGB")
    if im.width > MAX_W:
        im = im.resize((MAX_W, round(im.height * MAX_W / im.width)), Image.LANCZOS)
    im.save(dest, "WEBP", quality=78, method=6)
    return im.width, im.height


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--id")
    ap.add_argument("--help-images")
    a = ap.parse_args()
    cat = {p["id"]: p["name"] for p in json.loads((ROOT / "site" / "catalogue.json").read_text())["plugins"]}
    data = json.loads(DATA.read_text()) if DATA.exists() else {"plugins": {}}
    names = {}
    for f in sorted(pathlib.Path(a.folder).glob("*.png")):
        m = re.fullmatch(r"(catalogue|install)-([\w-]+)\.png", f.name)
        if not m or m.group(2) not in cat:
            continue
        kind, pid = m.groups()
        out = ROOT / "assets" / "shots" / pid
        out.mkdir(parents=True, exist_ok=True)
        w, h = convert(f, out / f"{kind}.webp")
        cap, alt = CAPS[kind]
        action = "an Added mark" if kind == "catalogue" and (pathlib.Path(a.folder) / f"install-{pid}.png").exists() is False else "an Install button"
        row = {"file": f"{kind}.webp", "alt": alt.format(name=cat[pid], action=action), "caption": cap, "w": w, "h": h, "kind": kind}
        items = [x for x in data["plugins"].get(pid, []) if x.get("kind") != kind and not x["file"].startswith("help-")]
        keep_help = [x for x in data["plugins"].get(pid, []) if x["file"].startswith("help-")]
        data["plugins"][pid] = sorted(items + [row], key=lambda x: 0 if x["kind"] == "catalogue" else 1) + keep_help
        names[pid] = 1
    DATA.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"Wrote pictures for {len(names)} plug-ins")


if __name__ == "__main__":
    sys.exit(main())
