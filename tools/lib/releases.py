"""Starboard's releases and the plug-in API each one has, so a plug-in's range (>=1.14 <2.0) becomes a plain
"Needs Starboard 0.26 or later". Data in data/starboard-releases.json, written by tools/refresh_releases.py."""
import json
import pathlib
import re

RANGE_PART = re.compile(r"^(>=|<=|>|<|=)?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def ver(s):
    """'1.14.0' or '0.26' as a tuple of three numbers, or None."""
    m = re.match(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$", str(s or "").strip())
    return tuple(int(x or 0) for x in m.groups()) if m else None


def parse_range(spec):
    """[(op, (a,b,c))] for a range such as '>=1.14 <2.0', or None if it is not one."""
    out = []
    for part in str(spec or "").split():
        m = RANGE_PART.match(part)
        if not m:
            return None
        out.append((m.group(1) or "=", tuple(int(x or 0) for x in m.groups()[1:])))
    return out or None


def satisfies(api, spec):
    r = parse_range(spec)
    a = ver(api)
    if r is None or a is None:
        return False
    ops = {">=": lambda x, y: x >= y, "<=": lambda x, y: x <= y, ">": lambda x, y: x > y, "<": lambda x, y: x < y, "=": lambda x, y: x == y}
    return all(ops[op](a, v) for op, v in r)


def load(path):
    """The releases, oldest first: [{version, tag, date, api, url}], those with a known plug-in API only."""
    try:
        data = json.loads(pathlib.Path(path).read_text())
    except (OSError, ValueError):
        return []
    out = []
    for r in data.get("releases", []):
        if isinstance(r, dict) and ver(r.get("version")) and ver(r.get("api")):
            out.append(r)
    return sorted(out, key=lambda r: ver(r["version"]))


def short(version):
    v = ver(version)
    return f"{v[0]}.{v[1]}" if v else str(version)


def needs(spec, releases):
    """{'first': '0.26' or None, 'newest': '0.29' or None, 'limited': bool}: the first Starboard release whose plug-in API
    satisfies the range, and the newest one that does. `limited` is true when newer releases exist that it does not
    work with (the manifest's range stops before them)."""
    ok = [r for r in releases if satisfies(r["api"], spec)]
    if not ok:
        return {"first": None, "newest": None, "limited": False}
    newest = ok[-1]
    return {"first": short(ok[0]["version"]), "first_full": ok[0]["version"], "newest": short(newest["version"]),
            "limited": newest is not releases[-1]}
