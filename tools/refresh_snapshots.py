#!/usr/bin/env python3
"""Refreshes data/snapshots/<id>.json: fetches each listed plug-in's manifest (and logo) as data, checks it with
Starboard's own check, and keeps the old snapshot if the maker's server is down or the new manifest fails the check.
Writes data/refresh-report.md for the pull request that carries the refresh: what changed, and anything a person must
look at (more permissions, a new image digest, a failed check).

python3 tools/refresh_snapshots.py [id ...]       (no ids: every listing)
Exit code 0 even when a server is down: the build uses the old snapshot until it is too old (see tools/build.py)."""
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))
import listing as lst  # noqa: E402
import manifest as mf  # noqa: E402
import safefetch  # noqa: E402


def diff(old, new):
    """Plain lines saying what changed between two trimmed manifests, the risky ones first."""
    out = []
    if old["version"] != new["version"]:
        out.append(f"version {old['version']} to {new['version']}")
    more = sorted(set(new["permissions"]) - set(old["permissions"]))
    less = sorted(set(old["permissions"]) - set(new["permissions"]))
    if more:
        out.insert(0, "**asks for more: " + ", ".join(more) + "**")
    if less:
        out.append("no longer asks for: " + ", ".join(less))
    oi, ni = [c["image"] for c in old["containers"]], [c["image"] for c in new["containers"]]
    if oi != ni:
        out.append("image changed")
    if old["starboard_api"] != new["starboard_api"]:
        out.append(f"Starboard API {old['starboard_api']} to {new['starboard_api']}")
    return out


def main(ids):
    listings = lst.load_all(ROOT / "listings")
    snaps = ROOT / "data" / "snapshots"
    report, changed = [], 0
    for lid, l in listings.items():
        if ids and lid not in ids:
            continue
        path = snaps / (lid + ".json")
        old = mf.load_snapshot(path) if path.exists() else None
        try:
            new = mf.make_snapshot(l["manifest"])
        except (safefetch.FetchError, ValueError) as e:
            report.append(f"- {lid}: not refreshed ({e}). The old snapshot stays.")
            continue
        if new["id"] != lid:
            report.append(f"- {lid}: **the manifest says its id is {new['id']!r}. Not refreshed.**")
            continue
        if new["problems"] and old:
            report.append(f"- {lid}: **the new manifest fails Starboard's check, so the old snapshot stays:** " + "; ".join(new["problems"][:3]))
            continue
        if old and old["sha256"] == new["sha256"] and old["logo"] == new["logo"]:
            old["fetched_at"] = new["fetched_at"]  # unchanged: only the date moves
            new = old
        else:
            changed += 1
            report.append(f"- {lid}: " + ("; ".join(diff(old["manifest_data"], new["manifest_data"])) if old else "first snapshot") +
                          (" (checks: " + "; ".join(new["problems"][:3]) + ")" if new["problems"] else ""))
        path.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    text = "# Snapshot refresh\n\n" + ("\n".join(report) if report else "Nothing changed.") + "\n"
    (ROOT / "data" / "refresh-report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
