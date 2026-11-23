#!/usr/bin/env python3
"""Refreshes data/snapshots/<id>.json: fetches each listed plug-in's manifest (and logo) as data, checks it with
Starboard's own check, and keeps the old snapshot if the maker's server is down or the new manifest fails the check.
Writes data/refresh-report.md for the pull request that carries the refresh: what changed, and anything a person must
look at (more permissions, a new image digest, a failed check).

python3 tools/refresh_snapshots.py [id ...]       (no ids: every listing)
Exit code 0 even when a server is down: the build uses the old snapshot until it is too old (see tools/build.py)."""
import datetime as dt
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE / "lib"))
sys.path.insert(0, str(HERE))
import listing as lst  # noqa: E402
import manifest as mf  # noqa: E402
import safefetch  # noqa: E402
import submission  # noqa: E402

REREAD_DAYS = 7


def line(s, most=160):
    """Text that came from a maker, made safe for a pull request body: no markup, links, mentions or references."""
    return submission.md(s, most)


def diff(old, new):
    """Plain lines saying what changed between two trimmed manifests, the risky ones first."""
    out = []
    if old["version"] != new["version"]:
        out.append(f"version {line(old['version'], 30)} to {line(new['version'], 30)}")
    more = sorted(set(new["permissions"]) - set(old["permissions"]))
    less = sorted(set(old["permissions"]) - set(new["permissions"]))
    if more:
        out.insert(0, "**asks for more: " + ", ".join(line(m, 40) for m in more) + "**")
    if less:
        out.append("no longer asks for: " + ", ".join(line(m, 40) for m in less))
    oi, ni = [c["image"] for c in old["containers"]], [c["image"] for c in new["containers"]]
    if oi != ni:
        out.append("**image changed**")
    if old["starboard_api"] != new["starboard_api"]:
        out.append(f"Starboard API {line(old['starboard_api'], 40)} to {line(new['starboard_api'], 40)}")
    return out


def one(lid, l, snaps, today):
    """The report line for one listing, or None for no change. Raises nothing the caller cannot catch."""
    path = snaps / (lid + ".json")
    old = mf.load_snapshot(path) if path.exists() else None
    try:
        new = mf.make_snapshot(l["manifest"])
    except (safefetch.FetchError, ValueError) as e:
        return f"- {lid}: not refreshed ({line(e)}). The old snapshot stays."
    if new["id"] != lid:
        return f"- {lid}: **the manifest says its id is {submission.code(new['id'], 40)}. Not refreshed.**"
    if new["problems"] and old:
        return f"- {lid}: **the new manifest fails Starboard's check, so the old snapshot stays:** " + "; ".join(line(p) for p in new["problems"][:3])
    if old and old["sha256"] == new["sha256"] and old["logo"] == new["logo"]:
        # The file is the one that was reviewed. A pull request is opened only when it changes, or to say it was read again
        # (a snapshot older than 7 days gets its date moved, so a listing is never left out for being unread).
        if old["manifest"] != new["manifest"]:  # the listing now names the same file at another address (a commit)
            path.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
            return f"- {lid}: the same file, now at a commit address"
        if mf.snapshot_age_days(old, today) < REREAD_DAYS:
            return None
        old["fetched_at"] = new["fetched_at"]
        path.write_text(json.dumps(old, indent=1, ensure_ascii=False) + "\n")
        return f"- {lid}: the same file, read again (date moved only)"
    path.write_text(json.dumps(new, indent=1, ensure_ascii=False) + "\n")
    what = "; ".join(diff(old["manifest_data"], new["manifest_data"])) if old else "first snapshot"
    return f"- {lid}: **the file changed since it was reviewed.** " + what + (" (checks: " + "; ".join(line(p) for p in new["problems"][:3]) + ")" if new["problems"] else "")


def main(ids):
    listings = lst.load_all(ROOT / "listings")
    snaps = ROOT / "data" / "snapshots"
    today = dt.datetime.now(dt.timezone.utc).date()
    report = []
    for lid, l in listings.items():
        if ids and lid not in ids:
            continue
        try:  # one maker's file can never stop the others
            r = one(lid, l, snaps, today)
        except Exception as e:  # noqa: BLE001  # nosec B110
            r = f"- {lid}: not refreshed (unexpected {line(type(e).__name__, 40)}). The old snapshot stays."
        if r:
            report.append(r)
    text = "# Snapshot refresh\n\n" + ("\n".join(report) if report else "Nothing changed.") + "\n"
    (ROOT / "data" / "refresh-report.md").write_text(text)
    print(text)


if __name__ == "__main__":
    main(set(sys.argv[1:]))
