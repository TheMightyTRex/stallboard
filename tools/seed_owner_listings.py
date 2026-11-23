#!/usr/bin/env python3
"""One-off: writes listings/<id>.json for the owner's own plug-ins from the starboard-plugins catalogue.
python3 tools/seed_owner_listings.py PATH_TO/catalogue.json REVIEW_DATE
Each help address was checked with a request (the plug-in help centre's page for each plug-in) before it was written.
Never overwrites a listing that exists: a review date is the day the file was created."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
HELP = "https://themightytrex.github.io/starboard-plugins/help/plugins/{}/index.html"


def main(cat_path, day):
    cat = json.loads(pathlib.Path(cat_path).read_text())
    made = 0
    for p in cat["plugins"]:
        out = ROOT / "listings" / (p["id"] + ".json")
        if out.exists():
            continue
        d = {"id": p["id"], "name": p["name"], "manifest": p["manifest"], "maker": "TheMightyTRexUK", "listed_at": day,
             "reviewed": {"by": "TheMightyTRexUK", "at": day, "version": p["version"]}, "kind": p["kind"],
             "help": HELP.format(p["id"])}
        if p.get("recommended"):
            d["recommended"] = True
        older = [{"version": v["version"], "starboard_api": v.get("starboard_api", ""), "manifest": v["manifest"],
                  "manifest_sha256": v.get("manifest_sha256", "")} for v in (p.get("versions") or [])[1:] if v.get("manifest")]
        if older:
            d["older_versions"] = older
        if p.get("rest"):
            d["maker_figures"] = {"memory_mib": p["rest"]["memory_mb"], "cpu_percent": p["rest"]["cpu_percent"]}
        out.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n")
        made += 1
    print("wrote", made, "listings")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
